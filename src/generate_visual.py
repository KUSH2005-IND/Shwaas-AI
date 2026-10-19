# src/generate_visuals.py
import sys
import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import cv2
from pathlib import Path
from sklearn.metrics import roc_curve, auc, precision_recall_curve, average_precision_score, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit

# Ensure the project root is in the system path so imports work perfectly
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.model import LateFusionTBModel
from src.gradcam import GradCAM

# --- SETUP ---
CACHE_DIR = PROJECT_ROOT / "cache"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Set professional plotting style
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.family'] = 'sans-serif'

print("🎨 Generating Presentation-Ready Visuals...")

# =========================================================================
# VISUAL 1: Training Curves (Hardcoded from your exact training output)
# =========================================================================
print("📊 1. Generating Training Curves...")
epochs = np.arange(1, 16)
train_loss = [0.5839, 0.3661, 0.3168, 0.3209, 0.2812, 0.2895, 0.2847, 0.2755, 0.3047, 0.2917, 0.2598, 0.2732, 0.2644, 0.2485, 0.2525]
val_loss =   [0.4634, 0.2919, 0.3190, 0.3013, 0.3191, 0.2929, 0.2601, 0.2712, 0.2852, 0.2690, 0.2812, 0.2364, 0.2541, 0.2954, 0.2647]
train_acc =  [0.7114, 0.8475, 0.8639, 0.8659, 0.8871, 0.8824, 0.8784, 0.8871, 0.8706, 0.8788, 0.8969, 0.8890, 0.8957, 0.9035, 0.8969]
val_acc =    [0.7821, 0.8636, 0.8683, 0.8589, 0.8621, 0.8636, 0.8856, 0.8918, 0.8668, 0.9013, 0.8824, 0.8981, 0.8903, 0.8746, 0.8887]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

ax1.plot(epochs, train_loss, label='Train Loss', marker='o', color='#1f77b4', linewidth=2)
ax1.plot(epochs, val_loss, label='Validation Loss', marker='s', color='#ff7f0e', linewidth=2)
ax1.set_title('Model Convergence: Loss over Epochs')
ax1.set_xlabel('Epoch')
ax1.set_ylabel('Binary Cross Entropy Loss')
ax1.legend()
ax1.set_xticks(epochs)

ax2.plot(epochs, train_acc, label='Train Accuracy', marker='o', color='#1f77b4', linewidth=2)
ax2.plot(epochs, val_acc, label='Validation Accuracy', marker='s', color='#ff7f0e', linewidth=2)
ax2.set_title('Model Performance: Accuracy over Epochs')
ax2.set_xlabel('Epoch')
ax2.set_ylabel('Accuracy')
ax2.legend()
ax2.set_xticks(epochs)
ax2.set_ylim(0.6, 1.0)

plt.tight_layout()
plt.savefig(REPORTS_DIR / "01_training_curves.png", dpi=300, bbox_inches='tight')
plt.close()

# =========================================================================
# VISUAL 2 & 3: ROC Curve, PR Curve, and Confusion Matrix
# =========================================================================
print("📊 2. Generating Evaluation Metrics (ROC, PR, Confusion Matrix)...")
cached_data = torch.load(CACHE_DIR / "spectrograms.pt", weights_only=True)
audio_tensors, labels, participant_ids = [], [], []
for item in cached_data:
    audio_tensors.append(item['tensor'])
    labels.append(item['label'])
    participant_ids.append(item['participant_id'])

audio_tensors = torch.stack(audio_tensors)
labels = np.array(labels)
participant_ids = np.array(participant_ids)

# Strict participant split
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
_, test_idx = next(gss.split(audio_tensors, labels, groups=participant_ids))
X_test, y_test = audio_tensors[test_idx], labels[test_idx]

# Load model
device = torch.device("cpu")
model = LateFusionTBModel().to(device)
model.load_state_dict(torch.load(CACHE_DIR / "late_fusion_model.pth", map_location=device, weights_only=True))
model.eval()

# Inference
probs = []
with torch.no_grad():
    for i in range(0, len(X_test), 32):
        batch_audio = X_test[i:i+32].to(device)
        batch_tab = torch.zeros((len(batch_audio), 4), dtype=torch.float32).to(device)
        out = model(batch_audio, batch_tab).squeeze().cpu().numpy()
        probs.extend(out.flatten().tolist())
probs = np.array(probs)

# Calculate metrics
fpr, tpr, roc_thresh = roc_curve(y_test, probs)
roc_auc = auc(fpr, tpr)
precision, recall, pr_thresh = precision_recall_curve(y_test, probs)
pr_auc = average_precision_score(y_test, probs)

# Plot ROC and PR
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

ax1.plot(fpr, tpr, color='#d62728', lw=2, label=f'Audio CNN (AUC = {roc_auc:.3f})')
ax1.plot([0, 1], [0, 1], color='gray', lw=2, linestyle='--')
ax1.set_xlim([0.0, 1.0])
ax1.set_ylim([0.0, 1.05])
ax1.set_xlabel('False Positive Rate (1 - Specificity)')
ax1.set_ylabel('True Positive Rate (Sensitivity)')
ax1.set_title('Receiver Operating Characteristic (ROC) Curve')
ax1.legend(loc="lower right")

ax2.plot(recall, precision, color='#2ca02c', lw=2, label=f'Audio CNN (AP = {pr_auc:.3f})')
ax2.set_xlim([0.0, 1.0])
ax2.set_ylim([0.0, 1.05])
ax2.set_xlabel('Recall (Sensitivity)')
ax2.set_ylabel('Precision (Positive Predictive Value)')
ax2.set_title('Precision-Recall Curve')
ax2.legend(loc="lower left")

plt.tight_layout()
plt.savefig(REPORTS_DIR / "02_roc_pr_curves.png", dpi=300, bbox_inches='tight')
plt.close()

# --- FIXED CONFUSION MATRIX LOGIC ---
# Use Youden's J Statistic to find the optimal threshold (balances Sensitivity & Specificity)
# This avoids the "inf" threshold bug that predicted everything as Negative.
youden_j = tpr - fpr
optimal_idx = np.argmax(youden_j)
optimal_thresh = roc_thresh[optimal_idx]

y_pred = (probs >= optimal_thresh).astype(int)
cm = confusion_matrix(y_test, y_pred)

plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Normal (0)', 'Abnormal (1)'], yticklabels=['Normal (0)', 'Abnormal (1)'])
plt.title(f'Confusion Matrix at Optimal Threshold ({optimal_thresh:.2f})')
plt.xlabel('Predicted Label')
plt.ylabel('True Label')
plt.savefig(REPORTS_DIR / "03_confusion_matrix.png", dpi=300, bbox_inches='tight')
plt.close()

# =========================================================================
# VISUAL 4: Improved Grad-CAM Overlay
# =========================================================================
print("📊 3. Generating Improved Grad-CAM Overlay...")
sample = cached_data[0]
audio_tensor = sample['tensor'].unsqueeze(0).to(device)
tabular_zeros = torch.zeros((1, 4), dtype=torch.float32).to(device)

target_layer = model.audio_encoder.backbone.features[-1][0]
gradcam = GradCAM(model, target_layer)
heatmap = gradcam.generate_cam(audio_tensor, tabular_zeros)

# Get original spectrogram for overlay
spec = sample['tensor'][0].numpy()
spec_norm = ((spec - spec.min()) / (spec.max() - spec.min() + 1e-8) * 255).astype(np.uint8)
spec_rgb = cv2.cvtColor(spec_norm, cv2.COLOR_GRAY2RGB)

# Blend heatmap with original spectrogram (50% opacity)
overlay = cv2.addWeighted(spec_rgb, 0.5, heatmap, 0.5, 0)

plt.figure(figsize=(10, 5))
plt.imshow(overlay)
plt.title('Explainable AI: Grad-CAM Attention Map on Cough Spectrogram', fontsize=14)
plt.xlabel('Time (Frames)')
plt.ylabel('Frequency (Mel Bands)')
plt.axis('off')

# Add colorbar
sm = plt.cm.ScalarMappable(cmap='jet', norm=plt.Normalize(vmin=0, vmax=255))
sm.set_array([])
cbar = plt.colorbar(sm, ax=plt.gca(), fraction=0.046, pad=0.04)
cbar.set_label('Model Attention Intensity', rotation=270, labelpad=15)

plt.savefig(REPORTS_DIR / "04_gradcam_overlay.png", dpi=300, bbox_inches='tight')
plt.close()

# =========================================================================
# VISUAL 5: Ablation Study / Experiments Bar Chart
# =========================================================================
print("📊 4. Generating Ablation Study Chart...")
models = ['Metadata Nuisance\n(Demographics)', 'Statistical Baseline\n(MFCC + Logistic Reg)', 'Late-Fusion CNN\n(Audio Only)']
auroc_scores = [0.610, 0.681, 0.791]
colors = ['#999999', '#1f77b4', '#d62728']

plt.figure(figsize=(10, 6))
bars = plt.bar(models, auroc_scores, color=colors, edgecolor='black', linewidth=1.2)

# Add value labels on top of bars
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 0.015, f'{yval:.3f}', ha='center', va='bottom', fontsize=12, fontweight='bold')

plt.axhline(y=0.50, color='red', linestyle='--', linewidth=1.5, label='Random Chance (0.50)')
plt.ylim(0, 1.0)
plt.ylabel('Participant-Grouped AUROC')
plt.title('Ablation Study: Does the Deep Learning Add Value?', fontsize=14)
plt.legend(loc='lower right')
plt.tight_layout()
plt.savefig(REPORTS_DIR / "05_ablation_study.png", dpi=300, bbox_inches='tight')
plt.close()

print("\n✅ SUCCESS! All visuals saved to the 'reports/' folder:")
print("   -> 01_training_curves.png")
print("   -> 02_roc_pr_curves.png")
print("   -> 03_confusion_matrix.png (FIXED)")
print("   -> 04_gradcam_overlay.png")
print("   -> 05_ablation_study.png")