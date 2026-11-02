"""Run the documented module commands in real subprocesses, using synthetic audio."""
import subprocess
import sys

from src.common import ROOT


def test_documented_pipeline_and_plots(dataset):
    directory, _, frame = dataset
    raw = directory / "cli_raw.csv"
    frame.drop(columns="split").to_csv(raw, index=False)
    manifest = directory / "cli_manifest.csv"
    features = directory / "cli_features.npz"
    model = directory / "cli_model"
    commands = [
        ["src.manifest", "--input", str(raw), "--output", str(manifest)],
        ["src.features", "--manifest", str(manifest), "--output", str(features)],
        ["src.train", "--manifest", str(manifest), "--features", str(features), "--output", str(model)],
        ["src.evaluate", "--manifest", str(manifest), "--features", str(features),
         "--model", str(model), "--bootstrap", "10"],
        ["src.plot", "--evaluation", str(model / "evaluation")],
    ]
    for arguments in commands:
        result = subprocess.run([sys.executable, "-m", *arguments], cwd=ROOT,
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
    assert (model / "evaluation/evaluation.png").stat().st_size > 1000


def test_missing_data_gives_actionable_message_without_traceback(tmp_path):
    result = subprocess.run([sys.executable, "-m", "src.train", "--manifest", str(tmp_path / "missing.csv")],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "Run python -m src.prepare" in result.stderr
    assert "Traceback" not in result.stderr
