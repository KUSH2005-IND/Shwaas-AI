"""Development-only nuisance baseline; association does not prove leakage."""
import argparse
from pathlib import Path
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from src.common import ROOT, run_cli
from src.manifest import read_manifest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.csv")
    args = parser.parse_args()
    frame = read_manifest(args.manifest)
    frame = frame[frame.split == "train"].copy()
    columns = [name for name in ("age", "quality_score") if name in frame]
    if not columns:
        raise ValueError("No age/quality columns in this manifest.")
    pipeline = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
        LogisticRegression(max_iter=2000),
    )
    if frame.groupby("label").participant_id.nunique().min() < 5:
        raise ValueError("Need five training participants per class for this check.")
    probabilities = cross_val_predict(
        pipeline, frame[columns], frame.label, groups=frame.participant_id,
        cv=StratifiedGroupKFold(5, shuffle=True, random_state=42), method="predict_proba",
    )[:, 1]
    print(f"Training-only nuisance AUROC: {roc_auc_score(frame.label, probabilities):.3f}")
    print("Inspect collection confounding; this alone neither proves nor excludes acoustic bias.")

if __name__ == "__main__":
    run_cli(main)
