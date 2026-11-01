"""Freeze participant splits once; every experiment consumes this manifest."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split
from src.common import ROOT, SEED, run_cli, sha256_file, write_json

SPLITS = {"train", "validation", "test"}

def read_manifest(path: Path, require_splits: bool = True) -> pd.DataFrame:
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}. Run python -m src.prepare first.")
    frame = pd.read_csv(path, dtype={"participant_id": str, "recording_id": str})
    required = {"participant_id", "recording_id", "audio_path", "label", "audio_sha256"}
    if require_splits:
        required.add("split")
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Manifest is missing columns: {sorted(missing)}")
    if frame.empty or frame[list(required)].isna().any().any():
        raise ValueError("Manifest is empty or has missing required values.")
    for column in ("participant_id", "recording_id", "audio_path", "audio_sha256"):
        if frame[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"Empty values in {column}.")
    if frame.recording_id.duplicated().any():
        raise ValueError("Duplicate recording IDs.")
    if not set(frame.label).issubset({0, 1}) or frame.label.nunique() != 2:
        raise ValueError("Manifest must contain binary labels 0 and 1.")
    if frame.groupby("participant_id").label.nunique().max() != 1:
        raise ValueError("A participant has conflicting labels.")
    if frame.groupby("audio_sha256").participant_id.nunique().max() > 1:
        raise ValueError("Identical audio is assigned to different participants.")
    frame["audio_path"] = frame.audio_path.map(
        lambda p: str((path.parent / p).resolve()) if not Path(p).is_absolute() else p
    )
    if require_splits:
        if set(frame.split) != SPLITS:
            raise ValueError("Manifest must contain train, validation and test splits.")
        if frame.groupby("participant_id").split.nunique().max() != 1:
            raise ValueError("Participant leakage: one person appears in multiple splits.")
        for split, group in frame.groupby("split"):
            if group.label.nunique() != 2:
                raise ValueError(f"Both classes are required in {split}.")
    return frame

def assign_splits(frame: pd.DataFrame, seed: int = SEED) -> pd.DataFrame:
    participants = frame[["participant_id", "label"]].drop_duplicates()
    try:
        train, remainder = train_test_split(
            participants, test_size=0.30, stratify=participants.label, random_state=seed
        )
        validation, test = train_test_split(
            remainder, test_size=0.50, stratify=remainder.label, random_state=seed
        )
    except ValueError as error:
        raise ValueError("Too few participants per class for stratified 70/15/15 splits.") from error
    mapping = {pid: split for split, group in
               (("train", train), ("validation", validation), ("test", test))
               for pid in group.participant_id}
    result = frame.copy()
    result["split"] = result.participant_id.map(mapping)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/manifest_raw.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data/manifest.csv")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError(f"{args.output} exists. Reuse it or choose a new output filename.")
    frame = assign_splits(read_manifest(args.input, require_splits=False), args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    read_manifest(args.output)
    write_json(args.output.with_suffix(".json"), {
        "seed": args.seed, "manifest_sha256": sha256_file(args.output),
        "participants": frame.groupby("split").participant_id.nunique().to_dict(),
        "recordings": frame.groupby("split").size().to_dict(),
    })
    print(f"Saved {args.output}; reuse this exact manifest for every model.")

if __name__ == "__main__":
    run_cli(main)
