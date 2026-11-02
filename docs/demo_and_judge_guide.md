# 🎙️ ShwaasAI — Live Demo Script & Judge Defense Guide
**Event:** INNOTECH 2026 | **Team:** KARTAVYA  
**Focus:** Frontline ASHA Mobile App, Two-Channel Triage, Clinical Rule Safety, and Hardware Audio Link.

---

## 1. 2-to-3 Minute Live Presentation Script

### Step 1: Context & The Rural Problem (30 seconds)
> *"Judges, in rural India, Tuberculosis remains a persistent public health emergency with India accounting for 27% of the global burden. Frontline ASHA workers currently rely on manual symptom questioning, leading to high false-negative rates and over 44% of presumptive cases lost to follow-up. ShwaasAI provides an offline-first, multimodal triage assistant that pairs cough acoustics with WHO symptom histories right on the frontline phone."*

### Step 2: Patient Consent & Intake (30 seconds)
> *"Opening the app in Hindi or English, the ASHA worker begins with an informed consent screen. We collect basic demographics—notice that if a patient is under 18, our pediatric gate immediately directs them to specialized clinical protocols, preventing inappropriate algorithmic screening on minors."*

### Step 3: WHO Two-Channel Questionnaire (30 seconds)
> *"The worker conducts a 10-symptom questionnaire with simple Yes, No, and Unsure buttons. If an emergency red flag like Hemoptysis (coughing blood) is marked, the safety rule engine overrides acoustic scores to mandate immediate hospital triage. Notice how 'Unsure' responses do not penalize the score, but are flagged for doctor review."*

### Step 4: Acoustic Capture & Dynamic Escalation (45 seconds)
> *"Next is the 3-second cough recording. We can record directly via the phone mic or pull high-fidelity audio from our ESP32 acoustic horn over Wi-Fi. Our client-side quality gate immediately checks for clipping and silence before uploading.*
> 
> *Our backend processes the 16kHz spectrogram through a MobileNetV2 acoustic proxy model. Under our dynamic escalation engine, if acoustic confidence exceeds the context threshold, a borderline moderate case is safely escalated to priority GeneXpert / CBNAAT molecular testing.*
> 
> *We also display an explainable Grad-CAM heatmap so frontline workers understand the acoustic basis of the result."*

### Step 5: Privacy & Offline Sync (15 seconds)
> *"Audio is never retained—it is discarded immediately after feature extraction. Results are stored offline with anonymous patient codes and automatically sync with the PHC referral tracker when connectivity returns."*

---

## 2. Judge Questions & Bulletproof Answers

### Q1: "Why do you call this a 'Respiratory Abnormality Proxy' instead of TB Detection?"
> **Answer:** *"Responsible AI in healthcare requires diagnostic honesty. True open-source datasets with microbiologically confirmed TB cough audio are limited. Our acoustic encoder is trained and evaluated on the Coswara dataset for respiratory abnormality discrimination (AUROC 0.791). We combine this with an NTEP-aligned clinical rule engine for holistic triage, explicitly reminding workers that this is a prioritization tool, not a diagnostic confirmation."*

### Q2: "How did you pick the thresholds (0.02 vs 0.45 / 0.65 / 0.85)?"
> **Answer:** *"The 0.02 threshold was an uncalibrated operating point for the raw binary classifier on the training split. In our production pipeline, we applied Temperature Scaling (T=1.5) to calibrate probabilities into realistic distributions, coupled with a Two-Channel Dynamic Escalator where clinical tier modulates the required acoustic confidence: 0.45 for Low Risk, 0.65 for Moderate, and 0.85 for High."*

### Q3: "What happens if there is no internet in the village?"
> **Answer:** *"The Flutter app is 100% offline-first. It includes a built-in mock inference engine for emergency offline operation, local SQLite/SharedPreferences storage, and an automatic sync queue that holds pending records until the worker returns to network coverage at the PHC."*

### Q4: "What about patient privacy and voice biometric leakage?"
> **Answer:** *"We enforce three privacy guarantees: First, raw audio recordings are unlinked and destroyed in RAM immediately upon feature extraction. Second, patients are tracked only by anonymized codes (e.g. PAT-RAM-1042) rather than names or Aadhaar numbers. Third, informed verbal/written consent is an enforced prerequisite before any recording begins."*

---

## 3. How to Run the Project Locally

### 1. Launch Production Backend
```bash
source .venv/bin/activate
PYTHONPATH=. uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```
- Swagger UI Documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Seeded test accounts: `asha_rani` / `asha123`, `admin` / `admin123`

### 2. Launch Mock Server (Zero-CPU Mode)
```bash
source .venv/bin/activate
python3 server/mock_server.py
```
- Runs at `http://localhost:8001` with preloaded fixture branches.

### 3. Launch Flutter Mobile App
```bash
cd mobile
/home/anuj-gope/flutter/bin/flutter run -d linux
# Or connect an Android phone with USB debugging enabled:
/home/anuj-gope/flutter/bin/flutter run -d <device_id>
```
