"""
LSTM Agent - PyTorch LSTM Autoencoder for sequence anomaly detection
"""
import os
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Tuple, Optional, List
import redis
from collections import deque

from ..config import config
from ..utils import extract_features


class LSTMAutoencoder(nn.Module):
    """Small LSTM Autoencoder for anomaly detection."""
    
    def __init__(self, input_dim: int, hidden_size: int = 64, num_layers: int = 2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # Encoder
        self.encoder = nn.LSTM(
            input_dim,
            hidden_size,
            num_layers,
            batch_first=True,
        )
        
        # Decoder
        self.decoder = nn.LSTM(
            hidden_size,
            hidden_size,
            num_layers,
            batch_first=True,
        )
        
        # Output projection
        self.output_proj = nn.Linear(hidden_size, input_dim)
    
    def forward(self, x):
        """Forward pass: encode then decode."""
        # Encode
        encoded, (h_n, c_n) = self.encoder(x)
        
        # Use last hidden state as context
        last_hidden = encoded[:, -1:, :]  # Take last timestep
        
        # Decode (repeat last hidden state for sequence length)
        decoded, _ = self.decoder(last_hidden.repeat(1, x.size(1), 1))
        
        # Project to input dimension
        output = self.output_proj(decoded)
        
        return output, encoded
    
    def encode(self, x):
        """Encode input to hidden representation."""
        encoded, _ = self.encoder(x)
        return encoded


class LSTMAgent:
    """LSTM-based sequence anomaly detection agent."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.model: Optional[LSTMAutoencoder] = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.redis_client = redis_client
        self.seq_length = config.LSTM_SEQ_LENGTH
        self.feature_dim = config.LSTM_FEATURE_DIM
        self._load_model()
    
    def _load_model(self):
        """Load pretrained model if available."""
        model_path = config.LSTM_MODEL_PATH
        if os.path.exists(model_path):
            try:
                self.model = LSTMAutoencoder(
                    input_dim=self.feature_dim,
                    hidden_size=config.LSTM_HIDDEN_SIZE,
                    num_layers=config.LSTM_NUM_LAYERS,
                )
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                self.model.eval()
                self.model.to(self.device)
                print(f"Loaded pretrained LSTM model from {model_path}")
            except Exception as e:
                print(f"Failed to load LSTM model: {e}")
                self._init_default_model()
        else:
            self._init_default_model()
    
    def _init_default_model(self):
        """Initialize default untrained model."""
        self.model = LSTMAutoencoder(
            input_dim=self.feature_dim,
            hidden_size=config.LSTM_HIDDEN_SIZE,
            num_layers=config.LSTM_NUM_LAYERS,
        )
        self.model.eval()
        self.model.to(self.device)
        print("Initialized default LSTM model (bootstrap mode - will score conservatively)")
    
    def _get_sequence(self, ip: str) -> List[List[float]]:
        """Get recent sequence for IP from Redis or return empty."""
        if self.redis_client is None:
            return []
        
        try:
            key = f"lstm:seq:{ip}"
            data = self.redis_client.lrange(key, 0, self.seq_length - 1)
            sequence = [eval(x.decode()) if isinstance(x, bytes) else eval(x) for x in data]
            return sequence[-self.seq_length:] if len(sequence) >= self.seq_length else []
        except Exception as e:
            print(f"Error getting sequence for {ip}: {e}")
            return []
    
    def _add_to_sequence(self, ip: str, features: List[float]):
        """Add features to IP's sequence buffer in Redis."""
        if self.redis_client is None:
            return
        
        try:
            key = f"lstm:seq:{ip}"
            # Push new features
            self.redis_client.lpush(key, str(features))
            # Trim to seq_length
            self.redis_client.ltrim(key, 0, self.seq_length - 1)
            # Set expiry (1 hour)
            self.redis_client.expire(key, 3600)
        except Exception as e:
            print(f"Error adding to sequence for {ip}: {e}")
    
    def evaluate(
        self,
        ip: str,
        method: str,
        path: str,
        body_sample: str = "",
        query: str = "",
        hour_of_day: Optional[int] = None,
        recent_rps: float = 0.0,
    ) -> Tuple[float, Dict[str, str]]:
        """
        Evaluate request using LSTM sequence analysis.
        
        Returns:
            (score, signals_dict)
        """
        # Extract features
        features = extract_features(method, path, body_sample, query, hour_of_day, recent_rps)
        
        # Get sequence for this IP
        sequence = self._get_sequence(ip)
        
        # If no sequence history, return neutral score
        if len(sequence) < self.seq_length:
            # Add current features to sequence
            self._add_to_sequence(ip, features)
            return 0.1, {"status": "insufficient_history", "seq_len": str(len(sequence))}
        
        # Add current features
        sequence.append(features)
        sequence = sequence[-self.seq_length:]  # Keep only last seq_length
        self._add_to_sequence(ip, features)
        
        # Convert to tensor
        try:
            seq_tensor = torch.FloatTensor([sequence]).to(self.device)
            
            # Forward pass
            with torch.no_grad():
                reconstructed, encoded = self.model(seq_tensor)
                
                # Compute reconstruction error (MSE)
                mse = nn.MSELoss()(reconstructed, seq_tensor)
                mse_value = mse.item()
                
                # Normalize to 0-1 score
                # Higher reconstruction error = more anomalous
                # Typical MSE for normal sequences: 0.01-0.1
                # Anomalous: > 0.1
                normalized_score = min(1.0, mse_value * 10.0)  # Scale factor
                
                # If model not trained (default), be conservative
                if not os.path.exists(config.LSTM_MODEL_PATH):
                    normalized_score = normalized_score * 0.2  # Scale down in bootstrap
                
                signals = {
                    "lstm_score": f"{normalized_score:.3f}",
                    "mse": f"{mse_value:.6f}",
                    "seq_len": str(len(sequence)),
                }
                
                return normalized_score, signals
        except Exception as e:
            print(f"LSTM evaluation error: {e}")
            return 0.1, {"error": str(e)[:50]}
    
    def save_model(self, path: Optional[str] = None):
        """Save model to disk."""
        if path is None:
            path = config.LSTM_MODEL_PATH
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save(self.model.state_dict(), path)
        print(f"Saved LSTM model to {path}")

