# src/evaluate_audio_only.py
import torch
import numpy as np
import json
from pathlib import Path
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import roc_auc_score, roc_curve, average_precision_score
from model import LateFusionTBModel

# --- ROBUST PATHING ---
PROJECT_ROOT = Path(__file__).parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

print("🔬 Starting TRUE Audio-Only Evaluation (Participant-Grouped)...")

# 1. Load the cached spectrograms
print("📥 Loading cached data...")
cached_data = torch.load(CACHE_DIR / "spectrograms.pt", weights_only=True)

audio_tensors = []
labels = []
participant_ids = []

for item in cached_data:
    audio_tensors.append(item['tensor'])
    labels.append(item['label'])
    participant_ids.append(item['participant_id'])

audio_tensors = torch.stack(audio_tensors)
labels = np.array(labels)
participant_ids = np.array(participant_ids)

print(f"✅ Loaded {len(labels)} recordings from {len(np.unique(participant_ids))} unique participants.")

# 2. STRICT PARTICIPANT-LEVEL SPLIT
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(audio_tensors, labels, groups=participant_ids))

X_test, y_test = audio_tensors[test_idx], labels[test_idx]
test_participants = participant_ids[test_idx]

print(
    f"🔐 Evaluating on held-out test set: {len(y_test)} recordings from {len(np.unique(test_participants))} participants")

# 3. Load the Trained Model
print("🧠 Loading trained Late-Fusion model...")
device = torch.device("cpu")
model = LateFusionTBModel().to(device)
model.load_state_dict(torch.load(CACHE_DIR / "late_fusion_model.pth", weights_only=True))
model.eval()

# 4. Run Inference on the Test Set (AUDIO ONLY)
print("🏃 Running inference with NEUTRAL tabular input (zeros)...")
probabilities = []
batch_size = 32

with torch.no_grad():
    for i in range(0, len(X_test), batch_size):
        batch_audio = X_test[i:i + batch_size].to(device)

        # THE FIX: Pass zeros to the tabular branch to isolate audio performance
        batch_tab = torch.zeros((len(batch_audio), 4), dtype=torch.float32).to(device)

        outputs = model(batch_audio, batch_tab).squeeze()
        probabilities.extend(outputs.cpu().numpy())

probabilities = np.array(probabilities)

# 5. Calculate the REAL Metrics
auc = roc_auc_score(y_test, probabilities)
ap = average_precision_score(y_test, probabilities)

# Find the threshold that gives ~90% specificity
fpr, tpr, thresholds = roc_curve(y_test, probabilities)
idx_90_spec = np.argmax(fpr <= 0.10)
sensitivity_at_90_spec = tpr[idx_90_spec] if len(tpr) > 0 else 0.0
best_threshold = thresholds[idx_90_spec] if len(thresholds) > 0 else 0.5

print("\n" + "=" * 60)
print("📊 TRUE AUDIO-ONLY EVALUATION RESULTS")
print("=" * 60)
print(f"   AUROC (Participant-Grouped):  {auc:.4f}")
print(f"   Average Precision:            {ap:.4f}")
print(f"   Sensitivity @ 90% Spec:       {sensitivity_at_90_spec:.4f} (Threshold: {best_threshold:.3f})")
print("=" * 60)
print("💡 NOTE: This is the honest performance of the CNN on the spectrograms alone.")
print("   In the real app, the clinical questionnaire will boost this score via fusion.")

# 6. Save the results
metrics = {
    "model": "Audio_CNN_Only (Tabular input zeroed)",
    "task": "respiratory_abnormality_proxy",
    "auroc": float(auc),
    "average_precision": float(ap),
    "sensitivity_at_90_specificity": float(sensitivity_at_90_spec),
    "threshold": float(best_threshold),
    "test_participants": int(len(np.unique(test_participants)))
}
(REPORTS_DIR / "true_audio_metrics.json").write_text(json.dumps(metrics, indent=2))
print(f"\n💾 Saved true audio metrics to reports/true_audio_metrics.json")
print("✅ Evaluation Complete.")