"""Paths and strict, atomic output helpers. Imports never start a job."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TASK = "coswara_respiratory_abnormality_proxy"
SEED = 42

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def write_json(path: Path, data: dict) -> None:
    payload = json.dumps(data, indent=2, allow_nan=False) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)

def run_cli(main) -> None:
    try:
        main()
    except (ValueError, FileNotFoundError, RuntimeError, ImportError, OSError) as error:
        raise SystemExit(f"ShwaasAI: {error}") from None
