# src/baseline.py
from pathlib import Path
import json
import numpy as np
import pandas as pd
import torch
import joblib

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold, cross_val_predict
from sklearn.metrics import roc_auc_score, roc_curve, average_precision_score, brier_score_loss

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)
SEED = 42


def summarize(spec: np.ndarray) -> np.ndarray:
    """Turn a 224x224 log-mel image into a 68-d acoustic descriptor."""
    # spec axis 0 ≈ frequency, axis 1 ≈ time
    mean_profile = spec.mean(axis=1)
    std_profile = spec.std(axis=1)

    def bin_mean(v, n_bands=32):
        edges = np.linspace(0, len(v), n_bands + 1).astype(int)
        return np.array([v[edges[i]:edges[i + 1]].mean() for i in range(n_bands)])

    scalars = np.array([
        spec.mean(),                 # overall energy
        spec.std(),                  # dynamic range
        spec.max(),                  # peak activation
        spec.mean(axis=0).std(),     # burstiness over time
    ])

    return np.concatenate([bin_mean(mean_profile), bin_mean(std_profile), scalars])


def participant_bootstrap_auc(y, p, groups, n=1000, seed=SEED):
    """Resample PARTICIPANTS, never recordings."""
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    by_group = {g: np.flatnonzero(groups == g) for g in unique}
    vals = []

    for _ in range(n):
        picked = rng.choice(unique, size=len(unique), replace=True)
        idx = np.concatenate([by_group[g] for g in picked])
        if len(np.unique(y[idx])) == 2:
            vals.append(roc_auc_score(y[idx], p[idx]))

    return np.percentile(vals, [2.5, 97.5])


def sensitivity_at_specificity(y, p, target_spec=0.90):
    fpr, tpr, thr = roc_curve(y, p)
    valid = np.flatnonzero(fpr <= (1 - target_spec))
    if len(valid) == 0:
        return 0.0, 1.0
    best = valid[np.argmax(tpr[valid])]
    return float(tpr[best]), float(thr[best])


print("=" * 60)
print("📊 EXPERIMENT C — Statistical baseline (participant-grouped)")
print("=" * 60)

# ------------------------------------------------------------------
# 1. Load cached spectrograms
# ------------------------------------------------------------------
print("\n📥 Loading cached spectrograms...")
records = torch.load(CACHE / "spectrograms.pt", map_location="cpu", weights_only=True)
print(f"   {len(records)} recordings loaded")

X, y, groups = [], [], []
for r in records:
    spec = r["tensor"][0].numpy()  # all 3 channels are identical
    X.append(summarize(spec))
    y.append(int(r["label"]))
    groups.append(r["participant_id"])

X = np.stack(X).astype(np.float64)
y = np.array(y)
groups = np.array(groups)
del records

print(f"   Feature matrix: {X.shape}")
print(f"   Class balance:  {np.bincount(y).tolist()}")

# ------------------------------------------------------------------
# 2. Verify one label per participant
# ------------------------------------------------------------------
part_df = pd.DataFrame({"participant_id": groups, "label": y})
assert part_df.groupby("participant_id")["label"].nunique().max() == 1, \
    "A participant has conflicting labels — fix the label mapping first."

uniq = part_df["participant_id"].to_numpy()
uniq_y = part_df["label"].to_numpy()
print(f"   Unique participants: {len(uniq)}")

# ------------------------------------------------------------------
# 3. Participant-level HOLDOUT (never touched during development)
# ------------------------------------------------------------------
gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED)
tr_p, te_p = next(gss.split(uniq, uniq_y, groups=uniq))

train_participants = uniq[tr_p]
test_participants = uniq[te_p]

train_mask = np.isin(groups, train_participants)
test_mask = np.isin(groups, test_participants)

assert not set(groups[train_mask]) & set(groups[test_mask]), "LEAK: participant in both splits!"

print(f"\n🔐 Train participants: {len(train_participants)} | Test participants: {len(test_participants)}")
print(f"   Train recordings:  {train_mask.sum()} | Test recordings:  {test_mask.sum()}")

Xtr, ytr, gtr = X[train_mask], y[train_mask], groups[train_mask]
Xte, yte, gte = X[test_mask], y[test_mask], groups[test_mask]

# ------------------------------------------------------------------
# 4. Out-of-fold predictions INSIDE the training set
#    (used later for calibration + band cut-offs)
# ------------------------------------------------------------------
print("\n🔁 Running 5-fold StratifiedGroupKFold on training set...")
cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)

pipeline = make_pipeline(
    StandardScaler(),
    LogisticRegression(C=0.1, class_weight="balanced", max_iter=2000, random_state=SEED)
)

oof = cross_val_predict(
    pipeline, Xtr, ytr, groups=gtr, cv=cv, method="predict_proba"
)[:, 1]

cv_auc = roc_auc_score(ytr, oof)
print(f"   Training OOF AUROC: {cv_auc:.4f}")

# ------------------------------------------------------------------
# 5. Fit on train ONLY, evaluate on untouched test
# ------------------------------------------------------------------
print("\n🎯 Evaluating on held-out participants...")
pipeline.fit(Xtr, ytr)
p_test = pipeline.predict_proba(Xte)[:, 1]

auc = roc_auc_score(yte, p_test)
ci_low, ci_high = participant_bootstrap_auc(yte, p_test, gte)
ap = average_precision_score(yte, p_test)
brier = brier_score_loss(yte, p_test)
sens, threshold = sensitivity_at_specificity(yte, p_test, target_spec=0.90)

print("\n" + "=" * 60)
print("📊 BASELINE RESULTS — COSWARA PROXY TASK")
print("=" * 60)
print(f"   AUROC:                    {auc:.4f}  [95% CI: {ci_low:.4f} – {ci_high:.4f}]")
print(f"   Average Precision:        {ap:.4f}")
print(f"   Sensitivity @ 90% Spec:   {sens:.4f}  (threshold {threshold:.3f})")
print(f"   Brier score:              {brier:.4f}  (uncalibrated)")
print(f"   Test participants:        {len(np.unique(gte))}")
print("=" * 60)

# ------------------------------------------------------------------
# 6. Persist everything for the fusion stage
# ------------------------------------------------------------------
pred_df = pd.DataFrame({
    "participant_id": gte,
    "label": yte,
    "p_audio": p_test,
})
pred_df.to_csv(REPORTS / "baseline_test_predictions.csv", index=False)

oof_df = pd.DataFrame({
    "participant_id": gtr,
    "label": ytr,
    "p_audio_oof": oof,
})
oof_df.to_csv(REPORTS / "baseline_train_oof.csv", index=False)

joblib.dump(pipeline, CACHE / "baseline_pipeline.joblib")
np.save(CACHE / "baseline_X.npy", X)
np.save(CACHE / "baseline_y.npy", y)

metrics = {
    "experiment": "C_statistical_baseline",
    "task": "respiratory_abnormality_PROXY_NOT_TB",
    "n_recordings": int(len(y)),
    "n_participants": int(len(uniq)),
    "cv_auc": float(cv_auc),
    "test_auc": float(auc),
    "test_auc_ci": [float(ci_low), float(ci_high)],
    "average_precision": float(ap),
    "sensitivity_at_90_specificity": float(sens),
    "threshold": float(threshold),
    "brier_uncalibrated": float(brier),
    "split": "participant_grouped_75_25",
    "seed": SEED,
}
(REPORTS / "baseline_metrics.json").write_text(json.dumps(metrics, indent=2))

print("\n💾 Saved predictions, OOF probabilities, pipeline and metrics.")
print("✅ Baseline complete.")