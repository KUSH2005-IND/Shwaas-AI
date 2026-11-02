"""Clinical integration checks: no Torch, patient data or external archive."""
import hashlib
import io
import json
import uuid
import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, DigitalXRayImageStorageForPresentation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from server import clinical, clinical_pacs
from server.auth import hash_password, create_access_token
from server.db import Base, User, Screening, Referral, get_db
from server.clinical_models import ClinicalCase, ClinicalMutation, ClinicalChange

@pytest.fixture(scope="session")
def password_hash(): return hash_password("Test-password-2026")

@pytest.fixture
def setup(tmp_path, monkeypatch, password_hash):
    engine=create_engine("sqlite://",poolclass=StaticPool,connect_args={"check_same_thread":False})
    Base.metadata.create_all(engine); factory=sessionmaker(bind=engine)
    with factory() as db:
        db.add_all([User(id=1,username="doc",role="doctor",phc_center="A",hashed_password=password_hash),
                    User(id=2,username="worker",role="worker",phc_center="A",hashed_password=password_hash),
                    User(id=3,username="other",role="doctor",phc_center="B",hashed_password=password_hash)])
        db.flush()
        for sid,owner in [("case-a",2),("case-b",3)]:
            db.add(Screening(id=sid,user_id=owner,patient_code="DEMO-1042",age=40,sex="male",village="Demo",
                             answers_json='{"cough_duration":2}',clinical_score=2,audio_raw_score=.6,
                             audio_calibrated_score=.5,tier="MODERATE",pathway_code="PHC_EVALUATION",
                             recommended_pathway="Demo",consent_given=True))
            db.flush();db.add(Referral(screening_id=sid,status="pending"))
        db.commit()
    def dependency():
        with factory() as db: yield db
    clinical.app.dependency_overrides[get_db]=dependency
    monkeypatch.setattr(clinical,"FILES",tmp_path)
    with TestClient(clinical.app) as client: yield client,factory,dependency
    clinical.app.dependency_overrides.clear();engine.dispose()

def headers(user="doc"):return {"Authorization":"Bearer "+create_access_token({"sub":user})}
def review(version=0,**kwargs):return {"event_id":str(uuid.uuid4()),"expected_version":version,"status":"under_review","notes":"Clinical note","next_action":"Follow up",**kwargs}
def png():
    s=io.BytesIO();Image.new("RGB",(60,80),"white").save(s,"PNG");return s.getvalue()
def create_order(c):
    r=c.post('/clinical/cases/case-a/investigations',headers=headers(),json={"event_id":str(uuid.uuid4()),"kind":"Chest X-ray"})
    assert r.status_code==200,r.text
    return r.json()
def dicom(patient="DEMO-1042",study="1.2.3",sop="1.2.3.4.5"):
    meta=FileMetaDataset();meta.TransferSyntaxUID=ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID=DigitalXRayImageStorageForPresentation;meta.MediaStorageSOPInstanceUID=sop
    ds=FileDataset(None,{},file_meta=meta,preamble=b'\0'*128)
    ds.SOPClassUID=meta.MediaStorageSOPClassUID;ds.SOPInstanceUID=sop;ds.StudyInstanceUID=study
    ds.SeriesInstanceUID=study+'.1';ds.PatientID=patient;ds.Modality='DX'
    ds.Rows=2;ds.Columns=2;ds.SamplesPerPixel=1;ds.PhotometricInterpretation='MONOCHROME2'
    ds.BitsAllocated=8;ds.BitsStored=8;ds.HighBit=7;ds.PixelRepresentation=0;ds.PixelData=b'\0\x40\x80\xff'
    s=io.BytesIO();ds.save_as(s,enforce_file_format=True);return s.getvalue()
async def fake_archive(method,path,**kwargs):
    if method=='POST':return httpx.Response(200,json={"ID":"a"*40})
    if path.endswith('/preview'):return httpx.Response(200,content=png(),headers={'content-type':'image/png'})
    return httpx.Response(200,json=[],headers={'content-type':'application/dicom+json'})

def test_auth_and_facility_scope(setup):
    c,_,_=setup
    assert c.get('/clinical/cases').status_code==401
    assert c.get('/clinical/cases',headers=headers('worker')).status_code==403
    assert [s['id'] for s in c.get('/clinical/cases',headers=headers()).json()['cases']]==['case-a']
    assert c.get('/clinical/cases/case-b',headers=headers()).status_code==404

def test_cookie_login_and_csrf(setup):
    c,_,_=setup;body={'username':'doc','password':'Test-password-2026'}
    assert c.post('/clinical/session',json=body).status_code==403
    r=c.post('/clinical/session',json=body,headers={'X-Requested-With':'ShwaasClinical'})
    assert r.status_code==200 and 'HttpOnly' in r.headers['set-cookie']
    assert c.get('/clinical/session').status_code==200
    assert c.post('/clinical/cases/case-a/review',json=review()).status_code==403

def test_exact_retry_has_one_receipt(setup):
    c,f,_=setup;body=review();r=c.post('/clinical/cases/case-a/review',headers=headers(),json=body)
    assert r.status_code==200,r.text
    assert c.post('/clinical/cases/case-a/review',headers=headers(),json=body).json()==r.json()
    with f() as db:
        assert db.query(ClinicalMutation).count()==1 and db.query(ClinicalChange).count()==1
        assert db.get(ClinicalCase,'case-a').version==1

def test_event_reuse_cannot_change_body(setup):
    c,_,_=setup;body=review();assert c.post('/clinical/cases/case-a/review',headers=headers(),json=body).status_code==200
    body['notes']='Changed silently'
    assert c.post('/clinical/cases/case-a/review',headers=headers(),json=body).status_code==409

def test_stale_update_preserves_winning_note(setup):
    c,_,_=setup
    assert c.post('/clinical/cases/case-a/review',headers=headers(),json=review(notes='Winning note')).status_code==200
    assert c.post('/clinical/cases/case-a/review',headers=headers(),json=review(notes='Stale note')).status_code==409
    assert c.get('/clinical/cases/case-a',headers=headers()).json()['clinical']['notes']=='Winning note'

def test_report_snapshot_does_not_change(setup):
    c,_,_=setup
    assert c.post('/clinical/cases/case-a/review',headers=headers(),json=review(status='reviewed',notes='')).status_code==422
    r=c.post('/clinical/cases/case-a/review',headers=headers(),json=review(status='reviewed',notes='Original')).json()
    assert c.post('/clinical/cases/case-a/review',headers=headers(),json=review(1,notes='Later amendment')).status_code==200
    assert c.get('/clinical/reports/'+r['report_id'],headers=headers()).json()['snapshot']['clinical']['notes']=='Original'
    assert c.get('/clinical/reports/'+r['report_id'],headers=headers('other')).status_code==404

def test_investigation_transitions_and_retry(setup):
    c,_,_=setup;o=create_order(c);body={'event_id':str(uuid.uuid4()),'expected_version':1,'status':'reviewed','notes':'x'};url='/clinical/cases/case-a/investigations/'+o['id']
    assert c.post(url,headers=headers(),json=body).status_code==409
    body['status']='accepted';assert c.post(url,headers=headers(),json=body).status_code==200
    assert c.post(url,headers=headers(),json=body).status_code==200
    body['event_id']=str(uuid.uuid4());body['status']='result_received'
    assert c.post(url,headers=headers(),json=body).status_code==409

def test_document_receipt_and_source_verification(setup):
    c,_,_=setup;file=png();fields=[{'name':'Test','value':'Synthetic value','page':1}]
    def upload():return c.post('/clinical/cases/case-a/documents',headers=headers('worker'),files={'file':('demo.png',file)},data={'fields_json':json.dumps(fields),'expected_sha256':hashlib.sha256(file).hexdigest()})
    r=upload();assert r.status_code==200,r.text;doc=r.json()['document'];assert doc['verification']=='needs_verification'
    assert upload().json()['receipt']=='already_received'
    assert c.get('/clinical/documents/'+doc['id']+'/file',headers=headers('other')).status_code==404
    assert c.get('/clinical/documents/'+doc['id']+'/file',headers=headers()).content==file
    body={'expected_version':1,'fields':fields};url='/clinical/documents/'+doc['id']+'/confirm'
    assert c.post(url,headers=headers(),json=body).json()['verification']=='transcription_confirmed'
    assert c.post(url,headers=headers(),json=body).status_code==409

@pytest.mark.parametrize('data,fields,checksum',[(b'fake','[]',''),(png(),'{}',''),(png(),'[]','0'*64)])
def test_invalid_document_rejected(setup,data,fields,checksum):
    c,_,_=setup
    assert c.post('/clinical/cases/case-a/documents',headers=headers(),files={'file':('unsafe.png',data)},data={'fields_json':fields,'expected_sha256':checksum}).status_code==422

def test_changes_are_scoped(setup):
    c,_,_=setup;c.post('/clinical/cases/case-a/review',headers=headers(),json=review())
    r=c.get('/clinical/changes',headers=headers()).json();assert len(r['events'])==1
    assert c.get('/clinical/changes?after='+str(r['cursor']),headers=headers()).json()['events']==[]
    assert c.get('/clinical/changes',headers=headers('other')).json()['events']==[]

def test_dicom_ingest_scope_identity_and_retry(setup,monkeypatch):
    c,_,_=setup;monkeypatch.setattr(clinical_pacs,'archive',fake_archive);o=create_order(c)
    def upload(data,**extra):return c.post('/clinical/cases/case-a/imaging',headers=headers(),data={'order_id':o['id'],**extra},files={'files':('test.dcm',data)})
    assert upload(dicom('WRONG')).status_code==409
    r=upload(dicom());assert r.status_code==200,r.text;image=r.json()['instances'][0]
    assert upload(dicom()).json()['instances'][0]['id']==image['id']
    assert upload(dicom('DIFFERENT')).status_code==409
    assert c.get('/clinical/imaging/'+image['id']+'/preview',headers=headers('other')).status_code==404
    assert c.get('/clinical/imaging/'+image['id']+'/preview',headers=headers()).status_code==200
    assert c.get('/clinical/pacs/dicom-web/studies',headers=headers()).status_code==403
    assert c.get('/clinical/pacs/dicom-web/studies?StudyInstanceUID=1.2.3',headers=headers()).status_code==200
    assert c.get('/clinical/pacs/dicom-web/studies/1.2.3/metadata',headers=headers('other')).status_code==404
    assert c.get('/clinical/pacs/dicom-web/studies/1.2.3?StudyInstanceUID=9.9',headers=headers()).status_code==403

def test_unconfigured_pacs_is_explicit(setup,monkeypatch):
    c,_,_=setup;monkeypatch.delenv('ORTHANC_URL',raising=False)
    assert c.get('/clinical/pacs/status',headers=headers()).json()['archive']=='not_configured'
    o=create_order(c)
    assert c.post('/clinical/cases/case-a/imaging',headers=headers(),data={'order_id':o['id']},files={'files':('test.dcm',dicom())}).status_code==503

def test_legacy_read_endpoints_are_protected(setup):
    from server.main import app
    _,_,dependency=setup;app.dependency_overrides[get_db]=dependency
    try:
        with TestClient(app) as c:
            assert c.get('/screenings').status_code==401
            assert c.get('/stats').status_code==401
            assert c.get('/screenings/case-b',headers=headers()).status_code==404
            assert c.get('/stats',headers=headers()).json()['total_screenings']==1
            assert len(c.get('/screenings',headers=headers()).json())==1
    finally:app.dependency_overrides.clear()

def test_unknown_fields_are_rejected(setup):
    c,_,_=setup
    assert c.post('/clinical/cases/case-a/review',headers=headers(),json=review(unknown_field=True)).status_code==422

def test_mobile_submission_reaches_facility_worklist(setup,monkeypatch):
    import sys
    from types import ModuleType
    from server.main import app
    from server.schemas import TierEnum, PathwayCodeEnum
    _,_,dependency=setup
    module=ModuleType('server.pipeline')
    async def frozen_contract(**kwargs):
        return {'clinical_score':2,'questionnaire_max':18,'raw_prob':.5,'calibrated_prob':.4,
                'tier':TierEnum.MODERATE,'pathway_code':PathwayCodeEnum.PHC_EVALUATION,
                'recommended_pathway':'Demo pathway','red_flag':False,'high_risk':False,
                'uncertain_symptoms':[],'gradcam_image':None,'fusion_status':'finalized'}
    module.run_screening_pipeline=frozen_contract
    monkeypatch.setitem(sys.modules,'server.pipeline',module)
    app.dependency_overrides[get_db]=dependency
    try:
        with TestClient(app) as c:
            r=c.post('/screenings',headers=headers('worker'),data={'consent_given':'true','age':40},files={'file':('test.wav',b'synthetic','audio/wav')})
            assert r.status_code==200,r.text
            sid=r.json()['session_id']
            assert c.get('/clinical/cases/'+sid,headers=headers()).status_code==200
            assert c.get('/clinical/cases/'+sid,headers=headers('other')).status_code==404
    finally: app.dependency_overrides.clear()

def test_screening_requires_explicit_consent_and_auth(setup):
    from server.main import app
    _,_,dependency=setup;app.dependency_overrides[get_db]=dependency
    try:
        with TestClient(app) as c:
            f={'file':('test.wav',b'synthetic','audio/wav')}
            assert c.post('/screenings',files=f).status_code==401
            assert c.post('/screenings',headers=headers('worker'),files=f).status_code==422
    finally: app.dependency_overrides.clear()
