"""Shared waveform/mel frontend. Energy windows are NOT a cough detector.
HeAR uses unfiltered windows and its own official PCEN frontend.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from io import BytesIO
from math import gcd
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly
import soundfile as sf

SR = 16000
FRONTEND_VERSION = "waveform-v1-mel128-fft1024-hop512"

class AudioError(ValueError):
    pass

@dataclass(frozen=True)
class Quality:
    usable: bool
    duration_seconds: float
    rms: float
    clipped_fraction: float
    reasons: tuple[str, ...]

    def to_dict(self):
        return asdict(self)

def load_audio(source: bytes | str | Path, max_seconds: float = 30) -> np.ndarray:
    """Bound decoding before allocation, downmix and resample to 16 kHz."""
    try:
        with sf.SoundFile(BytesIO(source) if isinstance(source, bytes) else source) as handle:
            sr = handle.samplerate
            if not 8000 <= sr <= 192000 or not 1 <= handle.channels <= 8:
                raise AudioError("Unsupported sample rate/channels; use WAV at 16 kHz.")
            if handle.frames / sr > max_seconds:
                raise AudioError(f"Recording exceeds {max_seconds:g} seconds.")
            y = handle.read(dtype="float32", always_2d=True).mean(axis=1)
    except (RuntimeError, OSError, ValueError) as error:
        if isinstance(error, AudioError):
            raise
        raise AudioError("Could not decode audio. Upload a WAV or FLAC recording.") from error
    if not y.size or not np.isfinite(y).all():
        raise AudioError("Recording is empty or contains invalid samples.")
    if sr != SR:
        factor = gcd(sr, SR)
        y = resample_poly(y, SR // factor, sr // factor).astype(np.float32)
    return np.ascontiguousarray(y, dtype=np.float32)

def assess_quality(y: np.ndarray) -> Quality:
    y = np.asarray(y, dtype=np.float32)
    if y.ndim != 1 or not y.size or not np.isfinite(y).all():
        raise AudioError("Expected a finite, non-empty mono waveform.")
    rms = float(np.sqrt(np.mean(y.astype(np.float64) ** 2)))
    clipped = float(np.mean(np.abs(y) >= 0.999))
    duration = len(y) / SR
    reasons = []
    if duration < 0.5:
        reasons.append("too_short")
    if rms < 0.001:
        reasons.append("too_quiet")
    if clipped >= 0.01:
        reasons.append("clipping")
    return Quality(not reasons, duration, rms, clipped, tuple(reasons))

def activity_windows(y: np.ndarray, seconds: float, stride: float = 1.0) -> np.ndarray:
    """Include the recording tail; discard silent windows only."""
    quality = assess_quality(y)
    if not quality.usable:
        raise AudioError("Recording quality failed: " + ", ".join(quality.reasons))
    size, step = int(seconds * SR), int(stride * SR)
    if size <= 0 or step <= 0:
        raise ValueError("Window length and stride must be positive.")
    if len(y) <= size:
        return np.pad(y, (0, size - len(y)))[None].astype(np.float32)
    starts = list(range(0, len(y) - size + 1, step))
    if starts[-1] != len(y) - size:
        starts.append(len(y) - size)
    windows = np.stack([y[start:start + size] for start in starts])
    energy = np.sqrt(np.mean(windows.astype(np.float64) ** 2, axis=1))
    kept = windows[energy >= 0.001]
    if not len(kept):
        raise AudioError("No usable acoustic activity; please record again.")
    return kept.astype(np.float32)

def log_mel(window: np.ndarray) -> np.ndarray:
    import librosa
    y = np.asarray(window, dtype=np.float32)
    rms = float(np.sqrt(np.mean(y.astype(np.float64) ** 2)))
    y = y / max(rms * 5, 1e-5)
    mel = librosa.feature.melspectrogram(
        y=y, sr=SR, n_mels=128, n_fft=1024, hop_length=512, power=2.0
    )
    db = librosa.power_to_db(mel, ref=np.max)
    return ((db - db.min()) / max(float(np.ptp(db)), 1e-8)).astype(np.float32)

def mel_images(y: np.ndarray) -> np.ndarray:
    from scipy.ndimage import zoom
    images = []
    for window in activity_windows(y, seconds=3, stride=1.5):
        mel = log_mel(window)
        image = zoom(mel, (224 / mel.shape[0], 224 / mel.shape[1]), order=1)
        images.append(np.repeat(image[None, :224, :224], 3, axis=0))
    return np.stack(images).astype(np.float32)

def mel_summary(y: np.ndarray) -> np.ndarray:
    summaries = []
    for window in activity_windows(y, seconds=3, stride=1.5):
        mel = log_mel(window)
        bands = np.array_split(np.arange(mel.shape[0]), 32)
        summaries.append(np.r_[
            [mel[band].mean() for band in bands],
            [mel[band].std() for band in bands],
            mel.mean(), mel.std(), mel.max(), mel.mean(axis=0).std(),
        ])
    return np.mean(summaries, axis=0).astype(np.float32)
