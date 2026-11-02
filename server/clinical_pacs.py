"""Scoped DICOM ingest, archive preview and OHIF/DICOMweb gateway."""
import hashlib
import io
import os
import re
import uuid

import httpx
import pydicom
from pydicom.uid import (ComputedRadiographyImageStorage, DigitalXRayImageStorageForPresentation,
                        DigitalXRayImageStorageForProcessing)
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server.db import get_db
from server.clinical import doctor, image_data, event, MAX_FILE
from server.clinical_models import ImagingInstance, ImagingStudy, Investigation
from server.clinical_access import require_screening

router = APIRouter()

def archive_config():
    url = os.getenv("ORTHANC_URL", "").rstrip("/")
    if not url: raise HTTPException(503, "Imaging archive not configured. Start the PACS services.")
    return url, (os.getenv("ORTHANC_USER", "clinical"), os.getenv("ORTHANC_PASSWORD", ""))

async def archive(method, path, **kwargs):
    url, auth = archive_config()
    try:
        async with httpx.AsyncClient(timeout=20, auth=auth, follow_redirects=False) as client:
            response = await client.request(method, url+path, **kwargs)
    except httpx.HTTPError:
        raise HTTPException(503, "Imaging archive is unavailable.")
    if response.status_code >= 400:
        raise HTTPException(502, "Imaging archive rejected the request.")
    return response

@router.post("/cases/{case_id}/imaging")
async def upload_imaging(case_id: str, order_id: str = Form(...),
                         identity_confirmed: bool = Form(False), files: list[UploadFile] = File(...),
                         user=Depends(doctor), db: Session = Depends(get_db)):
    s = require_screening(db, user, case_id)
    order = db.query(Investigation).filter_by(id=order_id, screening_id=case_id, kind="Chest X-ray").first()
    if not order or order.status in {"cancelled", "reviewed"}:
        raise HTTPException(422, "Select an open chest X-ray investigation.")
    if not 1 <= len(files) <= 20: raise HTTPException(422, "Upload 1 to 20 DICOM files per batch.")
    received = []
    for file in files:
        data = await file.read(MAX_FILE+1)
        if not data or len(data) > MAX_FILE: raise HTTPException(413, "Each DICOM file must be at most 20 MB.")
        try:
            ds = pydicom.dcmread(io.BytesIO(data))
            sop, series, study = str(ds.SOPInstanceUID), str(ds.SeriesInstanceUID), str(ds.StudyInstanceUID)
            if not all(re.fullmatch(r"[0-9.]{1,64}", x) for x in (sop, series, study)): raise ValueError()
            supported = {str(ComputedRadiographyImageStorage), str(DigitalXRayImageStorageForPresentation),
                         str(DigitalXRayImageStorageForProcessing)}
            if str(ds.SOPClassUID) not in supported or str(ds.get('Modality','')) not in {'CR','DX'}:
                raise ValueError()
            if str(ds.file_meta.MediaStorageSOPInstanceUID) != sop or str(ds.file_meta.MediaStorageSOPClassUID) != str(ds.SOPClassUID):
                raise ValueError()
            if 'PixelData' not in ds or not 1 <= int(ds.Rows)*int(ds.Columns) <= 25_000_000:
                raise ValueError()
            if int(ds.get('NumberOfFrames',1)) != 1: raise ValueError()
            patient = str(ds.get("PatientID", ""))[:128]
        except Exception:
            raise HTTPException(422, "Use a valid single-frame CR/DX image with matching DICOM identifiers and pixel data.")
        if patient != s.patient_code and not identity_confirmed:
            raise HTTPException(409, "DICOM patient ID differs. Explicitly confirm patient association.")
        association = db.get(ImagingStudy, study)
        if association and association.screening_id != case_id:
            raise HTTPException(409, "This study is linked to another case.")
        digest = hashlib.sha256(data).hexdigest()
        old = db.query(ImagingInstance).filter_by(sop_uid=sop).first()
        if old:
            if old.screening_id != case_id or old.sha256 != digest or old.order_id != order_id:
                raise HTTPException(409, "Conflicting DICOM instance.")
            received.append(image_data(old)); continue
        if association is None:
            db.add(ImagingStudy(study_uid=study, screening_id=case_id))
            try: db.flush()
            except IntegrityError:
                db.rollback(); raise HTTPException(409, "Study association changed. Reload and retry.")
        result = await archive("POST", "/instances", content=data, headers={"Content-Type": "application/dicom"})
        instance_id = result.json().get("ID", "")
        if not re.fullmatch(r"[a-f0-9-]{20,80}", instance_id):
            raise HTTPException(502, "Archive returned an invalid receipt.")
        obj = ImagingInstance(id=str(uuid.uuid4()), screening_id=case_id, order_id=order_id,
                              sop_uid=sop, series_uid=series, study_uid=study, orthanc_id=instance_id,
                              sha256=digest, patient_id=patient,
                              identity_check="id_match" if patient == s.patient_code else "manually_confirmed")
        db.add(obj); event(db, case_id, user, "image_received", {"id": obj.id, "order_id": order_id})
        try: db.commit()
        except IntegrityError:
            db.rollback(); raise HTTPException(409, "Concurrent ingestion; reload and retry.")
        received.append(image_data(obj))
    return {"instances": received, "receipt": "received", "study_completeness": "unconfirmed"}

@router.get("/imaging/{image_id}/preview")
async def image_preview(image_id: str, user=Depends(doctor), db: Session = Depends(get_db)):
    obj = db.get(ImagingInstance, image_id)
    if not obj: raise HTTPException(404, "Image not found.")
    require_screening(db, user, obj.screening_id)
    result = await archive("GET", f"/instances/{obj.orthanc_id}/frames/0/preview")
    return Response(result.content, media_type="image/png", headers={"Cache-Control": "no-store"})

@router.get("/pacs/status")
async def pacs_status(user=Depends(doctor)):
    if not os.getenv("ORTHANC_URL"):
        return {"archive": "not_configured", "viewer": bool(os.getenv("OHIF_URL"))}
    try:
        await archive("GET", "/system")
        return {"archive": "connected", "viewer": bool(os.getenv("OHIF_URL"))}
    except HTTPException:
        return {"archive": "unavailable", "viewer": bool(os.getenv("OHIF_URL"))}

@router.get("/pacs/dicom-web/{path:path}")
async def dicom_web(path: str, request: Request, user=Depends(doctor), db: Session = Depends(get_db)):
    # Global QIDO searches, arbitrary archive routes and writes are not exposed.
    if ".." in path or "%" in path or "\\" in path:
        raise HTTPException(404, "Unsupported imaging path.")
    pieces = path.strip("/").split("/")
    study = pieces[1] if len(pieces) > 1 and pieces[0] == "studies" else None
    if path.strip("/") == "studies":
        study = request.query_params.get("StudyInstanceUID")
    if not study or not re.fullmatch(r"[0-9.]{1,64}", study):
        raise HTTPException(403, "An explicit authorised StudyInstanceUID is required.")
    if any(v != study for v in request.query_params.getlist("StudyInstanceUID")):
        raise HTTPException(403, "Conflicting study filter.")
    obj = db.query(ImagingInstance).filter_by(study_uid=study).first()
    if not obj: raise HTTPException(404, "Study not found.")
    require_screening(db, user, obj.screening_id)
    if pieces[0] != "studies": raise HTTPException(404, "Unsupported imaging path.")
    allowed_query = {"StudyInstanceUID", "includefield", "limit", "offset", "SeriesInstanceUID", "SOPInstanceUID"}
    params = [(k, v) for k, v in request.query_params.multi_items() if k in allowed_query]
    result = await archive("GET", "/dicom-web/"+path, params=params,
                           headers={"Accept": request.headers.get("accept", "*/*")})
    headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    if "content-type" in result.headers: headers["Content-Type"] = result.headers["content-type"]
    # Orthanc may emit absolute BulkDataURI values. Never expose its private origin.
    if "application/dicom+json" in result.headers.get("content-type", ""):
        def rewrite(value):
            if isinstance(value, dict):
                for k, v in value.items():
                    if k == "BulkDataURI" and isinstance(v, str):
                        match = re.search(r"/studies/([0-9.]+)/", v)
                        if not match or match.group(1) != study:
                            raise HTTPException(502, "Unexpected archive bulk data reference.")
                        value[k] = "/clinical/pacs/dicom-web"+v[match.start():]
                    else: rewrite(v)
            elif isinstance(value, list):
                for v in value: rewrite(v)
        metadata = result.json(); rewrite(metadata)
        from fastapi.responses import JSONResponse
        return JSONResponse(metadata, media_type="application/dicom+json", headers={"Cache-Control": "no-store"})
    return Response(result.content, headers=headers)

@router.get("/pacs/viewer/{path:path}")
async def ohif(path: str, user=Depends(doctor)):
    base = os.getenv("OHIF_URL", "").rstrip("/")
    if not base: raise HTTPException(503, "OHIF viewer not configured.")
    if ".." in path or "%" in path or "\\" in path: raise HTTPException(404, "Unsupported viewer path.")
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            result = await client.get(base+"/"+path)
    except httpx.HTTPError: raise HTTPException(503, "OHIF viewer unavailable.")
    if result.status_code != 200: raise HTTPException(result.status_code, "Viewer resource unavailable.")
    return Response(result.content, headers={"Content-Type": result.headers.get("content-type", "application/octet-stream"),
                                             "Cache-Control": "no-store",
                                             "Cross-Origin-Opener-Policy": "same-origin",
                                             "Cross-Origin-Embedder-Policy": "require-corp"})

