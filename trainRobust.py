import json
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import logging
from torch.optim.lr_scheduler import ReduceLROnPlateau

# Setup logging
logging.basicConfig(filename='training.log', level=logging.INFO)

# Config
config = {
    'batch_size': 16,
    'hidden_dim': 64,
    'num_layers': 2,
    'dropout': 0.3,
    'lr': 0.001,
    'epochs': 10,
    'patience': 3,
    'input_file': 'labeled_embeddings.json',
    'model_path': 'gru_classifier.pt'
}

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Data Loading
def load_data(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} does not exist")
    with open(file_path, 'r') as f:
        data = json.load(f)
    if not data:
        raise ValueError("Empty dataset")
    return data

# Dataset
class EmbeddingDataset(Dataset):
    def __init__(self, data):
        self.X, self.y = [], []
        for item in data:
            if 'embedding' not in item or 'label' not in item:
                raise KeyError("Missing 'embedding' or 'label'")
            self.X.append(torch.tensor(item['embedding'], dtype=torch.float32))
            self.y.append(0 if item['label'] == 'no' else 1)
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], torch.tensor(self.y[idx], dtype=torch.long)

# Model
class GRUClassifier(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, num_layers=2, dropout=0.3):
        super().__init__()
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers=num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, 2)
    
    def forward(self, x):
        x = x.unsqueeze(1)
        _, h = self.gru(x)
        h = h[-1]
        h = self.dropout(h)
        logits = self.fc(h)
        return logits

# Training
def train_model(model, train_loader, val_loader, optimizer, criterion, config, device):
    scheduler = ReduceLROnPlateau(optimizer, mode='max', factor=0.1, patience=2, verbose=True)
    best_acc = 0
    patience_counter = 0
    for epoch in range(config['epochs']):
        model.train()
        train_loss = 0
        for X, y in train_loader:
            X, y = X.to(device), y.to(device)
            optimizer.zero_grad()
            outputs = model(X)
            loss = criterion(outputs, y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item()
        
        val_acc = evaluate(model, val_loader, device)
        logging.info(f"Epoch {epoch+1} - Train Loss: {train_loss/len(train_loader):.4f}, Val Accuracy: {val_acc:.4f}")
        print(f"Epoch {epoch+1} - Train Loss: {train_loss/len(train_loader):.4f}, Val Accuracy: {val_acc:.4f}")
        
        scheduler.step(val_acc)
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), config['model_path'])
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= config['patience']:
                print("Early stopping triggered")
                break

# Evaluation
def evaluate(model, dataloader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for X, y in dataloader:
            X, y = X.to(device), y.to(device)
            outputs = model(X)
            preds = torch.argmax(outputs, dim=1)
            correct += (preds == y).sum().item()
            total += y.size(0)
    return correct / total

# Main
def main(config):
    # Load and preprocess data
    data = load_data(config['input_file'])
    scaler = StandardScaler()
    embeddings = [item['embedding'] for item in data]
    scaled_embeddings = scaler.fit_transform(embeddings)
    for i, item in enumerate(data):
        item['embedding'] = scaled_embeddings[i].tolist()
    
    train_data, val_data = train_test_split(data, test_size=0.2, random_state=42)
    train_dataset = EmbeddingDataset(train_data)
    val_dataset = EmbeddingDataset(val_data)
    
    train_loader = DataLoader(train_dataset, batch_size=config['batch_size'], shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=config['batch_size'])
    
    # Initialize model
    input_dim = len(train_data[0]["embedding"])
    model = GRUClassifier(input_dim, config['hidden_dim'], config['num_layers'], config['dropout']).to(device)
    
    optimizer = optim.Adam(model.parameters(), lr=config['lr'])
    criterion = nn.CrossEntropyLoss()
    
    # Train
    train_model(model, train_loader, val_loader, optimizer, criterion, config, device)

if __name__ == "__main__":
    main(config)