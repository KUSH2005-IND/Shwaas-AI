"""Evaluate an unchanged bundle on the exact frozen test participants."""
from __future__ import annotations
import argparse
from pathlib import Path
import time
import numpy as np
from src.common import ROOT, run_cli, sha256_file, write_json
from src.features import read_features
from src.inference import Predictor
from src.manifest import read_manifest
from src.metrics import bootstrap_auc, calibrate, metrics, participant_predictions

def evaluate_bundle(model_dir, manifest, output=None, features=None, bootstrap=500):
    model_dir, manifest = Path(model_dir), Path(manifest)
    output = Path(output) if output else model_dir / "evaluation"
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"{output} is not empty; choose a new report directory.")
    if bootstrap < 1:
        raise ValueError("Bootstrap repeats must be positive.")
    predictor = Predictor(model_dir)
    frame = read_manifest(manifest)
    if predictor.meta["manifest_sha256"] != sha256_file(manifest):
        raise ValueError("Model and evaluation manifest differ; evaluation would not be held out.")
    test = frame[frame.split == "test"].copy()
    start = time.perf_counter()
    if features:
        if predictor.kind == "cnn":
            raise ValueError("CNN evaluation uses waveform inference, not a feature cache.")
        cached_frame, X, meta = read_features(Path(features), manifest)
        if predictor.kind != f"{meta['encoder']}-logreg" or meta.get("hear_revision") != predictor.meta.get("hear_revision"):
            raise ValueError("Feature cache and model encoder/revision differ.")
        scores = predictor.model.decision_function(X[cached_frame.split.eq("test")])
        probabilities = calibrate(scores, predictor.meta["calibration"])
        timing_scope = "cached_head_only_excludes_audio_and_encoder"
    else:
        for row in test.itertuples():
            if sha256_file(Path(row.audio_path)) != row.audio_sha256:
                raise ValueError(f"Audio checksum mismatch: {row.recording_id}.")
        probabilities = [predictor.predict_file(row.audio_path)["score"] for row in test.itertuples()]
        timing_scope = "waveform_decode_encoder_head"
    elapsed = time.perf_counter() - start
    predictions = test[["recording_id", "participant_id", "label", "split"]].copy()
    predictions["probability"] = np.asarray(probabilities)
    threshold = predictor.meta["threshold"]
    predictions["prediction"] = predictions.probability.ge(threshold).astype(int)
    participant = participant_predictions(predictions)
    report = {
        "task": predictor.meta["task"], "model_version": predictor.meta["model_version"],
        "manifest_sha256": predictor.meta["manifest_sha256"],
        "n_test_participants": int(test.participant_id.nunique()),
        "recording_metrics": metrics(predictions.label, predictions.probability, threshold),
        "participant_mean_probability_metrics": metrics(participant.label, participant.probability, threshold),
        "recording_auroc_participant_bootstrap_95ci": bootstrap_auc(predictions, bootstrap),
        "seconds_per_recording": elapsed / len(test), "timing_scope": timing_scope,
        "calibration_and_threshold_selected_on": "validation",
    }
    output.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output / "predictions.csv", index=False)
    participant.to_csv(output / "participant_predictions.csv", index=False)
    write_json(output / "metrics.json", report)
    print(f"Saved {output}; test AUROC={report['recording_metrics']['auroc']:.3f}")
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.csv")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--features", type=Path, help="Optional cached-head evaluation; excludes encoder latency")
    parser.add_argument("--bootstrap", type=int, default=500)
    args = parser.parse_args()
    evaluate_bundle(args.model, args.manifest, args.output, args.features, args.bootstrap)

if __name__ == "__main__":
    run_cli(main)
