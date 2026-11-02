"""Generate evaluation figures from saved predictions, never hardcoded scores."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import ConfusionMatrixDisplay, PrecisionRecallDisplay, RocCurveDisplay
from src.common import run_cli

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", type=Path, required=True)
    args = parser.parse_args()
    directory = args.evaluation
    frame = pd.read_csv(directory / "predictions.csv")
    metadata = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    RocCurveDisplay.from_predictions(frame.label, frame.probability, ax=axes[0, 0])
    PrecisionRecallDisplay.from_predictions(frame.label, frame.probability, ax=axes[0, 1])
    ConfusionMatrixDisplay.from_predictions(frame.label, frame.prediction, ax=axes[1, 0])
    fraction, mean = calibration_curve(frame.label, frame.probability, n_bins=8, strategy="quantile")
    axes[1, 1].plot([0, 1], [0, 1], "--", color="gray")
    axes[1, 1].plot(mean, fraction, "o-")
    axes[1, 1].set(xlabel="Mean score", ylabel="Observed proxy-positive fraction", title="Reliability")
    fig.suptitle(metadata["model_version"] + " | held-out Coswara proxy task")
    fig.tight_layout()
    fig.savefig(directory / "evaluation.png", dpi=160)
    plt.close(fig)
    print(f"Saved {directory / 'evaluation.png'}")

if __name__ == "__main__":
    run_cli(main)
