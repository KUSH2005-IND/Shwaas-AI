"""Synthetic audio is for software checks only, never biomedical performance."""
import numpy as np
import pandas as pd
import pytest
import soundfile as sf
from src.common import sha256_file
from src.features import extract_features
from src.manifest import assign_splits
from src.train import train_bundle

@pytest.fixture(scope="session")
def dataset(tmp_path_factory):
    directory = tmp_path_factory.mktemp("identified_audio")
    rng = np.random.default_rng(123)
    rows = []
    t = np.arange(48000) / 16000
    for person in range(40):
        label = person % 2
        for recording in range(2):
            y = .12 * np.sin(2 * np.pi * (220 + 1200 * label + person) * t)
            y += rng.normal(0, .005, size=len(t))
            path = directory / f"p{person}_r{recording}.wav"
            sf.write(path, y.astype(np.float32), 16000, subtype="FLOAT")
            rows.append({"participant_id": f"p{person}", "recording_id": path.stem,
                         "label": label, "audio_path": str(path), "audio_sha256": sha256_file(path)})
    frame = assign_splits(pd.DataFrame(rows))
    manifest = directory / "manifest.csv"
    frame.to_csv(manifest, index=False)
    return directory, manifest, frame

@pytest.fixture(scope="session")
def bundle(dataset):
    directory, manifest, frame = dataset
    features = directory / "features.npz"
    extract_features(manifest, features)
    output = directory / "mel"
    train_bundle(manifest, output, features=features)
    return output, features
