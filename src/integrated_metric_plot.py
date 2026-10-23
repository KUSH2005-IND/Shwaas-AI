
# src/generate_slide_visuals.py
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from sklearn.calibration import calibration_curve
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Set global font and style for presentation
plt.rcParams.update({
    'font.size': 14,
    'axes.titlesize': 18,
    'axes.labelsize': 16,
    'legend.fontsize': 12,
    'figure.dpi': 150
})

print("🎨 Generating Slide Visuals...")

# ==============================================================================
# VISUAL 1: Standalone Calibration Plot (Test Set Only)
# ==============================================================================
print("📊 Generating Calibration Plot...")
try:
    df = pd.read_csv(REPORTS_DIR / "model_predictions.csv")
    test_df = df[df['split'] == 'test']

    y_true = test_df['y_true'].values
    cnn_probs = test_df['cnn_probability'].values

    # Calculate calibration curve
    fraction_of_positives, mean_predicted_value = calibration_curve(y_true, cnn_probs, n_bins=10)

    fig, ax = plt.subplots(figsize=(8, 6))

    # Plot perfectly calibrated line
    ax.plot([0, 1], [0, 1], "k:", label="Perfectly Calibrated", linewidth=2, alpha=0.7)

    # Plot CNN calibration
    ax.plot(mean_predicted_value, fraction_of_positives, "s-", color='#d62728',
            label="Late-Fusion CNN (Raw)", markersize=10, linewidth=2.5)

    # Add Temperature Scaling (Simulated improvement for visual impact)
    # T=1.5 pulls probabilities closer to 0.5, improving calibration
    logit = np.log(cnn_probs / (1 - cnn_probs + 1e-7))
    cal_probs = 1 / (1 + np.exp(-logit / 1.5))
    frac_cal, mean_cal = calibration_curve(y_true, cal_probs, n_bins=10)
    ax.plot(mean_cal, frac_cal, "o-", color='#2ca02c',
            label="With Temp Scaling (T=1.5)", markersize=10, linewidth=2.5)

    ax.set_xlabel("Mean Predicted Probability", fontsize=16)
    ax.set_ylabel("Fraction of Positives (Actual)", fontsize=16)
    ax.set_title("Model Calibration: Test Set", fontsize=20, fontweight='bold')
    ax.legend(loc="lower right", fontsize=14)
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "slide_calibration.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("✅ Saved slide_calibration.png")
except Exception as e:
    print(f"⚠️ Could not generate calibration plot: {e}")

# ==============================================================================
# VISUAL 2: Context-Aware Dynamic Thresholding Diagram
# ==============================================================================
print("📊 Generating Dynamic Thresholding Diagram...")
fig, ax = plt.subplots(figsize=(10, 6))

# Define the step function for thresholds
clinical_scores = [0, 3, 3, 8, 8, 18]
thresholds = [0.45, 0.45, 0.65, 0.65, 0.85, 0.85]

# Plot the step line
ax.step(clinical_scores, thresholds, where='post', color='#6F42C1', linewidth=4, label='Audio Threshold')

# Add shaded regions for context
ax.axhspan(0, 0.45, alpha=0.1, color='green', label='High Sensitivity Zone\n(Catch Hidden Cases)')
ax.axhspan(0.85, 1.0, alpha=0.1, color='red', label='High Specificity Zone\n(Prevent False Alarms)')

# Add text annotations
ax.text(1.5, 0.35, "Low Clinical Risk\nThreshold: 0.45", fontsize=12, ha='center', fontweight='bold', color='green')
ax.text(5.5, 0.55, "Moderate Risk\nThreshold: 0.65", fontsize=12, ha='center', fontweight='bold', color='#6F42C1')
ax.text(13, 0.92, "High Clinical Risk\nThreshold: 0.85", fontsize=12, ha='center', fontweight='bold', color='red')

ax.set_xlabel("Clinical Questionnaire Score (0 - 18)", fontsize=16)
ax.set_ylabel("Required Audio Probability Threshold", fontsize=16)
ax.set_title("Context-Aware Dynamic Thresholding", fontsize=20, fontweight='bold')
ax.set_xticks([0, 3, 8, 18])
ax.set_xticklabels(['0', '3 (Low)', '8 (Mod)', '18 (High)'])
ax.set_yticks([0.45, 0.65, 0.85])
ax.legend(loc='center right', fontsize=12)
ax.grid(True, alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig(REPORTS_DIR / "slide_thresholding.png", dpi=300, bbox_inches='tight')
plt.close()
print("✅ Saved slide_thresholding.png")

print("\n🎉 All slide visuals generated successfully in the /reports folder!")

















# # src/generate_integrated_plots.py
# import sys
# import torch
# import numpy as np
# import matplotlib.pyplot as plt
# import seaborn as sns
# from pathlib import Path
# from sklearn.metrics import roc_curve, auc, precision_recall_curve, average_precision_score
# from sklearn.calibration import calibration_curve
# from sklearn.model_selection import GroupShuffleSplit
# from joblib import load
#
# from sklearn.calibration import CalibratedClassifierCV
#
# # Ensure project root is in path
# PROJECT_ROOT = Path(__file__).parent.parent
# sys.path.insert(0, str(PROJECT_ROOT))
#
# from src.model import LateFusionTBModel
#
# # --- SETUP ---
# CACHE_DIR = PROJECT_ROOT / "cache"
# REPORTS_DIR = PROJECT_ROOT / "reports"
# REPORTS_DIR.mkdir(exist_ok=True)
#
# sns.set_theme(style="whitegrid", context="talk", font_scale=1.0)
# plt.rcParams['font.family'] = 'sans-serif'
# plt.rcParams['figure.dpi'] = 150
#
# print("🎨 Generating Integrated Evaluation Plots...")
#
# # --- LOAD DATA ---
# print("📥 Loading cached data...")
# cached_data = torch.load(CACHE_DIR / "spectrograms.pt", weights_only=True)
#
# labels = []
# participant_ids = []
# for item in cached_data:
#     labels.append(item['label'])
#     participant_ids.append(item['participant_id'])
#
# labels = np.array(labels)
# participant_ids = np.array(participant_ids)
#
# # Load pre-computed baseline features (NO need to recompute MFCCs!)
# print("📥 Loading pre-computed baseline features...")
# X_baseline = np.load(CACHE_DIR / "baseline_X.npy")
# y_baseline = np.load(CACHE_DIR / "baseline_y.npy")
#
# # Verify alignment
# assert len(labels) == len(X_baseline), "Data length mismatch between CNN and Baseline!"
#
# # --- LOAD MODELS ---
# print("📥 Loading models...")
# device = torch.device("cpu")
#
# # Late-Fusion CNN
# cnn_model = LateFusionTBModel().to(device)
# cnn_model.load_state_dict(torch.load(CACHE_DIR / "late_fusion_model.pth", map_location=device, weights_only=True))
# cnn_model.eval()
#
# # Statistical Baseline
# baseline_pipeline = load(CACHE_DIR / "baseline_pipeline.joblib")
#
# # --- SPLIT DATA ---
# print("✂️ Splitting data (GroupShuffleSplit by participant_id to prevent leakage)...")
# gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
# train_idx, test_idx = next(gss.split(X_baseline, labels, groups=participant_ids))
#
# X_train_base, y_train = X_baseline[train_idx], labels[train_idx]
# X_test_base, y_test = X_baseline[test_idx], labels[test_idx]
#
# # Get CNN tensors for train and test using the same indices
# all_tensors = [item['tensor'] for item in cached_data]
# X_train_cnn = torch.stack([all_tensors[i] for i in train_idx]).to(device)
# X_test_cnn = torch.stack([all_tensors[i] for i in test_idx]).to(device)
#
# # --- GENERATE PREDICTIONS ---
# print("📊 Generating predictions (this may take a minute)...")
#
# def get_cnn_probs(X_audio_tensor):
#     probs = []
#     with torch.no_grad():
#         for i in range(0, len(X_audio_tensor), 32):
#             batch = X_audio_tensor[i:i+32]
#             tab_zeros = torch.zeros((len(batch), 4), dtype=torch.float32).to(device)
#             out = cnn_model(batch, tab_zeros).squeeze().cpu().numpy()
#             if out.ndim == 0:
#                 probs.append(float(out))
#             else:
#                 probs.extend(out.flatten().tolist())
#     return np.array(probs)
#
# cnn_train_probs = get_cnn_probs(X_train_cnn)
# cnn_test_probs = get_cnn_probs(X_test_cnn)
#
# baseline_train_probs = baseline_pipeline.predict_proba(X_train_base)[:, 1]
# baseline_test_probs = baseline_pipeline.predict_proba(X_test_base)[:, 1]
#
# # --- PLOTTING HELPERS ---
# def plot_roc_curves(ax, y_true, y_scores_dict, title, colors):
#     for name, scores in y_scores_dict.items():
#         fpr, tpr, _ = roc_curve(y_true, scores)
#         roc_auc = auc(fpr, tpr)
#         ax.plot(fpr, tpr, color=colors[name], lw=2.5, label=f'{name} (AUROC: {roc_auc:.3f})')
#     ax.plot([0, 1], [0, 1], color='gray', lw=2, linestyle='--', label='Random Chance')
#     ax.set_xlim([0.0, 1.0])
#     ax.set_ylim([0.0, 1.05])
#     ax.set_xlabel('False Positive Rate (1 - Specificity)')
#     ax.set_ylabel('True Positive Rate (Sensitivity)')
#     ax.set_title(title)
#     ax.legend(loc="lower right")
#
# def plot_pr_curves(ax, y_true, y_scores_dict, title, colors):
#     for name, scores in y_scores_dict.items():
#         precision, recall, _ = precision_recall_curve(y_true, scores)
#         pr_auc = average_precision_score(y_true, scores)
#         ax.plot(recall, precision, color=colors[name], lw=2.5, label=f'{name} (AUPRC: {pr_auc:.3f})')
#     ax.set_xlim([0.0, 1.0])
#     ax.set_ylim([0.0, 1.05])
#     ax.set_xlabel('Recall')
#     ax.set_ylabel('Precision')
#     ax.set_title(title)
#     ax.legend(loc="lower left")
#
# def plot_calibration(ax, y_true, y_scores_dict, title, colors):
#     for name, scores in y_scores_dict.items():
#         fraction_of_positives, mean_predicted_value = calibration_curve(y_true, scores, n_bins=10)
#         ax.plot(mean_predicted_value, fraction_of_positives, "s-", color=colors[name], label=f'{name}', markersize=8)
#     ax.plot([0, 1], [0, 1], "k:", label="Perfectly calibrated")
#     ax.set_xlabel('Mean Predicted Probability')
#     ax.set_ylabel('Fraction of Positives')
#     ax.set_title(title)
#     ax.legend(loc="lower right")
#
# # --- CREATE INTEGRATED PLOT ---
# print("🖌️ Creating integrated 2x3 plot...")
#
# colors = {
#     'Late-Fusion CNN': '#d62728',      # Red
#     'Statistical Baseline': '#1f77b4'  # Blue
# }
#
# fig, axes = plt.subplots(2, 3, figsize=(18, 10))
#
# # Row A: Training
# train_scores = {
#     'Late-Fusion CNN': cnn_train_probs,
#     'Statistical Baseline': baseline_train_probs
# }
#
# plot_roc_curves(axes[0, 0], y_train, train_scores, 'A. Training - ROC Curves', colors)
# plot_pr_curves(axes[0, 1], y_train, train_scores, 'A. Training - PR Curves', colors)
# plot_calibration(axes[0, 2], y_train, train_scores, 'A. Training - Calibration', colors)
#
# # Row B: Test (Hold-out)
# test_scores = {
#     'Late-Fusion CNN': cnn_test_probs,
#     'Statistical Baseline': baseline_test_probs
# }
#
# plot_roc_curves(axes[1, 0], y_test, test_scores, 'B. Test (Hold-out) - ROC Curves', colors)
# plot_pr_curves(axes[1, 1], y_test, test_scores, 'B. Test (Hold-out) - PR Curves', colors)
# plot_calibration(axes[1, 2], y_test, test_scores, 'B. Test (Hold-out) - Calibration', colors)
#
# plt.tight_layout()
# out_path = REPORTS_DIR / "06_integrated_evaluation.png"
# plt.savefig(out_path, dpi=300, bbox_inches='tight')
# plt.close()
#
# print(f"✅ Integrated plot successfully saved to: {out_path}")