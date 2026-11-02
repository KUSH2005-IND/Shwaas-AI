from io import BytesIO
import numpy as np
import pandas as pd
import pytest
import soundfile as sf
from src.audio import AudioError, activity_windows, assess_quality, load_audio, mel_images
from src.features import read_features
from src.manifest import assign_splits, read_manifest
from src.prepare import export_recordings

def wav_bytes(y, sr=16000):
    stream = BytesIO()
    sf.write(stream, y, sr, format="WAV", subtype="FLOAT")
    return stream.getvalue()

def test_splits_are_reproducible_and_subject_disjoint(dataset):
    directory, manifest, frame = dataset
    loaded = read_manifest(manifest)
    assert loaded.participant_id.nunique() == 40
    assert loaded.groupby("participant_id").split.nunique().max() == 1
    pd.testing.assert_series_equal(assign_splits(frame).split, frame.split)
    broken = frame.copy()
    pid = broken.participant_id.iloc[0]
    indices = broken.index[broken.participant_id == pid]
    broken.loc[indices[0], "split"] = "test"
    broken.loc[indices[1], "split"] = "train"
    path = directory / "leaked.csv"
    broken.to_csv(path, index=False)
    with pytest.raises(ValueError, match="leakage"):
        read_manifest(path)

def test_audio_resampling_tail_and_clipping():
    t = np.arange(48000) / 48000
    y = .1 * np.sin(2 * np.pi * 700 * t)
    decoded = load_audio(wav_bytes(np.stack([y, y], axis=1), sr=48000))
    assert decoded.shape == (16000,)
    assert np.isfinite(decoded).all()
    with pytest.raises(AudioError, match="decode"):
        load_audio(b"not a recording")
    with pytest.raises(AudioError, match="empty"):
        load_audio(wav_bytes(np.empty(0)))
    assert not assess_quality(np.zeros(16000)).usable
    peak = np.full(48000, .01, dtype=np.float32)
    peak[0] = 1
    assert assess_quality(peak).usable  # one peak is not sustained clipping
    peak[:1000] = 1
    assert not assess_quality(peak).usable
    tail = np.zeros(16000 * 5, dtype=np.float32)
    tail[-8000:] = .1
    windows = activity_windows(tail, seconds=2)
    assert np.max(windows[-1, -8000:]) == pytest.approx(.1)
    assert mel_images(decoded).shape == (1, 3, 224, 224)

def test_prepare_keeps_labels_attached_to_identified_rows(tmp_path):
    waveform = .1 * np.sin(np.arange(48000) * .2).astype(np.float32)
    rows = [
        {"participant_id": "alice", "audio_type": "cough-heavy", "quality_score": 2,
         "covid_status": "healthy", "audio": {"bytes": wav_bytes(waveform), "path": "does-not-exist.wav"}},
        {"participant_id": "bob", "audio_type": "cough-shallow", "quality_score": 1,
         "covid_status": "positive_mild", "audio": {"bytes": wav_bytes(waveform * .8)}},
    ]
    frame, skipped = export_recordings(rows[::-1], tmp_path / "raw.csv", "revision-123")
    assert frame.set_index("participant_id").label.to_dict() == {"alice": 0, "bob": 1}
    assert all(frame.source_revision == "revision-123")
    assert not skipped

def test_feature_cache_rejects_a_different_manifest(dataset, bundle):
    directory, manifest, frame = dataset
    _, features = bundle
    changed = directory / "changed.csv"
    frame.iloc[::-1].to_csv(changed, index=False)
    with pytest.raises(ValueError, match="different manifest"):
        read_features(features, changed)
