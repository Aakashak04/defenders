"""
Statistical Agent - IsolationForest-based anomaly detection
"""
import os
import pickle
import numpy as np
from typing import Dict, Tuple, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ..config import config
from ..utils import extract_features


class StatsAgent:
    """IsolationForest-based statistical anomaly detection."""
    
    def __init__(self):
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.is_trained = False
        self._load_model()
    
    def _load_model(self):
        """Load pretrained model if available."""
        model_path = config.STATS_MODEL_PATH
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data.get('model')
                    self.scaler = data.get('scaler')
                    self.is_trained = data.get('is_trained', False)
                print(f"Loaded pretrained stats model from {model_path}")
            except Exception as e:
                print(f"Failed to load stats model: {e}")
                self._init_default_model()
        else:
            self._init_default_model()
    
    def _init_default_model(self):
        """Initialize default untrained model (bootstrap mode)."""
        self.model = IsolationForest(
            contamination=config.STATS_CONTAMINATION,
            random_state=42,
            n_estimators=100,
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        print("Initialized default stats model (bootstrap mode - will score conservatively)")
    
    def fit(self, X: np.ndarray):
        """Train the model on feature vectors."""
        if len(X) < 10:
            print("Warning: Not enough data to train. Need at least 10 samples.")
            return
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train IsolationForest
        self.model.fit(X_scaled)
        self.is_trained = True
        
        print(f"Trained stats model on {len(X)} samples")
    
    def evaluate(
        self,
        method: str,
        path: str,
        body_sample: str = "",
        query: str = "",
        hour_of_day: Optional[int] = None,
        recent_rps: float = 0.0,
    ) -> Tuple[float, Dict[str, str]]:
        """
        Evaluate request and return anomaly score (0-1).
        
        Returns:
            (score, signals_dict)
        """
        # Extract features
        features = extract_features(method, path, body_sample, query, hour_of_day, recent_rps)
        X = np.array([features])
        
        # Scale
        if self.scaler is not None:
            try:
                X_scaled = self.scaler.transform(X)
            except:
                # If scaler not fitted, fit on this single sample (bootstrap)
                X_scaled = self.scaler.fit_transform(X)
        else:
            X_scaled = X
        
        # Predict
        if self.model is not None:
            try:
                # Get anomaly score (negative values = more anomalous)
                anomaly_score = self.model.score_samples(X_scaled)[0]
                
                # Normalize to 0-1 (more negative = higher score)
                # IsolationForest scores are typically in range [-0.5, 0.5]
                # Convert: score = (0.5 - anomaly_score) / 1.0, clamped to [0, 1]
                normalized_score = max(0.0, min(1.0, (0.5 - anomaly_score) / 1.0))
                
                # If not trained, be conservative (lower scores)
                if not self.is_trained:
                    normalized_score = normalized_score * 0.3  # Scale down in bootstrap mode
                
                signals = {
                    "stats_score": f"{normalized_score:.3f}",
                    "raw_anomaly": f"{anomaly_score:.3f}",
                    "trained": str(self.is_trained),
                }
                
                return normalized_score, signals
            except Exception as e:
                print(f"Stats agent evaluation error: {e}")
                return 0.1, {"error": str(e)[:50]}
        else:
            return 0.1, {"status": "no_model"}
    
    def save_model(self, path: Optional[str] = None):
        """Save model to disk."""
        if path is None:
            path = config.STATS_MODEL_PATH
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        data = {
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained,
        }
        
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"Saved stats model to {path}")

