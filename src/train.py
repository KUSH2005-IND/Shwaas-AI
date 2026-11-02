"""Train on frozen participant splits, then calibrate on validation data only."""
from __future__ import annotations
import argparse
from importlib.metadata import version
from pathlib import Path
import random
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from src.audio import FRONTEND_VERSION, load_audio, mel_images
from src.common import ROOT, SEED, TASK, run_cli, sha256_file, write_json
from src.features import read_features
from src.manifest import read_manifest
from src.metrics import calibrate, fit_calibrator, select_threshold

def cnn_scores(model, frame, device="cpu"):
    import torch
    model.eval()
    scores = []
    with torch.inference_mode():
        for row in frame.itertuples():
            windows = torch.from_numpy(mel_images(load_audio(row.audio_path))).to(device)
            scores.append(float(model(windows).reshape(-1).mean().cpu()))
    return np.asarray(scores)

def train_cnn(frame, epochs=20, patience=5, seed=SEED, device="cpu"):
    import torch
    from torch.utils.data import DataLoader, Dataset
    from src.model import AudioOnlyModel
    torch.manual_seed(seed)
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise ValueError("CUDA is unavailable; use --device cpu.")
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    train = frame[frame.split == "train"].reset_index(drop=True)
    validation = frame[frame.split == "validation"].reset_index(drop=True)
    # Verify files before fitting; no old cached spectrograms are reused.
    for row in frame.itertuples():
        if sha256_file(Path(row.audio_path)) != row.audio_sha256:
            raise ValueError(f"Audio checksum mismatch: {row.recording_id}.")
    rng = np.random.default_rng(seed)
    class Recordings(Dataset):
        def __len__(self):
            return len(train)
        def __getitem__(self, index):
            row = train.iloc[index]
            windows = mel_images(load_audio(row.audio_path))
            window = windows[rng.integers(len(windows))]
            return torch.from_numpy(window.copy()), torch.tensor(float(row.label))
    loader = DataLoader(Recordings(), batch_size=16, shuffle=True, num_workers=0)
    model = AudioOnlyModel().to(device)
    labels = train.label.to_numpy()
    weight = torch.tensor(float((labels == 0).sum() / (labels == 1).sum()), device=device)
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=weight)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    history, best_state, best_auc, stale = [], None, -1., 0
    for epoch in range(1, epochs + 1):
        model.train()
        total = 0.
        for windows, targets in loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(windows.to(device)).reshape(-1)
            loss = loss_fn(logits, targets.to(device).reshape(-1))
            loss.backward()
            optimizer.step()
            total += float(loss.detach()) * len(targets)
        scores = cnn_scores(model, validation, device)
        auc = float(roc_auc_score(validation.label, scores))
        history.append({"epoch": epoch, "train_loss": total / len(train), "validation_auroc": auc})
        print(f"Epoch {epoch}: loss={history[-1]['train_loss']:.4f}, validation AUROC={auc:.4f}")
        if auc > best_auc:
            best_auc, stale = auc, 0
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        else:
            stale += 1
        if stale >= patience:
            break
    if best_state is None:
        raise RuntimeError("No valid CNN checkpoint was produced.")
    model.load_state_dict(best_state, strict=True)
    return model.cpu(), history

def train_bundle(manifest, output, features=None, encoder="mel", epochs=20,
                 patience=5, seed=SEED, target_specificity=.90, device="cpu"):
    manifest, output = Path(manifest), Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"{output} is not empty. Choose a new model directory.")
    frame = read_manifest(manifest)
    random.seed(seed)
    np.random.seed(seed)
    train_mask = frame.split.eq("train").to_numpy()
    val_mask = frame.split.eq("validation").to_numpy()
    history, details = [], {}
    if encoder == "cnn":
        if epochs < 1 or patience < 1:
            raise ValueError("Epochs and patience must be positive.")
        model, history = train_cnn(frame, epochs, patience, seed, device)
        validation_scores = cnn_scores(model, frame[val_mask])
        kind, weights_name = "cnn", "model.pt"
    else:
        if features is None:
            features = ROOT / f"cache/{encoder}_features.npz"
        frame, X, details = read_features(Path(features), manifest)
        if details["encoder"] != encoder:
            raise ValueError("Requested encoder and cached features do not match.")
        best_auc, model = -1., None
        for strength in (.01, .1, 1., 10.):
            candidate = make_pipeline(StandardScaler(), LogisticRegression(
                C=strength, class_weight="balanced", max_iter=2000, random_state=seed
            ))
            candidate.fit(X[train_mask], frame.label.to_numpy()[train_mask])
            scores = candidate.decision_function(X[val_mask])
            auc = roc_auc_score(frame.label.to_numpy()[val_mask], scores)
            if auc > best_auc:
                best_auc, model = auc, candidate
        validation_scores = model.decision_function(X[val_mask])
        details["selected_C"] = float(model[-1].C)
        kind, weights_name = f"{encoder}-logreg", "model.joblib"
    calibration = fit_calibrator(validation_scores, frame.label.to_numpy()[val_mask])
    probabilities = calibrate(validation_scores, calibration)
    threshold = select_threshold(frame.label.to_numpy()[val_mask], probabilities, target_specificity)
    output.mkdir(parents=True, exist_ok=True)
    if encoder == "cnn":
        import torch
        torch.save(model.state_dict(), output / weights_name)
        pd.DataFrame(history).to_csv(output / "history.csv", index=False)
    else:
        joblib.dump(model, output / weights_name)
    checksum = sha256_file(output / weights_name)
    metadata = {
        "format_version": 1, "kind": kind, "task": TASK,
        "model_version": f"{kind}-{checksum[:12]}", "frontend_version": FRONTEND_VERSION,
        "manifest_sha256": sha256_file(manifest), "weights_sha256": checksum,
        "hear_revision": details.get("hear_revision"), "selected_C": details.get("selected_C"),
        "calibration": calibration, "threshold": threshold,
        "threshold_selection": {"split": "validation", "target_specificity": target_specificity,
                                "criterion": "maximum_sensitivity_at_minimum_specificity"},
        "seed": seed, "calibration_split": "validation",
        "versions": {name: version(name) for name in ("numpy", "scipy", "scikit-learn", "librosa")},
    }
    write_json(output / "bundle.json", metadata)
    print(f"Saved {output}. Test data was not used for fitting, calibration or threshold selection.")
    return metadata

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.csv")
    parser.add_argument("--encoder", choices=("mel", "hear", "cnn"), default="mel")
    parser.add_argument("--features", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--target-specificity", type=float, default=.90)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    output = args.output or ROOT / f"artifacts/{args.encoder}"
    train_bundle(args.manifest, output, args.features, args.encoder, args.epochs,
                 args.patience, args.seed, args.target_specificity, args.device)

if __name__ == "__main__":
    run_cli(main)
