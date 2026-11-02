#!/usr/bin/env python3
"""
ShwaasAI Lightweight Mock Server
Allows developing and testing the Mobile App without running the heavy PyTorch model.
Returns realistic fixture branches based on input parameters or an explicit mock selector.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="ShwaasAI Lightweight Mock Server", version="1.0.0")

# Enable CORS for all local development clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).parent.parent
RESPONSES_DIR = PROJECT_ROOT / "fixtures" / "responses"

def load_fixture(filename: str) -> dict:
    path = RESPONSES_DIR / f"{filename}.json"
    if not path.exists():
        return {"status": "error", "message": f"Fixture {filename} not found."}
    with open(path, "r") as f:
        return json.load(f)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ShwaasAI Mock Server",
        "mode": "static_fixtures",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/version")
async def version_info():
    return {
        "version": "1.0.0-mock",
        "contract": "1.0.0",
        "engine": "fixture-replay"
    }

@app.post("/predict")
@app.post("/screenings")
async def mock_predict(
    file: UploadFile = File(None),
    age: int = Form(18),
    sex: str = Form("prefer_not_to_say"),
    village: str = Form("Unknown"),
    cough_duration: int = Form(0),
    fever: int = Form(0),
    night_sweats: int = Form(0),
    weight_loss: int = Form(0),
    hemoptysis: int = Form(0),
    tb_contact: int = Form(0),
    diabetes: int = Form(0),
    hiv: int = Form(0),
    immunosuppression: int = Form(0),
    silica_exposure: int = Form(0),
    include_gradcam: bool = Query(False),
    mock_branch: str = Query(None)  # Optional query param to force a specific branch
):
    # 1. Direct branch override via query param
    if mock_branch:
        fix = load_fixture(mock_branch)
        status_code = fix.get("status_code", 200)
        resp = fix.get("response", fix)
        if isinstance(resp, dict) and "session_id" not in resp and status_code == 200:
            resp["session_id"] = str(uuid.uuid4())
        return JSONResponse(status_code=status_code, content=resp)

    # 2. Pediatric age check
    if age < 18:
        fix = load_fixture("branch_07_error_pediatric_age")
        return JSONResponse(status_code=fix.get("status_code", 400), content=fix.get("response"))

    # 3. Audio file quality simulation
    filename = file.filename.lower() if (file and file.filename) else ""
    if "clipping" in filename:
        fix = load_fixture("branch_08_error_clipping")
        return JSONResponse(status_code=fix.get("status_code", 400), content=fix.get("response"))
    if "silence" in filename or "quiet" in filename:
        fix = load_fixture("branch_09_error_silence")
        return JSONResponse(status_code=fix.get("status_code", 400), content=fix.get("response"))
    if "corrupt" in filename:
        fix = load_fixture("branch_10_error_500")
        return JSONResponse(status_code=fix.get("status_code", 500), content=fix.get("response"))

    # 4. Clinical Logic Routing Simulation
    if hemoptysis == 2:
        fix = load_fixture("branch_02_urgent_red_flag")
    elif (hiv == 2 or immunosuppression == 2 or tb_contact == 2) and (cough_duration + fever + night_sweats <= 2):
        fix = load_fixture("branch_03_high_risk_screening")
    elif fever == 2 and night_sweats == 2 and weight_loss == 2:
        fix = load_fixture("branch_05_high_risk")
    elif cough_duration == 2 or (fever + night_sweats + weight_loss >= 2):
        fix = load_fixture("branch_04_moderate_risk")
    elif include_gradcam:
        fix = load_fixture("branch_06_with_gradcam")
    else:
        fix = load_fixture("branch_01_low_risk")

    response_body = fix.get("response", fix).copy()
    response_body["session_id"] = str(uuid.uuid4())
    if "patient_demographics" in response_body:
        response_body["patient_demographics"]["age"] = age
        response_body["patient_demographics"]["sex"] = sex
        response_body["patient_demographics"]["village"] = village

    # Add optional Grad-CAM if requested and not already attached
    if include_gradcam and "gradcam_image" not in response_body:
        cam_fix = load_fixture("branch_06_with_gradcam")
        response_body["gradcam_image"] = cam_fix.get("response", {}).get("gradcam_image")

    return JSONResponse(status_code=fix.get("status_code", 200), content=response_body)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mock_server:app", host="0.0.0.0", port=8001, reload=True)
