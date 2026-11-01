"""Optional spectrogram attribution debugger; no OpenCV dependency."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import torch
from src.common import ROOT, run_cli
from src.audio import load_audio, mel_images
from src.inference import Predictor

class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.activations = None
        self._hook = target_layer.register_forward_hook(self._save_activation)

    def _save_activation(self, module, inputs, output):
        self.activations = output
        if output.requires_grad:
            output.retain_grad()

    def close(self):
        self._hook.remove()

    def generate_cam(self, audio_tensor, tabular_tensor=None):
        from matplotlib import colormaps
        self.model.eval()
        self.model.zero_grad(set_to_none=True)
        with torch.enable_grad():
            output = (self.model(audio_tensor, tabular_tensor) if tabular_tensor is not None
                      else self.model(audio_tensor))
            output.reshape(-1)[0].backward()
        if self.activations is None or self.activations.grad is None:
            raise RuntimeError("No attribution gradients; use a trainable CNN outside inference_mode.")
        activation = self.activations.detach()
        weights = self.activations.grad.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * activation).sum(dim=1, keepdim=True))
        cam = torch.nn.functional.interpolate(cam, size=(224, 224), mode="bilinear", align_corners=False)
        image = cam[0, 0].cpu().numpy()
        image = (image - image.min()) / max(float(np.ptp(image)), 1e-8)
        return (colormaps["jet"](image)[..., :3] * 255).astype(np.uint8)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/gradcam.png")
    args = parser.parse_args()
    predictor = Predictor(args.model)
    if predictor.kind != "cnn":
        raise ValueError("This debugger supports CNN bundles only.")
    from matplotlib import pyplot as plt
    debugger = GradCAM(predictor.model, predictor.model.audio_encoder.backbone.features[-1])
    try:
        windows = torch.from_numpy(mel_images(load_audio(args.audio)))
        image = debugger.generate_cam(windows[:1])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        plt.imsave(args.output, image)
    finally:
        debugger.close()
    print(f"Saved {args.output}. Attribution shows network sensitivity, not a clinical explanation.")

if __name__ == "__main__":
    run_cli(main)
