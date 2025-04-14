import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split

# ------------------------------
# Dataset
# ------------------------------
class EmbeddingDataset(Dataset):
    def __init__(self, data):
        self.X = [torch.tensor(item['embedding'], dtype=torch.float32) for item in data]
        self.y = [0 if item['label'] == 'no' else 1 for item in data]

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], torch.tensor(self.y[idx], dtype=torch.long)

# ------------------------------
# Model
# ------------------------------
class GRUClassifier(nn.Module):
    def __init__(self, input_dim, hidden_dim=64):
        super().__init__()
        self.gru = nn.GRU(input_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, 2)

    def forward(self, x):
        x = x.unsqueeze(1)  # Shape: (batch, seq_len=1, input_dim)
        _, h = self.gru(x)
        logits = self.fc(h.squeeze(0))
        return logits

# ------------------------------
# Training
# ------------------------------
def train_model(model, dataloader, optimizer, criterion):
    model.train()
    for X, y in dataloader:
        optimizer.zero_grad()
        outputs = model(X)
        loss = criterion(outputs, y)
        loss.backward()
        optimizer.step()

def evaluate(model, dataloader):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for X, y in dataloader:
            outputs = model(X)
            preds = torch.argmax(outputs, dim=1)
            correct += (preds == y).sum().item()
            total += y.size(0)
    return correct / total

# ------------------------------
# Main
# ------------------------------
with open("labeled_embeddings.json") as f:
    data = json.load(f)

    train_data, val_data = train_test_split(data, test_size=0.2, random_state=42)

    train_dataset = EmbeddingDataset(train_data)
    val_dataset = EmbeddingDataset(val_data)

    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=16)

    input_dim = len(train_data[0]["embedding"])
    model = GRUClassifier(input_dim)

    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(10):
        train_model(model, train_loader, optimizer, criterion)
        acc = evaluate(model, val_loader)
        print(f"Epoch {epoch+1} - Val Accuracy: {acc:.4f}")

    # Save the model for export
    torch.save(model.state_dict(), "gru_classifier.pt")