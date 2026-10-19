# src/labels.py
import pandas as pd
from pathlib import Path

# --- ROBUST PATHING ---
# Get the directory of this script (src/), go up one level to project root, then into data/
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

print("🏷️ Building Proxy Labels and Filtering Dataset...")
print(f"📂 Looking for raw data in: {DATA_DIR}")

# 1. Load the raw data from the audit
meta = pd.read_parquet(DATA_DIR / "raw_meta.parquet")
audio_idx = pd.read_parquet(DATA_DIR / "audio_index.parquet")

# 2. Define the Label Mapping (Strictly based on Audit Output)
NORMAL = {"healthy", "no_resp_illness_exposed"}
ABNORMAL = {"resp_illness_not_identified", "positive_mild", "positive_moderate"}

def map_label(status):
    if pd.isna(status): return -1
    if status in NORMAL: return 0   # Normal respiratory health
    if status in ABNORMAL: return 1 # Respiratory abnormality (Proxy for TB triage)
    return -1                       # Excluded (ambiguous states)

meta["label"] = meta["covid_status"].apply(map_label)

# Filter out excluded labels
meta_filtered = meta[meta["label"] != -1].copy()
print(f"✅ Participants after filtering excluded classes: {len(meta_filtered)}")
print(f"📊 Proxy Label distribution:\n{meta_filtered['label'].value_counts().to_dict()}")

# 3. Merge Metadata with Audio Index
# Join key: meta['id'] == audio_idx['participant_id']
merged = pd.merge(audio_idx, meta_filtered, left_on="participant_id", right_on="id", suffixes=("_aud", "_meta"))

# 4. Filter by Quality and Audio Type
# Keep only good quality (>= 1.0) and the two cough types
merged = merged[merged["quality_score"] >= 1.0]
merged = merged[merged["audio_type"].isin(["cough-heavy", "cough-shallow"])]

print(f"\n✅ Final recordings ready for embedding: {len(merged)}")
print(f"🎤 Audio types:\n{merged['audio_type'].value_counts().to_dict()}")
print(f"🌟 Quality scores:\n{merged['quality_score'].value_counts().to_dict()}")

# 5. Save the clean, filtered tables
meta_filtered.to_parquet(DATA_DIR / "participants.parquet", index=False)
merged.to_parquet(DATA_DIR / "train_audio_index.parquet", index=False)

print(f"\n💾 Saved filtered data to:")
print(f"   -> {DATA_DIR / 'participants.parquet'}")
print(f"   -> {DATA_DIR / 'train_audio_index.parquet'}")