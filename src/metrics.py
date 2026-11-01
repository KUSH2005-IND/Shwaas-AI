"""Development-only calibration/threshold selection and grouped evaluation."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.metrics import (
    average_precision_score, brier_score_loss, confusion_matrix, log_loss,
    roc_auc_score, roc_curve,
)

def fit_calibrator(scores, labels):
    scores, labels = np.asarray(scores, float), np.asarray(labels, int)
    if not np.isfinite(scores).all() or set(labels) != {0, 1}:
        raise ValueError("Calibration requires finite validation scores and both classes.")
    def objective(parameters):
        z = np.exp(parameters[0]) * scores + parameters[1]
        return float(np.mean(np.logaddexp(0, z) - labels * z) + 1e-6 * np.sum(parameters ** 2))
    fit = minimize(objective, [0., 0.], method="L-BFGS-B", bounds=[(-5, 5), (-10, 10)])
    if not fit.success or not np.isfinite(fit.fun):
        raise RuntimeError("Calibration did not converge; inspect validation scores.")
    return {"scale": float(np.exp(fit.x[0])), "bias": float(fit.x[1]), "method": "positive_sigmoid"}

def calibrate(scores, parameters):
    return expit(parameters["scale"] * np.asarray(scores, float) + parameters["bias"])

def select_threshold(labels, probabilities, target_specificity=0.90):
    if not 0 < target_specificity < 1:
        raise ValueError("Target specificity must lie strictly between 0 and 1.")
    fpr, tpr, thresholds = roc_curve(labels, probabilities)
    # ROC begins with +inf (predict nobody positive). Keep that legitimate
    # operating point, but serialize a finite value above every observed score.
    thresholds[~np.isfinite(thresholds)] = np.nextafter(float(np.max(probabilities)), np.inf)
    valid = np.flatnonzero(np.isfinite(thresholds) & (fpr <= 1 - target_specificity + 1e-12))
    if not len(valid):
        raise ValueError("No finite threshold meets the requested validation specificity.")
    index = valid[np.argmax(tpr[valid])]
    return float(thresholds[index])

def metrics(labels, probabilities, threshold):
    labels, probabilities = np.asarray(labels), np.asarray(probabilities, float)
    if set(labels) != {0, 1} or not np.isfinite(probabilities).all() or not np.isfinite(threshold):
        raise ValueError("Metrics need both classes, finite probabilities and a finite threshold.")
    tn, fp, fn, tp = confusion_matrix(labels, probabilities >= threshold, labels=[0, 1]).ravel()
    return {
        "auroc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
        "brier": float(brier_score_loss(labels, probabilities)),
        "log_loss": float(log_loss(labels, probabilities, labels=[0, 1])),
        "sensitivity": float(tp / (tp + fn)), "specificity": float(tn / (tn + fp)),
        "precision": float(tp / (tp + fp)) if tp + fp else None,
        "negative_predictive_value": float(tn / (tn + fn)) if tn + fn else None,
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "threshold": float(threshold), "n_samples": int(len(labels)),
    }

def participant_predictions(frame):
    if frame.groupby("participant_id").label.nunique().max() != 1:
        raise ValueError("Conflicting participant labels.")
    return frame.groupby("participant_id", as_index=False).agg(
        label=("label", "first"), probability=("probability", "mean")
    )

def bootstrap_auc(frame, repeats=500, seed=42):
    rng = np.random.default_rng(seed)
    groups = [group for _, group in frame.groupby("participant_id")]
    values = []
    for _ in range(repeats):
        sample = pd.concat([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        if sample.label.nunique() == 2:
            values.append(roc_auc_score(sample.label, sample.probability))
    if not values:
        raise ValueError("Not enough valid participant bootstrap samples.")
    return [float(x) for x in np.percentile(values, [2.5, 97.5])]
