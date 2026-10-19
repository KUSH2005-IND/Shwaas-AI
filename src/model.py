# src/model.py
import torch
import torch.nn as nn
import torchvision.models as models


class AudioCNN(nn.Module):
    """Extracts a 128-dimensional embedding from a 224x224 spectrogram."""

    def __init__(self):
        super().__init__()
        # Using MobileNetV2: lightweight, fast, perfect for edge/mobile deployment later
        self.backbone = models.mobilenet_v2(weights=None)
        # Remove the final classification layer
        self.backbone.classifier = nn.Identity()
        # Project the 1280-dim output to a 128-dim embedding
        self.fc = nn.Linear(1280, 128)

    def forward(self, x):  # x is [batch, 3, 224, 224]
        features = self.backbone(x)
        return self.fc(features)


class TabularMLP(nn.Module):
    """Extracts a 32-dimensional embedding from the 4-question clinical quiz."""

    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(4, 16),
            nn.ReLU(),
            nn.Linear(16, 32)  # 32-dimensional embedding
        )

    def forward(self, x):  # x is [batch, 4]
        return self.net(x)


class LateFusionTBModel(nn.Module):
    """Combines Audio and Tabular embeddings to output a single risk probability."""

    def __init__(self):
        super().__init__()
        self.audio_encoder = AudioCNN()
        self.tabular_encoder = TabularMLP()

        # The Fusion Head: Combines 128 (audio) + 32 (tabular) = 160 dimensions
        self.fusion_head = nn.Sequential(
            nn.Linear(128 + 32, 64),
            nn.ReLU(),
            nn.Dropout(0.3),  # Prevents overfitting
            nn.Linear(64, 1),
            nn.Sigmoid()  # Outputs a probability between 0.0 and 1.0
        )

    def forward(self, audio_input, tabular_input):
        audio_emb = self.audio_encoder(audio_input)
        tab_emb = self.tabular_encoder(tabular_input)

        # Concatenate the embeddings
        fused = torch.cat((audio_emb, tab_emb), dim=1)
        return self.fusion_head(fused)