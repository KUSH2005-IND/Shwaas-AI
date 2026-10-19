# src/audit.py
import pandas as pd
from datasets import load_dataset
import os

# Ensure data directory exists
os.makedirs("../data", exist_ok=True)

print("🔍 Loading Coswara Metadata...")
try:
    # Load metadata
    meta_ds = load_dataset("szzs1693/coswara-data", "metadata", split="train")
    meta = meta_ds.to_pandas()
    print("✅ Metadata loaded successfully.")
except Exception as e:
    print(f"❌ Failed to load metadata: {e}")
    exit(1)

print("\n🔍 Loading Audio Index (this may take a minute as it downloads file manifests)...")
try:
    # Load audio index (FIXED: to_pandas instead of to_padas)
    aud_ds = load_dataset("szzs1693/coswara-data", "audio", split="train")
    audio_idx = aud_ds.remove_columns(["audio"]).to_pandas()
    print("✅ Audio index loaded successfully.")
except Exception as e:
    print(f"⚠️ Failed to load audio index directly. Error: {e}")
    print("Attempting to extract audio info from metadata instead...")
    # Fallback: sometimes audio info is in the metadata
    audio_idx = meta[meta['audio_type'].notna()].copy() if 'audio_type' in meta.columns else pd.DataFrame()

# Add a row index for later fetching
if not audio_idx.empty:
    audio_idx["row_index"] = range(len(audio_idx))

print("\n" + "="*60)
print("📊 AUDIT RESULTS (Copy this output for your Mentor)")
print("="*60)

print("\n1. Metadata Columns:")
print(meta.columns.tolist())

print("\n2. Audio Index Columns:")
print(audio_idx.columns.tolist() if not audio_idx.empty else "Audio index empty or not found")

print("\n3. Join Key Check (First 5 rows):")
id_cols = [c for c in meta.columns if 'id' in c.lower() or 'participant' in c.lower()]
print(meta[id_cols].head() if id_cols else meta.head())

print("\n4. Audio Types Available:")
if 'audio_type' in audio_idx.columns:
    print(audio_idx["audio_type"].value_counts().to_dict())
else:
    print("Column 'audio_type' not found in audio index.")

print("\n5. Quality Score Distribution:")
q_cols = [c for c in audio_idx.columns if 'quality' in c.lower() or 'score' in c.lower()]
if q_cols:
    print(audio_idx[q_cols[0]].value_counts(dropna=False).to_dict())
else:
    print("No obvious quality score column found.")

print("\n6. Target Label (Health Status) Distribution:")
status_cols = [c for c in meta.columns if 'status' in c.lower() or 'health' in c.lower() or 'covid' in c.lower()]
if status_cols:
    print(meta[status_cols[0]].value_counts(dropna=False).to_dict())
else:
    print("No obvious health status column found.")

print("\n7. Recordings per Participant (Min, Max, Mean):")
p_id_cols = [c for c in (audio_idx.columns if not audio_idx.empty else meta.columns) if 'participant' in c.lower() or 'id' in c.lower()]
if p_id_cols and not audio_idx.empty:
    print(audio_idx.groupby(p_id_cols[0]).size().describe()[['min', 'max', 'mean']])
else:
    print("Could not calculate recordings per participant.")

print("\n8. Symptom Columns Check (Sample):")
symptom_cols = [c for c in meta.columns if any(s in c.lower() for s in ['cough', 'fever', 'breath', 'fatigue', 'symptom', 'illness'])]
for col in symptom_cols[:5]: # Print first 5 found
    print(f"  - {col}: {meta[col].value_counts(dropna=False).to_dict()}")

# Save to parquet for the next steps
meta.to_parquet("data/raw_meta.parquet", index=False)
if not audio_idx.empty:
    audio_idx.to_parquet("data/audio_index.parquet", index=False)
    print("\n💾 Saved to data/raw_meta.parquet and data/audio_index.parquet")
else:
    print("\n💾 Saved to data/raw_meta.parquet")