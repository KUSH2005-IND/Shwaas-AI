# ShwaasAI

ShwaasAI combines cough acoustic analysis, a structured questionnaire and an
explainable referral workflow for frontline screening. The acoustic experiment
uses the versioned **Coswara respiratory-abnormality proxy** in src/labels.py.
The TB screening workflow is the intended application; the current acoustic
score is a proxy score.

## Changes in v0.2

- A frozen manifest keeps participants separate across training, validation and test.
- Audio-only MobileNetV2, mel-summary logistic regression and optional frozen HeAR
  use the same manifest and evaluation.
- Label-generated questionnaire inputs were removed from performance experiments.
- Shared waveform/mel processing is used offline and in the API.
- Calibration and finite operating thresholds are selected on validation data only.
- Versioned bundles bind model weights, frontend, manifest, calibration and threshold.
- API startup performs no model download. Questionnaire routing continues when
  audio or weights are unavailable.
- Old fusion classes remain loadable in src/model.py. New training and serving
  use new audio-only bundles.
- Old reports remain historical; see reports/README.md.

## 1. Install

Use a fresh **Python 3.11 or 3.12** environment. Run commands from the repository root.

Windows PowerShell:

    py -3.12 -m venv .venv
    .venv\Scripts\Activate.ps1

Linux/macOS:

    python3.12 -m venv .venv
    source .venv/bin/activate

Then:

    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    python -m pip install --no-deps -e .

The mel/logistic-regression pipeline does not require PyTorch. For CNN or HeAR
on Windows/Linux CPU, install this matched pair:

    python -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu

GPU/Colab installations need a matched torch/torchvision pair for that runtime.
The checks here use the CPU pair above. ARM/macOS require platform-appropriate wheels.

## 2. Prepare identified Coswara recordings

    python -m pip install -r requirements-data.txt
    python -m src.prepare
    python -m src.manifest

The exporter resolves a dataset commit, reads the audio configuration with decoding
disabled, and keeps participant ID, health-status label, recording type and quality
attached to each row. It writes canonical WAVs and data/manifest_raw.csv.
No labels are joined to an independently reconstructed positional row index.

The default HF source partition is train, matching the earlier experiment source.
Internal participant partitions are then created within that source. These are
internal research partitions, not the publisher's external test set.

The second command writes data/manifest.csv once. Both cough types and every
window from a participant stay together. Reuse it for all experiments. Existing
manifest, feature-cache, model and report outputs are not silently overwritten;
choose a new filename/directory for a new experiment.

For local WAVs, supply a CSV containing participant_id, recording_id, audio_path,
label (0/1) and audio_sha256 (SHA-256 of the file), then:

    python -m src.manifest --input your_manifest.csv

Relative audio paths resolve against that CSV's directory. Old spectrograms.pt is
not reused because it cannot establish the new waveform processing or a fresh
training split. Rebuild from identified audio once.

## 3. Train the inexpensive baseline first

    python -m src.features --encoder mel
    python -m src.train --encoder mel
    python -m src.evaluate --model artifacts/mel --features cache/mel_features.npz
    python -m src.plot --evaluation artifacts/mel/evaluation

This baseline is mel-summary + logistic regression, not MFCC. Scaling is fitted
on training features only. A small regularization grid is selected using validation
AUROC. A positive-slope sigmoid calibrator and operating threshold are fitted on
validation data, never the test partition.

The threshold maximizes validation sensitivity subject to the requested specificity.
The default specificity of 0.90 is an experiment setting, not a clinical claim.
If no positive operating point meets it, the result can honestly show zero sensitivity
with a finite all-negative threshold.

The optional features argument measures the cached head only and excludes encoder
latency. To measure waveform-to-score execution:

    python -m src.evaluate --model artifacts/mel --output artifacts/mel/waveform_evaluation

Reports include recording metrics, secondary participant mean-probability metrics,
participant-bootstrap AUROC intervals, predictions and the frozen threshold.
The API scores one uploaded recording; participant aggregation describes the
available research recordings. Develop with validation results; repeatedly selecting
models from test results invalidates the final holdout.

## 4. Add frozen HeAR

Accept the terms at https://huggingface.co/google/hear-pytorch first.
Weights are governed by Google's Health AI Developer Foundations terms and are
separate from the Apache-licensed frontend code vendored here.

    python -m pip install -r requirements-hear.txt
    python -c "from huggingface_hub import login; login()"
    python -m src.features --encoder hear --allow-download
    python -m src.train --encoder hear
    python -m src.evaluate --model artifacts/hear --features cache/hear_features.npz
    python -m src.plot --evaluation artifacts/hear/evaluation

Two-second, 16 kHz mono activity windows use the pinned official PCEN frontend and
frozen HeAR. Mean window embeddings produce one 512-dimensional vector per recording.
A new logistic-regression head is trained on those vectors. The actual model commit
is recorded and reused during serving.

The official frontend normalizes across its batch; applying it separately per window
avoids dependence on unrelated recordings. Model inference uses batches of four
to limit activation memory. The activity selector removes silence; it does not
establish cough identity. Speech/noise require recording instructions, inspection
and future cough-detector work.

Run HeAR on a server/Colab initially. No phone deployment or speed claim is made.

## 5. Train the audio-only CNN comparison

    python -m src.train --encoder cnn --epochs 20 --patience 5
    python -m src.evaluate --model artifacts/cnn
    python -m src.plot --evaluation artifacts/cnn/evaluation

MobileNetV2 initializes without pretrained weights. Its new head outputs logits and
uses BCEWithLogitsLoss, training-only class weighting, AdamW, seeds, validation
checkpoint selection and early stopping. Training samples an activity window per
recording visit; evaluation and serving average window logits. No synthetic
questionnaire answers are generated. Use suitable hardware for substantial training.

## 6. Run the API

The default bundle is artifacts/mel.

    python -m uvicorn src.api:app --host 127.0.0.1 --port 8000

Open http://127.0.0.1:8000/docs and http://127.0.0.1:8000/health.
A functioning questionnaire service may report audio_bundle_loaded: false.
For HeAR, a loaded head does not prove encoder weights are cached. The first audio
request loads cached-only weights and reports unavailable if they are missing.

Choose a different model in PowerShell:

    $env:SHWAAS_MODEL_DIR = "artifacts/hear"
    python -m uvicorn src.api:app --host 127.0.0.1 --port 8000

Linux/macOS:

    SHWAAS_MODEL_DIR=artifacts/hear python -m uvicorn src.api:app --host 127.0.0.1 --port 8000

POST /screen (or /predict) accepts multipart fields:

- questionnaire: JSON text containing raw answers.
- file: optional WAV/FLAC. Collect 3–10 seconds in the app. Decoding is bounded to
  30 seconds/10 MB; audio quality checks assess usability, not cough identity.

Example questionnaire:

    {"age":35,"sex":"male","cough_duration_days":21,"fever":true,
     "night_sweats":false,"weight_loss":null,"hemoptysis":false,
     "tb_contact":false,"diabetes":false,"hiv":null,
     "immunosuppression":false,"silica_exposure":false}

Use booleans/null rather than numeric question weights. Unknown is separate from no.
The previous weighted integer form fields and Grad-CAM response are not part of
this contract. Update clients to send the JSON field above. /predict preserves the
URL, not the old request schema.

Outputs separate audio_model, audio_quality, priority, reasons, unknown_answers,
channels_disagree and rules_version. Acoustic scores cannot cancel questionnaire
triggers. Reported hemoptysis retains priority even when audio fails.

Rules in src/rules.py are an explicit prototype configuration for clinical review,
not a validated WHO/NTEP score. Assistants can explain the outputs; an LLM does not
set thresholds or referral rules.

Authentication, patient storage, encryption-at-rest, clinician assignment and
Ni-kshay synchronization remain application-layer work in the broader workflow.
Run this endpoint locally. Load only trusted bundles you trained: joblib executes
Python during deserialization.

## 7. Run regression checks

    python -m pip install -r requirements-test.txt
    python -m pytest -q

PyTorch checks skip if torch is absent. With the matched CPU pair installed, checks
include a full synthetic baseline run, one-epoch CNN training, the actual HeAR
frontend with a test encoder, cache identity, finite thresholds, API scoring and
routing with missing/invalid audio.

Synthetic recordings establish software behaviour only. Actual gated HeAR weights
and the Coswara benchmark must run separately. CI is configured for Python 3.11/3.12.

Compatibility module commands such as python -m src.embed and
python -m src.evaluate_audio_only delegate to the new entry points; use --help.
Imports do not start training or download data.
