# 📋 ShwaasAI — Locked API & Data Contract
**Specification Version:** 1.0.0 (Phase 0 Complete)  
**Target Clients:** Frontline ASHA Mobile App (Flutter), Hardware ESP32 Gateway, Mock Server  
**Backend:** FastAPI Extended Service (`src.server_ext:app` / `mock_server:app`)  

---

## 1. Questions for Kushagra & Architectural Resolutions

| Question | Issue in Current Repo | Locked Architectural Resolution |
| :--- | :--- | :--- |
| **1. What does each answer value mean (0, 1, 2)? Is "Unsure" a score or a flag?** | `src/api.py` sums `0 + 1 + 2`, so "Unsure" scored 2 points (more than "Yes" = 1). | **`0 = No` (0 pts)**, **`1 = Unsure` (0 pts, uncertainty flag raised)**, **`2 = Yes` (clinical points awarded)**. Uncertainty does not artificially inflate symptom severity; instead, it raises `uncertain_symptoms` for frontline clarification. |
| **2. Which fields count as red flags and high-risk?** | `tb_contact == 3` was dead code; `hemoptysis == 2` fired on "Unsure" under old docs. | **Red Flag:** `hemoptysis == 2` (Yes) triggers immediate `URGENT` triage override.<br>**High Risk:** `hiv == 2`, `immunosuppression == 2`, or `tb_contact == 2` triggers `HIGH_RISK_SCREENING` pathway if clinical score is low. |
| **3. Is the score max 18 or 20?** | 10 questions at max 2 each gave 20, but docs and payload state `questionnaire_max: 18`. | Standardized WHO-aligned clinical weighting table where the maximum possible sum across all 10 fields is strictly **18 points**. |
| **4. Can we add session_id, tier enum, and pathway_code?** | Missing in `src/api.py`. | **Yes.** Every response now includes a unique `session_id` (UUIDv4), a strict `tier` enum, and a machine-readable `pathway_code`. |
| **5. Where can we get 5–10 sample cough WAVs?** | None in original repo. | 5 standardized, realistic cough WAVs (heavy, shallow, wet, double-burst) plus silence and clipping test fixtures are now generated and stored in `fixtures/audio/`. |

---

## 2. Symptom Questionnaire Schema & Clinical Weights

| Field Name | Type | Options | Weight if Yes (2) | Clinical Role |
| :--- | :--- | :--- | :---: | :--- |
| `cough_duration` | int | 0=No, 1=Unsure, 2=Yes (>2 weeks) | 2 | Primary symptom |
| `fever` | int | 0=No, 1=Unsure, 2=Yes | 2 | Cardinal TB symptom |
| `night_sweats` | int | 0=No, 1=Unsure, 2=Yes | 2 | Cardinal TB symptom |
| `weight_loss` | int | 0=No, 1=Unsure, 2=Yes (unintended) | 2 | Cardinal TB symptom |
| `hemoptysis` | int | 0=No, 1=Unsure, 2=Yes (coughing blood) | 2 | **RED FLAG** (Triggers `URGENT`) |
| `tb_contact` | int | 0=No, 1=Unsure, 2=Yes (household contact) | 2 | **High Risk** factor |
| `diabetes` | int | 0=No, 1=Unsure, 2=Yes | 2 | Comorbidity factor |
| `hiv` | int | 0=No, 1=Unsure, 2=Yes | 2 | **High Risk** (Immunocompromised) |
| `immunosuppression`| int | 0=No, 1=Unsure, 2=Yes | 1 | **High Risk** factor |
| `silica_exposure` | int | 0=No, 1=Unsure, 2=Yes (mining/stone) | 1 | Occupational risk factor |
| **TOTAL MAX SCORE**| | | **18** | Aligned with NTEP/WHO Guidelines |

---

## 3. Stable Enums

### 3.1 Risk Tiers (`tier`)
- `LOW`: Clinical score <= 3 and calibrated audio prob <= 0.45.
- `MODERATE`: Clinical score 4–8, or escalated by audio prob > 0.45.
- `HIGH`: Clinical score > 8, or escalated to high by audio prob > 0.65.
- `HIGH_RISK_SCREENING`: High-risk factor present (HIV, immunosuppression, contact) with low clinical score.
- `URGENT`: Hemoptysis (coughing blood) safety override.

### 3.2 Machine-Readable Pathway Codes (`pathway_code`)
- `STANDARD_HYGIENE`: Low immediate risk; follow standard respiratory hygiene.
- `PHC_EVALUATION`: Persistent symptoms warrant primary health center clinical visit.
- `CBNAAT_REFERRAL`: High risk; prioritized referral for GeneXpert / CBNAAT molecular testing.
- `HIGH_RISK_PATHWAY`: Targeted contact tracing or immunosuppression screening pathway.
- `IMMEDIATE_TRIAGE`: Urgent medical emergency assessment required (hemoptysis).
- `PEDIATRIC_PATHWAY`: Patient < 18 years; route to pediatric TB protocol.

---

## 4. API Endpoints Specification

### 4.1 POST `/predict` (or `/screenings`)
**Content-Type:** `multipart/form-data`

#### Request Parameters
| Field | Type | Required | Default | Description |
| :--- | :--- | :---: | :---: | :--- |
| `file` | Binary (WAV) | **Yes** | — | 16 kHz mono WAV recording (~3 seconds). Max size 10MB. |
| `age` | Integer | **Yes** | 18 | Patient age in years. Age < 18 triggers 400 pediatric gate. |
| `sex` | String | No | `"prefer_not_to_say"` | `"male"`, `"female"`, `"other"`, `"prefer_not_to_say"` |
| `village` | String | No | `"Unknown"` | Village or PHC sector code |
| `cough_duration` | Integer | No | 0 | 0=No, 1=Unsure, 2=Yes |
| `fever` | Integer | No | 0 | 0=No, 1=Unsure, 2=Yes |
| `night_sweats` | Integer | No | 0 | 0=No, 1=Unsure, 2=Yes |
| `weight_loss` | Integer | No | 0 | 0=No, 1=Unsure, 2=Yes |
| `hemoptysis` | Integer | No | 0 | 0=No, 1=Unsure, 2=Yes |
| `tb_contact` | Integer | No | 0 | 0=No, 1=Unsure, 2=Yes |
| `diabetes` | Integer | No | 0 | 0=No, 1=Unsure, 2=Yes |
| `hiv` | Integer | No | 0 | 0=No, 1=Unsure, 2=Yes |
| `immunosuppression`| Integer | No | 0 | 0=No, 1=Unsure, 2=Yes |
| `silica_exposure` | Integer | No | 0 | 0=No, 1=Unsure, 2=Yes |
| `include_gradcam` | Boolean | No | `false` | If true, returns base64 Grad-CAM spectrogram overlay. |

---

### 4.2 Response Shapes

#### 200 OK — Standard Success (LOW / MODERATE / HIGH / URGENT)
```json
{
  "status": "success",
  "session_id": "4a7c8b2e-091f-4b0d-85f2-98e3b7b51201",
  "patient_demographics": {
    "age": 28,
    "sex": "male",
    "village": "Rampur",
    "bias_note": "Excluded from scoring to prevent algorithmic bias."
  },
  "questionnaire_score": 0,
  "questionnaire_max": 18,
  "red_flag_detected": false,
  "high_risk_factors_present": false,
  "uncertain_symptoms": [],
  "audio_model": {
    "target": "respiratory_abnormality_proxy",
    "raw_score": 0.0174,
    "calibrated_score": 0.0637,
    "tb_probability_validated": false
  },
  "fusion": {
    "status": "finalized",
    "tier": "LOW"
  },
  "pathway_code": "STANDARD_HYGIENE",
  "recommended_pathway": "Low immediate risk. Maintain standard respiratory hygiene.",
  "clinical_note": "This is a screening support tool, not a diagnostic. Final decision requires clinician review.",
  "gradcam_image": null
}
```

#### 200 OK — With Grad-CAM Visualization (`include_gradcam=true`)
```json
{
  "status": "success",
  "session_id": "8c1e2f3a-1234-5678-abcd-ef0123456789",
  "...": "...",
  "fusion": {
    "status": "finalized",
    "tier": "MODERATE"
  },
  "pathway_code": "PHC_EVALUATION",
  "gradcam_image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAg..."
}
```

#### 400 Bad Request — Pediatric Protocol Gate
```json
{
  "status": "error",
  "error_code": "PEDIATRIC_PATIENT",
  "message": "Patient is under 18. Pediatric TB screening requires a different clinical pathway.",
  "action": "route_to_pediatric_protocol",
  "pathway_code": "PEDIATRIC_PATHWAY"
}
```

#### 400 Bad Request — Audio Quality Gate (Clipping / Silence)
```json
{
  "status": "error",
  "error_code": "AUDIO_QUALITY_REJECTED",
  "message": "Audio is clipping (distorted). Please move the microphone further away.",
  "action": "request_new_recording",
  "pathway_code": null
}
```

#### 500 Internal Server Error
```json
{
  "status": "error",
  "error_code": "SERVER_ERROR",
  "message": "Failed to process audio or run model inference.",
  "action": "retry_or_contact_admin"
}
```

---

## 5. Performance Benchmarks (Observed on Standard CPU)

| Metric | Measured Value | Notes |
| :--- | :---: | :--- |
| **Initial Cold-Start (HF Download)** | **47.97 s** | Downloads `late_fusion_model.pth` (9.85 MB) |
| **Warm Start (Local Cached Weights)** | **< 1.0 s** | Using `local_files_only=True` bypasses HF network check |
| **Inference Latency (Standard)** | **~290 – 350 ms** | Bandpass filter + VAD + Log-mel spectrogram + MobileNetV2 |
| **Inference Latency (With Grad-CAM)** | **~1200 ms** | Includes PyTorch backward hook and JET colormap resize |
| **Grad-CAM Payload Size** | **4.67 KB** | Optimized JPEG quality 60, base64 data URI |
| **Audio Gate Check Time** | **< 10 ms** | Rejects silence/clipping before deep learning pipeline |
