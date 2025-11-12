"""
Advanced Anomaly Detection Model using Autoencoder + One-Class SVM Ensemble.

This model provides superior accuracy compared to Isolation Forest alone by:
1. Using deep learning (Autoencoder) to learn complex normal patterns
2. Combining with One-Class SVM for non-linear boundary detection
3. Ensemble voting for robust predictions
4. Advanced feature engineering and normalization
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.svm import OneClassSVM
from sklearn.ensemble import IsolationForest
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None
    # Create a dummy base class for when PyTorch is not available
    class DummyModule:
        pass
    nn_module_base = DummyModule
    print("[WARNING] PyTorch not available. Falling back to sklearn-only models.")


# ----------------------------------------------------------------------------------
# Autoencoder Neural Network for Deep Learning Anomaly Detection
# ----------------------------------------------------------------------------------
if TORCH_AVAILABLE:
    class TrafficAutoencoder(nn.Module):
        """
        Autoencoder neural network that learns to reconstruct normal traffic patterns.
        High reconstruction error indicates anomalies.
        """

        def __init__(self, input_dim: int, encoding_dim: int = 8, hidden_dims: Tuple[int, ...] = (16, 12)):
            super().__init__()
            
            # Encoder layers
            encoder_layers = []
            prev_dim = input_dim
            for hidden_dim in hidden_dims:
                encoder_layers.extend([
                    nn.Linear(prev_dim, hidden_dim),
                    nn.ReLU(),
                    nn.Dropout(0.1),
                ])
                prev_dim = hidden_dim
            encoder_layers.append(nn.Linear(prev_dim, encoding_dim))
            self.encoder = nn.Sequential(*encoder_layers)

            # Decoder layers (mirror of encoder)
            decoder_layers = []
            prev_dim = encoding_dim
            for hidden_dim in reversed(hidden_dims):
                decoder_layers.extend([
                    nn.Linear(prev_dim, hidden_dim),
                    nn.ReLU(),
                    nn.Dropout(0.1),
                ])
                prev_dim = hidden_dim
            decoder_layers.append(nn.Linear(prev_dim, input_dim))
            self.decoder = nn.Sequential(*decoder_layers)

        def forward(self, x):
            encoded = self.encoder(x)
            decoded = self.decoder(encoded)
            return decoded

        def encode(self, x):
            """Get encoded representation."""
            return self.encoder(x)

        def reconstruct(self, x):
            """Get reconstruction."""
            return self.decoder(self.encoder(x))
else:
    # Dummy class when PyTorch is not available
    TrafficAutoencoder = None


# ----------------------------------------------------------------------------------
# Advanced Model Configuration
# ----------------------------------------------------------------------------------
@dataclass(frozen=True)
class AdvancedModelConfig:
    """Configuration for the advanced ensemble model."""

    # Feature engineering
    feature_columns: Tuple[str, ...] = (
        "requests_per_minute",
        "avg_payload_bytes",
        "avg_response_time_ms",
        "error_rate_pct",
        "status_code",
    )

    # Autoencoder settings
    encoding_dim: int = 8
    hidden_dims: Tuple[int, ...] = (16, 12)
    autoencoder_epochs: int = 100
    autoencoder_batch_size: int = 32
    autoencoder_lr: float = 0.001
    reconstruction_threshold_percentile: float = 95.0  # Top 5% reconstruction error = anomaly

    # One-Class SVM settings
    svm_nu: float = 0.1  # Expected fraction of outliers
    svm_gamma: str = "scale"  # RBF kernel parameter

    # Isolation Forest (as backup)
    if_contamination: float = 0.15
    if_n_estimators: int = 200

    # Ensemble voting
    ensemble_vote_threshold: int = 2  # Need 2+ models to agree for anomaly

    random_state: int = 42


# ----------------------------------------------------------------------------------
# Advanced Anomaly Detector with Ensemble
# ----------------------------------------------------------------------------------
class AdvancedAnomalyDetector:
    """
    Advanced ensemble detector combining Autoencoder, One-Class SVM, and Isolation Forest.
    """

    def __init__(self, config: AdvancedModelConfig):
        self.config = config
        self.scaler = RobustScaler()  # More robust to outliers than StandardScaler
        self.autoencoder: TrafficAutoencoder | None = None
        self.svm: OneClassSVM | None = None
        self.isolation_forest: IsolationForest | None = None
        self.reconstruction_threshold: float | None = None
        self._is_fitted = False

    def fit(self, normal_data: pd.DataFrame) -> None:
        """Train all ensemble models on normal traffic data."""

        feature_cols = list(self.config.feature_columns)
        X = normal_data[feature_cols].copy()

        # Feature engineering: add derived features
        X = self._engineer_features(X)

        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        X_scaled_df = pd.DataFrame(X_scaled, columns=X.columns)

        # Train Autoencoder (if PyTorch available)
        if TORCH_AVAILABLE:
            self.autoencoder = self._train_autoencoder(X_scaled_df)
            # Calculate reconstruction threshold on training data
            reconstructions = self._get_reconstructions(X_scaled_df)
            reconstruction_errors = np.mean((X_scaled - reconstructions) ** 2, axis=1)
            self.reconstruction_threshold = np.percentile(
                reconstruction_errors, self.config.reconstruction_threshold_percentile
            )
            print(f"[Advanced Detector] Autoencoder trained. Reconstruction threshold: {self.reconstruction_threshold:.4f}")

        # Train One-Class SVM
        self.svm = OneClassSVM(
            nu=self.config.svm_nu,
            gamma=self.config.svm_gamma,
            kernel="rbf",
        )
        self.svm.fit(X_scaled)
        print(f"[Advanced Detector] One-Class SVM trained.")

        # Train Isolation Forest (backup)
        self.isolation_forest = IsolationForest(
            contamination=self.config.if_contamination,
            n_estimators=self.config.if_n_estimators,
            random_state=self.config.random_state,
        )
        self.isolation_forest.fit(X_scaled)
        print(f"[Advanced Detector] Isolation Forest trained.")

        self._is_fitted = True

    def _engineer_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Add derived features for better detection."""

        X = X.copy()

        # Normalize status codes (map to 0-1 range)
        if "status_code" in X.columns:
            # Map: 2xx -> 0.0, 4xx -> 0.5, 5xx -> 1.0
            X["status_code_normalized"] = X["status_code"].apply(
                lambda x: 0.0 if 200 <= x < 300 else (0.5 if 400 <= x < 500 else 1.0)
            )

        # Request rate per payload (efficiency metric)
        if "requests_per_minute" in X.columns and "avg_payload_bytes" in X.columns:
            X["req_per_byte"] = X["requests_per_minute"] / (X["avg_payload_bytes"] + 1)

        # Response time per request (latency efficiency)
        if "avg_response_time_ms" in X.columns and "requests_per_minute" in X.columns:
            X["ms_per_request"] = X["avg_response_time_ms"] / (X["requests_per_minute"] + 1)

        # Error rate severity (combine error rate and status codes)
        if "error_rate_pct" in X.columns and "status_code_normalized" in X.columns:
            X["error_severity"] = X["error_rate_pct"] * (1 + X["status_code_normalized"])

        return X

    def _train_autoencoder(self, X_scaled: pd.DataFrame) -> TrafficAutoencoder:
        """Train the autoencoder neural network."""

        if not TORCH_AVAILABLE or TrafficAutoencoder is None:
            raise RuntimeError("PyTorch not available. Cannot train autoencoder.")

        input_dim = X_scaled.shape[1]
        model = TrafficAutoencoder(
            input_dim=input_dim,
            encoding_dim=self.config.encoding_dim,
            hidden_dims=self.config.hidden_dims,
        )

        optimizer = torch.optim.Adam(model.parameters(), lr=self.config.autoencoder_lr)
        criterion = nn.MSELoss()

        X_tensor = torch.FloatTensor(X_scaled.values)
        dataset = torch.utils.data.TensorDataset(X_tensor)
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=self.config.autoencoder_batch_size, shuffle=True
        )

        model.train()
        for epoch in range(self.config.autoencoder_epochs):
            total_loss = 0.0
            for batch in dataloader:
                x = batch[0]
                optimizer.zero_grad()
                reconstructed = model(x)
                loss = criterion(reconstructed, x)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            if (epoch + 1) % 20 == 0:
                avg_loss = total_loss / len(dataloader)
                print(f"  Epoch {epoch + 1}/{self.config.autoencoder_epochs}, Loss: {avg_loss:.6f}")

        model.eval()
        return model

    def _get_reconstructions(self, X_scaled: pd.DataFrame) -> np.ndarray:
        """Get reconstructions from autoencoder."""

        if self.autoencoder is None or not TORCH_AVAILABLE:
            raise RuntimeError("Autoencoder not trained or PyTorch not available")

        self.autoencoder.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_scaled.values)
            reconstructions = self.autoencoder(X_tensor).numpy()
        return reconstructions

    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomalies using ensemble voting."""

        self._ensure_fitted()

        feature_cols = list(self.config.feature_columns)
        X = data[feature_cols].copy()
        X = self._engineer_features(X)
        X_scaled = self.scaler.transform(X)
        X_scaled_df = pd.DataFrame(X_scaled, columns=X.columns)

        predictions = []

        # Autoencoder prediction
        if self.autoencoder is not None:
            reconstructions = self._get_reconstructions(X_scaled_df)
            reconstruction_errors = np.mean((X_scaled - reconstructions) ** 2, axis=1)
            ae_predictions = (reconstruction_errors > self.reconstruction_threshold).astype(int) * -1 + 1
            predictions.append(ae_predictions)

        # One-Class SVM prediction
        if self.svm is not None:
            svm_pred = self.svm.predict(X_scaled)
            predictions.append(svm_pred)

        # Isolation Forest prediction
        if self.isolation_forest is not None:
            if_pred = self.isolation_forest.predict(X_scaled)
            predictions.append(if_pred)

        # Ensemble voting: anomaly if majority vote
        if len(predictions) > 0:
            predictions_array = np.array(predictions)
            # Count anomalies (-1) per sample
            anomaly_votes = np.sum(predictions_array == -1, axis=0)
            # Need at least threshold number of models to agree
            ensemble_pred = np.where(
                anomaly_votes >= self.config.ensemble_vote_threshold, -1, 1
            )
        else:
            raise RuntimeError("No models available for prediction")

        return ensemble_pred

    def anomaly_scores(self, data: pd.DataFrame) -> np.ndarray:
        """Return anomaly scores (lower = more anomalous)."""

        self._ensure_fitted()

        feature_cols = list(self.config.feature_columns)
        X = data[feature_cols].copy()
        X = self._engineer_features(X)
        X_scaled = self.scaler.transform(X)
        X_scaled_df = pd.DataFrame(X_scaled, columns=X.columns)

        scores = []

        # Autoencoder score (reconstruction error, negated so lower = more anomalous)
        if self.autoencoder is not None:
            reconstructions = self._get_reconstructions(X_scaled_df)
            reconstruction_errors = np.mean((X_scaled - reconstructions) ** 2, axis=1)
            # Normalize and negate
            ae_scores = -reconstruction_errors / (self.reconstruction_threshold + 1e-6)
            scores.append(ae_scores)

        # One-Class SVM decision function
        if self.svm is not None:
            svm_scores = self.svm.decision_function(X_scaled)
            scores.append(svm_scores)

        # Isolation Forest decision function
        if self.isolation_forest is not None:
            if_scores = self.isolation_forest.decision_function(X_scaled)
            scores.append(if_scores)

        # Average scores
        if len(scores) > 0:
            return np.mean(scores, axis=0)
        else:
            raise RuntimeError("No models available for scoring")

    def detect_single(self, request_metrics: Dict[str, float]) -> str:
        """Classify a single request as SAFE or SUSPICIOUS."""

        self._ensure_fitted()
        features = pd.DataFrame([request_metrics], columns=self.config.feature_columns)
        prediction = self.predict(features)[0]
        return "SAFE" if prediction == 1 else "SUSPICIOUS"

    def _ensure_fitted(self) -> None:
        """Ensure model is fitted before prediction."""

        if not self._is_fitted:
            raise RuntimeError("Model not fitted. Call `fit` first.")


# ----------------------------------------------------------------------------------
# Integration with existing detector interface
# ----------------------------------------------------------------------------------
def create_advanced_detector(
    normal_data: pd.DataFrame,
    config: AdvancedModelConfig | None = None,
) -> AdvancedAnomalyDetector:
    """Create and train an advanced detector."""

    if config is None:
        config = AdvancedModelConfig()

    detector = AdvancedAnomalyDetector(config)
    detector.fit(normal_data)
    return detector

