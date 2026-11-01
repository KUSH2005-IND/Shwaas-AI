"""Cache one identified feature vector per recording for baseline/HeAR heads."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from src.audio import FRONTEND_VERSION, load_audio, mel_summary
from src.common import ROOT, run_cli, sha256_file, write_json
from src.manifest import read_manifest

def extract_features(manifest: Path, output: Path, encoder="mel", allow_download=False, revision=None):
    manifest, output = Path(manifest), Path(output)
    if output.suffix != ".npz":
        raise ValueError("Feature output must end in .npz.")
    frame = read_manifest(manifest)
    if output.exists() or output.with_suffix(".json").exists():
        raise ValueError(f"{output} exists. Use a new cache filename instead of overwriting an experiment.")
    hear = None
    if encoder == "hear":
        from src.hear import HeAREncoder
        hear = HeAREncoder(revision=revision, allow_download=allow_download)
    elif encoder != "mel":
        raise ValueError("Encoder must be mel or hear.")
    vectors = []
    for row in frame.itertuples():
        if sha256_file(Path(row.audio_path)) != row.audio_sha256:
            raise ValueError(f"Audio checksum mismatch: {row.recording_id}. Rebuild the manifest.")
        y = load_audio(row.audio_path)
        vectors.append(hear.encode(y) if hear else mel_summary(y))
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output, X=np.stack(vectors), recording_id=frame.recording_id.to_numpy(dtype=str),
        participant_id=frame.participant_id.to_numpy(dtype=str), label=frame.label.to_numpy(dtype=int),
        split=frame.split.to_numpy(dtype=str),
    )
    write_json(output.with_suffix(".json"), {
        "encoder": encoder, "frontend_version": FRONTEND_VERSION,
        "manifest_sha256": sha256_file(manifest),
        "features_sha256": sha256_file(output),
        "hear_revision": hear.revision if hear else None,
        "n_recordings": len(frame), "n_participants": int(frame.participant_id.nunique()),
    })

def read_features(path: Path, manifest: Path):
    meta_path = path.with_suffix(".json")
    if not path.is_file() or not meta_path.is_file():
        raise FileNotFoundError(f"Missing feature cache {path}. Run python -m src.features first.")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    required = {"manifest_sha256", "features_sha256", "frontend_version", "encoder"}
    if not isinstance(meta, dict) or not required.issubset(meta):
        raise ValueError("Feature metadata is incomplete; rebuild the cache.")
    if meta["encoder"] not in {"mel", "hear"}:
        raise ValueError("Unknown cached encoder.")
    if meta["features_sha256"] != sha256_file(path):
        raise ValueError("Feature cache checksum mismatch; rebuild it.")
    frame = read_manifest(manifest)
    if meta["manifest_sha256"] != sha256_file(manifest):
        raise ValueError("Feature cache belongs to a different manifest.")
    if meta["frontend_version"] != FRONTEND_VERSION:
        raise ValueError("Frontend version changed; rebuild the feature cache.")
    with np.load(path, allow_pickle=False) as data:
        X = data["X"].copy()
        for column in ("recording_id", "participant_id", "label", "split"):
            if not np.array_equal(data[column], frame[column].to_numpy()):
                raise ValueError(f"Feature-cache alignment failed for {column}.")
    if X.ndim != 2 or len(X) != len(frame) or not np.isfinite(X).all():
        raise ValueError("Invalid feature matrix.")
    expected = 512 if meta["encoder"] == "hear" else 68
    if X.shape[1] != expected:
        raise ValueError(f"Expected {expected} features, got {X.shape[1]}.")
    return frame, X, meta

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.csv")
    parser.add_argument("--encoder", choices=("mel", "hear"), default="mel")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--hear-revision")
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()
    output = args.output or ROOT / f"cache/{args.encoder}_features.npz"
    extract_features(args.manifest, output, args.encoder, args.allow_download, args.hear_revision)
    print(f"Saved {output}. Next: python -m src.train --features {output}")

if __name__ == "__main__":
    run_cli(main)
