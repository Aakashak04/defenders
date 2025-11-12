#!/usr/bin/env python3
"""
Train LSTM Autoencoder model
"""
import os
import sys
import json
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from torch.utils.data import Dataset, DataLoader

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aegismas_api.agents.lstm_agent import LSTMAutoencoder
from aegismas_api.config import config
from aegismas_api.utils import extract_features


class RequestDataset(Dataset):
    """Dataset for training LSTM."""
    
    def __init__(self, samples, seq_length=20):
        self.samples = samples
        self.seq_length = seq_length
        self.sequences = self._build_sequences()
    
    def _build_sequences(self):
        """Build sequences from samples."""
        sequences = []
        current_seq = []
        
        for sample in self.samples:
            features = extract_features(
                method=sample["method"],
                path=sample["path"],
                body_sample=sample.get("body_sample", ""),
                query=sample.get("query", ""),
            )
            current_seq.append(features)
            
            if len(current_seq) >= self.seq_length:
                sequences.append(current_seq[-self.seq_length:])
                current_seq = current_seq[-self.seq_length//2:]  # Overlap
        
        return sequences
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        seq = self.sequences[idx]
        return torch.FloatTensor(seq)  # Shape: [seq_length, feature_dim]


def train_model(epochs=3, batch_size=32, learning_rate=0.001):
    """Train LSTM model."""
    # Load synthetic data
    data_file = Path("training_data/synthetic_dataset.json")
    if not data_file.exists():
        print("Error: training_data/synthetic_dataset.json not found. Run gen_synthetic.py first.")
        return
    
    with open(data_file, "r") as f:
        samples = json.load(f)
    
    print(f"Loaded {len(samples)} samples")
    
    # Filter to benign samples for autoencoder training
    benign_samples = [s for s in samples if not s.get("malicious", False)]
    print(f"Using {len(benign_samples)} benign samples for training")
    
    # Create dataset
    dataset = RequestDataset(benign_samples, seq_length=config.LSTM_SEQ_LENGTH)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # Initialize model
    model = LSTMAutoencoder(
        input_dim=config.LSTM_FEATURE_DIM,
        hidden_size=config.LSTM_HIDDEN_SIZE,
        num_layers=config.LSTM_NUM_LAYERS,
    )
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.train()
    
    # Loss and optimizer
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # Training loop
    print(f"Training on {device}...")
    for epoch in range(epochs):
        total_loss = 0.0
        num_batches = 0
        
        for batch in dataloader:
            # batch shape: [batch_size, seq_length, feature_dim]
            # Need to add batch dimension if missing
            if batch.dim() == 2:
                batch = batch.unsqueeze(0)  # Add batch dimension
            batch = batch.to(device)
            
            # Forward
            reconstructed, _ = model(batch)
            loss = criterion(reconstructed, batch)
            
            # Backward
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        avg_loss = total_loss / max(num_batches, 1)
        print(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.6f}")
    
    # Save model
    model.eval()
    os.makedirs(config.MODELS_DIR, exist_ok=True)
    model_path = config.LSTM_MODEL_PATH
    torch.save(model.state_dict(), model_path)
    print(f"Saved model to {model_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train LSTM Autoencoder")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    
    args = parser.parse_args()
    
    train_model(epochs=args.epochs, batch_size=args.batch_size, learning_rate=args.lr)

