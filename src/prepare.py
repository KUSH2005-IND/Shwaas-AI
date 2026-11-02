"""Export identified cough WAVs directly from one pinned Coswara revision."""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
from pathlib import Path
import pandas as pd
import soundfile as sf
from src.audio import assess_quality, load_audio
from src.common import ROOT, run_cli, sha256_file, write_json
from src.labels import LABEL_VERSION, map_label

def export_recordings(rows, output: Path, source_revision: str):
    """Each label stays attached to its row; no positional-index joins."""
    records, skipped, seen = [], Counter(), set()
    audio_dir = output.parent / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        label = map_label(row.get("covid_status"))
        if row.get("audio_type") not in {"cough-heavy", "cough-shallow"} or label < 0:
            skipped["type_or_label"] += 1
            continue
        if float(row.get("quality_score") or 0) < 1:
            skipped["dataset_quality"] += 1
            continue
        pid = str(row.get("participant_id") or "").strip()
        if not pid:
            raise ValueError("A cough row is missing participant_id.")
        recording_id = sha256(f"{pid}:{row['audio_type']}".encode()).hexdigest()[:24]
        if recording_id in seen:
            raise ValueError(f"Repeated participant/audio-type pair: {pid}, {row['audio_type']}")
        seen.add(recording_id)
        audio = row.get("audio")
        if not isinstance(audio, dict):
            raise ValueError("Expected undecoded audio dict. Use datasets.Audio(decode=False).")
        source = audio.get("bytes") or audio.get("path")
        if source is None:
            raise ValueError(f"Missing audio for {recording_id}.")
        path = audio_dir / f"{recording_id}.wav"
        try:
            y = load_audio(source)
            quality = assess_quality(y)
        except ValueError:
            skipped["decode_or_duration"] += 1
            continue
        if not quality.usable:
            skipped["waveform_quality"] += 1
            continue
        sf.write(path, y, 16000, subtype="FLOAT")
        records.append({
            "participant_id": pid, "recording_id": recording_id,
            "audio_path": str(path.resolve()), "label": label,
            "audio_type": row["audio_type"], "quality_score": row["quality_score"],
            "age": row.get("age"), "sex": row.get("gender"),
            "source_revision": source_revision, "label_version": LABEL_VERSION,
            "audio_sha256": sha256_file(path),
        })
    if not records:
        raise ValueError("No usable cough recordings. Check schema and quality filters.")
    frame = pd.DataFrame(records)
    frame.to_csv(output, index=False)
    return frame, dict(skipped)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="szzs1693/coswara-data")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--source-split", default="train", help="HF source partition, not experiment split")
    parser.add_argument("--output", type=Path, default=ROOT / "data/manifest_raw.csv")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError(f"{args.output} exists. Choose a new output directory to rebuild data.")
    try:
        from datasets import Audio, load_dataset
        from huggingface_hub import HfApi
    except ImportError as error:
        raise ImportError("Install requirements-data.txt to download Coswara.") from error
    try:
        revision = HfApi().dataset_info(args.dataset, revision=args.revision).sha
        rows = load_dataset(args.dataset, "audio", split=args.source_split, revision=revision)
        rows = rows.cast_column("audio", Audio(decode=False))
    except Exception as error:
        raise RuntimeError(f"Could not load Coswara. Check connectivity/access: {error}") from error
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame, skipped = export_recordings(rows, args.output, revision)
    write_json(args.output.with_suffix(".json"), {
        "dataset": args.dataset, "revision": revision, "source_split": args.source_split,
        "label_version": LABEL_VERSION, "recordings": len(frame),
        "participants": int(frame.participant_id.nunique()), "skipped": skipped,
    })
    print(f"Saved {len(frame)} recordings. Next: python -m src.manifest")

if __name__ == "__main__":
    run_cli(main)
