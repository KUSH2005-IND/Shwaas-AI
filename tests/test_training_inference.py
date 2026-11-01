import json
from types import SimpleNamespace
import numpy as np
import pytest
from src.evaluate import evaluate_bundle
from src.inference import Predictor
from src.train import train_bundle

def test_baseline_end_to_end_matches_cached_and_waveform_inference(dataset, bundle):
    directory, manifest, frame = dataset
    output, features = bundle
    cached = evaluate_bundle(output, manifest, directory / "cached_eval", features, bootstrap=20)
    waveform = evaluate_bundle(output, manifest, directory / "wave_eval", bootstrap=20)
    assert cached["recording_metrics"] == waveform["recording_metrics"]
    assert cached["n_test_participants"] == frame[frame.split == "test"].participant_id.nunique()
    assert "Infinity" not in (directory / "cached_eval/metrics.json").read_text()
    prediction = Predictor(output).predict_file(frame.audio_path.iloc[0])
    assert 0 <= prediction["score"] <= 1

def test_test_audio_does_not_influence_training(dataset, bundle, monkeypatch):
    directory, manifest, frame = dataset
    _, features = bundle
    # Train reads train/validation cached features. Test feature perturbations
    # cannot influence parameter choice, calibration or operating threshold.
    from src import train
    original = train.read_features
    def changed(path, manifest):
        f, X, meta = original(path, manifest)
        X[f.split.eq("test")] = 123456.
        return f, X, meta
    monkeypatch.setattr(train, "read_features", changed)
    metadata = train_bundle(manifest, directory / "perturbed", features=features)
    original_meta = json.loads((bundle[0] / "bundle.json").read_text())
    assert metadata["selected_C"] == original_meta["selected_C"]
    assert metadata["calibration"] == original_meta["calibration"]
    assert metadata["threshold"] == original_meta["threshold"]

def test_cnn_training_checkpoint_and_single_record_inference(dataset):
    torch = pytest.importorskip("torch")
    torch.set_num_threads(2)
    directory, manifest, frame = dataset
    output = directory / "cnn"
    train_bundle(manifest, output, encoder="cnn", epochs=1, patience=1)
    predictor = Predictor(output)
    result = predictor.predict_file(frame.audio_path.iloc[0])
    assert np.isfinite(result["score"])
    assert len((output / "history.csv").read_text().splitlines()) == 2
    from src.audio import load_audio, mel_images
    from src.gradcam import GradCAM
    debugger = GradCAM(predictor.model, predictor.model.audio_encoder.backbone.features[-1])
    try:
        image = debugger.generate_cam(torch.from_numpy(mel_images(load_audio(frame.audio_path.iloc[0]))))
        assert image.shape == (224, 224, 3)
        assert np.isfinite(image).all()
    finally:
        debugger.close()

def test_hear_frontend_and_aggregation_without_gated_weights():
    torch = pytest.importorskip("torch")
    torch.set_num_threads(2)
    from src.hear import HeAREncoder
    from src.vendor.hear_audio_utils import preprocess_audio
    t = np.arange(64000) / 16000
    y = (.1 * np.sin(2 * np.pi * 600 * t)).astype(np.float32)
    prepared = preprocess_audio(torch.from_numpy(y[:32000][None].copy()))
    assert prepared.shape == (1, 1, 192, 128)
    assert torch.isfinite(prepared).all()
    class FrozenModel:
        def __call__(self, batch, return_dict=True):
            return SimpleNamespace(pooler_output=batch.mean(dim=(1, 2, 3))[:, None].repeat(1, 512))
    encoder = HeAREncoder.__new__(HeAREncoder)
    encoder.model, encoder.device = FrozenModel(), "cpu"
    vector = encoder.encode(y)
    assert vector.shape == (512,)
    assert np.isfinite(vector).all()
