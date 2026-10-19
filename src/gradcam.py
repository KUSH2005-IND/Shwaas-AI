# src/gradcam.py
import torch
import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from src.model import LateFusionTBModel


class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.gradients = None
        self.activations = None

        # Register hooks to capture gradients and activations
        target_layer.register_forward_hook(self.save_activation)
        target_layer.register_full_backward_hook(self.save_gradient)

    def save_activation(self, module, input, output):
        self.activations = output.detach()

    def save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate_cam(self, audio_tensor, tabular_tensor):
        self.model.eval()
        self.model.zero_grad()

        # Forward pass
        output = self.model(audio_tensor, tabular_tensor)

        # Backward pass directly on the single sigmoid probability output
        output[0].backward()

        # Calculate CAM
        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = (weights * self.activations).sum(dim=1, keepdim=True)
        cam = torch.relu(cam)  # Only positive influences

        # Resize to 224x224
        cam = torch.nn.functional.interpolate(cam, size=(224, 224), mode='bilinear', align_corners=False)
        cam = cam.squeeze().cpu().numpy()

        # Normalize to 0-1
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        cam = np.uint8(255 * cam)

        # Apply Jet colormap
        heatmap = cv2.applyColorMap(cam, cv2.COLORMAP_JET)
        return heatmap


def test_gradcam():
    print("🎨 Testing Grad-CAM Visualization...")
    PROJECT_ROOT = Path(__file__).parent.parent
    CACHE_DIR = PROJECT_ROOT / "cache"

    # Load model
    model = LateFusionTBModel()
    model.load_state_dict(torch.load(CACHE_DIR / "late_fusion_model.pth", weights_only=True))
    model.eval()

    # Load one sample
    cached_data = torch.load(CACHE_DIR / "spectrograms.pt", weights_only=True)
    sample = cached_data[0]  # Just grab the first one for testing
    audio_tensor = sample['tensor'].unsqueeze(0)  # Add batch dimension
    tabular_tensor = torch.zeros((1, 4), dtype=torch.float32)  # Neutral tabular input

    # Target the last convolutional layer of MobileNetV2
    target_layer = model.audio_encoder.backbone.features[-1][0]

    gradcam = GradCAM(model, target_layer)
    heatmap = gradcam.generate_cam(audio_tensor, tabular_tensor)

    # Save the heatmap
    output_path = PROJECT_ROOT / "reports" / "gradcam_demo.jpg"
    cv2.imwrite(str(output_path), heatmap)
    print(f"✅ Grad-CAM heatmap saved to: {output_path}")
    print("   (Open this image to see the red/yellow 'hotspots' on the spectrogram!)")


if __name__ == "__main__":
    test_gradcam()