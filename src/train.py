# src/train.py
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
import numpy as np
from model import LateFusionTBModel

# --- ROBUST PATHING ---
PROJECT_ROOT = Path(__file__).parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"

print("🧠 Starting Model Training...")

# 1. Load the cached spectrograms
cache_file = CACHE_DIR / "spectrograms.pt"
print(f"📥 Loading data from {cache_file}...")
cached_data = torch.load(cache_file, weights_only=True)
print(f"✅ Loaded {len(cached_data)} samples.")


# 2. Custom PyTorch Dataset
class CoughFusionDataset(Dataset):
    def __init__(self, data):
        self.data = data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        audio_tensor = item['tensor']
        label = item['label']

        # PROXY TASK HACK: Coswara doesn't have the 4 NTEP questions.
        # We generate synthetic tabular data correlated with the label to train the fusion head.
        # If label is 1 (Abnormal), we bias the "quiz" answers towards 'Yes' (1).
        if label == 1:
            tabular_data = torch.tensor(np.random.choice([0, 1], size=4, p=[0.3, 0.7]), dtype=torch.float32)
        else:
            tabular_data = torch.tensor(np.random.choice([0, 1], size=4, p=[0.8, 0.2]), dtype=torch.float32)

        return audio_tensor, tabular_data, torch.tensor(label, dtype=torch.float32)


# 3. Split into Train and Validation (80/20)
dataset = CoughFusionDataset(cached_data)
train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size
train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])

train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)

print(f"📊 Train samples: {train_size} | Val samples: {val_size}")

# 4. Initialize Model, Loss, and Optimizer
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"🚀 Using device: {device}")

model = LateFusionTBModel().to(device)
criterion = nn.BCELoss()  # Binary Cross Entropy for probability output
optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)

# 5. Training Loop
EPOCHS = 15
print(f"\n🏋️ Starting training for {EPOCHS} epochs...")

for epoch in range(EPOCHS):
    # --- TRAINING PHASE ---
    model.train()
    train_loss = 0.0
    train_correct = 0

    for audios, tabs, labels in train_loader:
        audios, tabs, labels = audios.to(device), tabs.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(audios, tabs).squeeze()
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        train_loss += loss.item() * audios.size(0)
        preds = (outputs >= 0.5).float()
        train_correct += (preds == labels).sum().item()

    train_loss /= len(train_loader.dataset)
    train_acc = train_correct / len(train_loader.dataset)

    # --- VALIDATION PHASE ---
    model.eval()
    val_loss = 0.0
    val_correct = 0

    with torch.no_grad():
        for audios, tabs, labels in val_loader:
            audios, tabs, labels = audios.to(device), tabs.to(device), labels.to(device)
            outputs = model(audios, tabs).squeeze()
            loss = criterion(outputs, labels)

            val_loss += loss.item() * audios.size(0)
            preds = (outputs >= 0.5).float()
            val_correct += (preds == labels).sum().item()

    val_loss /= len(val_loader.dataset)
    val_acc = val_correct / len(val_loader.dataset)


    print(f"Epoch [{epoch + 1}/{EPOCHS}] | "
          f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
          f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}")

# 6. Save the trained model
save_path = CACHE_DIR / "late_fusion_model.pth"
torch.save(model.state_dict(), save_path)
print(f"\n💾 Model saved to {save_path}")
print("✅ Day 4 Complete! Your Late-Fusion Brain is trained.")