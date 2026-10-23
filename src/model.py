# src/model.py
import torch
import torch.nn as nn
import torchvision.models as models


class AudioCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = models.mobilenet_v2(weights=None)
        self.backbone.classifier = nn.Identity()
        self.fc = nn.Linear(1280, 128)

    def forward(self, x):
        return self.fc(self.backbone(x))


class TabularMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(4, 16),
            nn.ReLU(),
            nn.Linear(16, 32)
        )

    def forward(self, x):
        return self.net(x)


class LateFusionTBModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.audio_encoder = AudioCNN()
        self.tabular_encoder = TabularMLP()

        self.fusion_head = nn.Sequential(
            nn.Linear(128 + 32, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, audio_input, tabular_input):
        audio_emb = self.audio_encoder(audio_input)
        tab_emb = self.tabular_encoder(tabular_input)
        fused = torch.cat((audio_emb, tab_emb), dim=1)
        return self.fusion_head(fused)