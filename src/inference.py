"""Load local versioned bundles only. Legacy checkpoints are never substituted."""
from __future__ import annotations
import json
from threading import Lock
from pathlib import Path
import numpy as np
from src.audio import FRONTEND_VERSION, load_audio, mel_images, mel_summary
from src.common import TASK, sha256_file
from src.metrics import calibrate

class Predictor:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self._lock = Lock()
        metadata = self.directory / "bundle.json"
        if not metadata.is_file():
            raise FileNotFoundError(f"Missing {metadata}; train a new versioned audio-only bundle.")
        self.meta = json.loads(metadata.read_text(encoding="utf-8"))
        required = {"format_version", "task", "kind", "frontend_version", "threshold",
                    "calibration", "weights_sha256", "model_version", "manifest_sha256"}
        if not isinstance(self.meta, dict) or not required.issubset(self.meta):
            raise ValueError("Bundle metadata is incomplete.")
        if self.meta.get("format_version") != 1 or self.meta.get("task") != TASK:
            raise ValueError("Unsupported bundle format or task.")
        if self.meta.get("frontend_version") != FRONTEND_VERSION:
            raise ValueError("Bundle frontend mismatch; retrain with the current audio frontend.")
        threshold = self.meta.get("threshold")
        calibration = self.meta.get("calibration", {})
        if not isinstance(threshold, (int, float)) or not np.isfinite(threshold):
            raise ValueError("Bundle threshold must be finite.")
        if not all(np.isfinite(calibration.get(k, np.nan)) for k in ("scale", "bias")) or calibration["scale"] <= 0:
            raise ValueError("Bundle calibration parameters are invalid.")
        self.kind = self.meta["kind"]
        if self.kind not in {"cnn", "mel-logreg", "hear-logreg"}:
            raise ValueError(f"Unsupported model kind: {self.kind}")
        name = "model.pt" if self.kind == "cnn" else "model.joblib"
        path = self.directory / name
        if sha256_file(path) != self.meta["weights_sha256"]:
            raise ValueError("Model checksum mismatch; bundle is incomplete or changed.")
        self.hear = None
        if self.kind in {"mel-logreg", "hear-logreg"}:
            import joblib
            # Only load bundles you trained/trust: joblib is executable pickle.
            self.model = joblib.load(path)
            if self.kind == "hear-logreg" and not self.meta.get("hear_revision"):
                raise ValueError("HeAR bundle is missing its pinned model revision.")
        elif self.kind == "cnn":
            import torch
            from src.model import AudioOnlyModel
            self.model = AudioOnlyModel()
            self.model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True), strict=True)
            self.model.eval()
        else:
            raise ValueError(f"Unsupported model kind: {self.kind}")

    def score_waveform(self, y):
        with self._lock:
            return self._score_waveform(y)

    def _score_waveform(self, y):
        if self.kind == "cnn":
            import torch
            windows = torch.from_numpy(mel_images(y))
            with torch.inference_mode():
                # The deployed score uses all activity windows, as does evaluation.
                raw = float(self.model(windows).reshape(-1).mean())
        else:
            if self.kind == "hear-logreg" and self.hear is None:
                from src.hear import HeAREncoder
                self.hear = HeAREncoder(revision=self.meta["hear_revision"])
            vector = self.hear.encode(y) if self.hear else mel_summary(y)
            raw = float(self.model.decision_function(vector[None])[0])
        score = float(calibrate([raw], self.meta["calibration"])[0])
        if not np.isfinite(score):
            raise RuntimeError("Model returned a non-finite score.")
        return {
            "status": "available", "target": TASK, "score": score,
            "acoustic_flag": bool(score >= self.meta["threshold"]),
            "threshold": self.meta["threshold"], "model_version": self.meta["model_version"],
            "tb_probability_validated": False,
        }

    def predict_file(self, path):
        return self.score_waveform(load_audio(path))
