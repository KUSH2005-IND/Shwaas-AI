# src/leakage.py
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from sklearn.impute import SimpleImputer

# --- ROBUST PATHING ---
# Get the directory of this script (src/), go up one level to project root, then into data/
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

print(f"📂 Looking for data in: {DATA_DIR}")
print(f"📂 Does the data folder exist? {DATA_DIR.exists()}")

print("🛡️ Running Metadata Leakage Check...")

# Load the filtered dataset using the absolute path
file_path = DATA_DIR / "train_audio_index.parquet"

if not file_path.exists():
    print(f"❌ ERROR: Could not find {file_path}")
    print("Please ensure you have successfully run 'labels.py' first, and that the 'data' folder is in the project root.")
    exit(1)

merged = pd.read_parquet(file_path)
print(f"✅ Loaded {len(merged)} recordings.")

# We will test if 'age' and 'quality_score' can predict the label on their own.
# If they can, our audio model might just be learning demographics/recording artifacts.
features = ["age", "quality_score"]

X = merged[features].copy()
y = merged["label"].values
groups = merged["participant_id"].values # CRITICAL: Group by participant to prevent data leakage

# Impute any missing ages with the median
imp = SimpleImputer(strategy="median")
X_imp = imp.fit_transform(X)

# Train a nuisance model using Participant-Level Cross-Validation
cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))

# Get out-of-fold predictions
probs = cross_val_predict(clf, X_imp, y, groups=groups, cv=cv, method="predict_proba")[:, 1]

# Calculate AUROC
auc = roc_auc_score(y, probs)

print("="*50)
print("📊 METADATA LEAKAGE RESULTS")
print("="*50)
print(f"Nuisance AUROC (Age + Quality Score vs Label): {auc:.4f}")

if auc > 0.60:
    print("⚠️ WARNING: Metadata is leaking the label! The model might be learning demographics, not coughs.")
    print("   -> We will need to apply strict band-limiting and loudness normalization in the next step.")
else:
    print("✅ PASS: Metadata leakage is minimal. Safe to proceed with audio embeddings.")