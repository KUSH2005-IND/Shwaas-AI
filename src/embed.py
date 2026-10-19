# src/embed.py
import os
import io
import glob
import pandas as pd
import numpy as np
import torch
import librosa
import soundfile as sf
import scipy.signal as signal
import cv2
from pathlib import Path
from tqdm import tqdm

# --- ROBUST PATHING ---
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)

print("🎵 Starting Audio Embedding Extraction...")

# 1. Load the filtered index
merged = pd.read_parquet(DATA_DIR / "train_audio_index.parquet")
print(f"✅ Loaded {len(merged)} recordings to process.")

# 2. BYPASS HF DATASETS: Read raw Parquet files directly from the local cache
print("📥 Bypassing HF audio decoder. Reading raw Parquet files from local cache...")
repo_id = "datasets--szzs1693--coswara-data"
cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / repo_id / "snapshots"

# Find the parquet files for the 'audio' config, 'train' split
parquet_files = glob.glob(str(cache_dir / "*" / "audio" / "train" / "*.parquet"))
if not parquet_files:
    parquet_files = glob.glob(str(cache_dir / "*" / "train" / "*.parquet"))

if not parquet_files:
    print("❌ Could not find cached Parquet files.")
    exit(1)

print(f"📂 Found {len(parquet_files)} Parquet files in cache.")
raw_audio_df = pd.concat([pd.read_parquet(f) for f in parquet_files], ignore_index=True)
print(f"✅ Loaded {len(raw_audio_df)} raw audio records.")

# DEBUG: Print the first 3 audio values to see the exact schema
print("\n🔍 DEBUG: Sample audio values from raw Parquet:")
for i in range(3):
    print(f"   Row {i}: {raw_audio_df.iloc[i]['audio']}")

# 3. Preprocessing parameters
SR = 16000
DURATION = 3.0
N_MELS = 128
N_FFT = 1024
HOP_LENGTH = 512


def bandpass_filter(y, sr, lowcut=300.0, highcut=6000.0, order=4):
    nyq = 0.5 * sr
    low = lowcut / nyq
    high = highcut / nyq
    b, a = signal.butter(order, [low, high], btype='band')
    return signal.filtfilt(b, a, y)


def preprocess_audio(y, sr):
    if sr != SR:
        y = librosa.resample(y, orig_sr=sr, target_sr=SR)
    y = bandpass_filter(y, SR)
    y, _ = librosa.effects.trim(y, top_db=30)
    rms = np.sqrt(np.mean(y ** 2))
    if rms > 1e-5:
        y = y / (rms * 5.0)
    target_len = int(SR * DURATION)
    if len(y) < target_len:
        y = np.pad(y, (0, target_len - len(y)))
    else:
        y = y[:target_len]
    return y


def audio_to_mel_tensor(y):
    mel_spec = librosa.feature.melspectrogram(y=y, sr=SR, n_mels=N_MELS, n_fft=N_FFT, hop_length=HOP_LENGTH)
    log_mel = librosa.power_to_db(mel_spec, ref=np.max)
    log_mel = (log_mel - log_mel.min()) / (log_mel.max() - log_mel.min() + 1e-8)
    img = cv2.resize(log_mel, (224, 224))
    img_rgb = np.stack((img,) * 3, axis=-1)
    return torch.tensor(img_rgb, dtype=torch.float32).permute(2, 0, 1)


def load_audio_from_raw(val, parquet_dir):
    """Safely extract audio from raw Parquet struct, resolving relative paths."""
    if val is None:
        raise ValueError("Audio value is literally None")

    # Handle pyarrow struct or python dict
    if hasattr(val, 'as_py'):
        val = val.as_py()

    if isinstance(val, dict):
        path = val.get('path')
        bts = val.get('bytes')

        # If it's a file path (resolve relative paths against the parquet directory)
        if path:
            if not os.path.isabs(path):
                path = os.path.join(parquet_dir, path)
            if os.path.exists(path):
                y, sr = librosa.load(path, sr=SR, mono=True)
                return y, sr
            else:
                raise ValueError(f"Resolved path does not exist: {path}")

        # If it's raw bytes embedded in the Parquet file
        elif bts:
            buf = io.BytesIO(bts)
            y, sr = sf.read(buf, dtype='float32')
            if len(y.shape) > 1:
                y = y.mean(axis=1)  # Convert stereo to mono
            return y.astype(np.float32), sr

    raise ValueError(f"Could not parse audio data. Type: {type(val)}, Value: {val}")


# 4. Process and Cache
print("\n🔄 Processing and caching spectrograms (this will take ~2-3 minutes)...")
cached_data = []
error_count = 0

# We need the directory of the parquet files to resolve relative paths
parquet_dir = os.path.dirname(parquet_files[0])

for idx, row in tqdm(merged.iterrows(), total=len(merged)):
    row_idx = int(row['row_index'])

    try:
        # Get the raw audio data directly from the Parquet dataframe
        audio_val = raw_audio_df.iloc[row_idx]['audio']
        y, sr = load_audio_from_raw(audio_val, parquet_dir)

        y_clean = preprocess_audio(y, sr)
        spec_tensor = audio_to_mel_tensor(y_clean)

        cached_data.append({
            "participant_id": row["participant_id"],
            "label": int(row["label"]),
            "audio_type": row["audio_type"],
            "tensor": spec_tensor
        })

    except Exception as e:
        error_count += 1
        if error_count <= 3:
            print(f"\n❌ ERROR at row_idx {row_idx}: {e}")
        continue

# 5. Save results
cache_file = CACHE_DIR / "spectrograms.pt"
torch.save(cached_data, cache_file)

print(f"\n💾 Successfully cached {len(cached_data)} out of {len(merged)} spectrograms.")
print(f"⚠️ Total skipped due to errors: {error_count}")

if len(cached_data) > 0:
    print("✅ Day 3 Complete! Your audio brain is ready for model training.")
else:
    print("🛑 HALTED: 0 spectrograms cached. Please review the errors above.")