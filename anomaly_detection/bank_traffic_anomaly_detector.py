"""
Bank traffic anomaly detection using Isolation Forest.

This script simulates normal and attack traffic patterns, trains an Isolation Forest
model to learn healthy behavior, and highlights anomalies in the combined dataset.

The layout and helper utilities are designed to be production-ready and easily
extendable into an API layer (e.g., Flask or FastAPI) with minimal changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

try:
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover - optional dependency for headless environments
    plt = None
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# Try to import advanced detector (optional dependency)
try:
    from .advanced_detector import (
        AdvancedAnomalyDetector,
        AdvancedModelConfig,
        create_advanced_detector,
        TORCH_AVAILABLE,
    )
    ADVANCED_DETECTOR_AVAILABLE = True
except (ImportError, ValueError):
    try:
        from advanced_detector import (
            AdvancedAnomalyDetector,
            AdvancedModelConfig,
            create_advanced_detector,
            TORCH_AVAILABLE,
        )
        ADVANCED_DETECTOR_AVAILABLE = True
    except ImportError:
        ADVANCED_DETECTOR_AVAILABLE = False
        TORCH_AVAILABLE = False


# --------------------------------------------------------------------------------------
# Configuration dataclasses keep hyperparameters and feature definitions grouped
# together, simplifying reuse from other modules or API layers.
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class SimulationConfig:
    """Configuration values governing synthetic traffic generation."""

    normal_samples: int = 800
    attack_samples: int = 120
    random_state: int = 42


@dataclass(frozen=True)
class ModelConfig:
    """Configuration values for the Isolation Forest model."""

    contamination: float = 0.15  # Expected fraction of anomalies in evaluation data
    random_state: int = 42
    n_estimators: int = 200
    max_samples: str | int = "auto"

    feature_columns: Tuple[str, ...] = (
        "requests_per_minute",
        "avg_payload_bytes",
        "avg_response_time_ms",
        "error_rate_pct",
        "status_code",
    )


# --------------------------------------------------------------------------------------
# Data generation utilities mimic realistic server telemetry with intuitive ranges.
# --------------------------------------------------------------------------------------
def generate_normal_traffic(config: SimulationConfig) -> pd.DataFrame:
    """
    Create a DataFrame representing healthy bank server traffic.

    The random distributions reflect stable request throughput, modest payload size,
    fast response times, low error rates, and mostly HTTP 200-level responses.
    """

    rng = np.random.default_rng(config.random_state)

    normal_data = pd.DataFrame(
        {
            "requests_per_minute": rng.normal(loc=180, scale=25, size=config.normal_samples).clip(min=60),
            "avg_payload_bytes": rng.normal(loc=3500, scale=600, size=config.normal_samples).clip(min=500),
            "avg_response_time_ms": rng.normal(loc=120, scale=20, size=config.normal_samples).clip(min=40),
            "error_rate_pct": rng.normal(loc=0.5, scale=0.2, size=config.normal_samples).clip(min=0),
            "status_code": rng.choice([200, 201, 202, 204], size=config.normal_samples, p=[0.5, 0.2, 0.2, 0.1]),
        }
    )

    normal_data["label"] = "normal"
    return normal_data


def generate_attack_traffic(config: SimulationConfig) -> pd.DataFrame:
    """
    Create a DataFrame representing malicious traffic bursts.

    We intentionally push each metric toward suspicious extremes: high request rates,
    large payloads, slow responses, elevated error rates, and 5xx status codes.
    """

    rng = np.random.default_rng(config.random_state + 1)

    attack_data = pd.DataFrame(
        {
            "requests_per_minute": rng.normal(loc=420, scale=60, size=config.attack_samples).clip(min=180),
            "avg_payload_bytes": rng.normal(loc=9000, scale=1500, size=config.attack_samples).clip(min=3000),
            "avg_response_time_ms": rng.normal(loc=480, scale=80, size=config.attack_samples).clip(min=160),
            "error_rate_pct": rng.normal(loc=6.0, scale=1.5, size=config.attack_samples).clip(min=1.0),
            "status_code": rng.choice([400, 401, 403, 429, 500, 502, 503, 504], size=config.attack_samples),
        }
    )

    attack_data["label"] = "attack"
    return attack_data


def combine_datasets(
    normal_df: pd.DataFrame,
    attack_df: pd.DataFrame,
    *,
    random_state: int,
) -> pd.DataFrame:
    """
    Concatenate normal and attack traffic into a single, shuffled dataset.

    The combined DataFrame contains both labeled samples for offline evaluation.
    """

    combined = pd.concat([normal_df, attack_df], ignore_index=True)
    return combined.sample(frac=1.0, random_state=random_state).reset_index(drop=True)


# --------------------------------------------------------------------------------------
# The core detector object wraps the Isolation Forest instantiation, training, and use.
# --------------------------------------------------------------------------------------
class BankTrafficAnomalyDetector:
    """Encapsulates Isolation Forest workflow for bank server traffic."""

    def __init__(self, model_config: ModelConfig) -> None:
        self.model_config = model_config
        self.model = IsolationForest(
            n_estimators=model_config.n_estimators,
            contamination=model_config.contamination,
            max_samples=model_config.max_samples,
            random_state=model_config.random_state,
        )
        self._is_fitted = False

    def fit(self, training_data: pd.DataFrame) -> None:
        """Fit the Isolation Forest on known-good traffic samples."""

        self.model.fit(training_data[list(self.model_config.feature_columns)])
        self._is_fitted = True

    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomalies (-1) and normal points (1) for the supplied dataset."""

        self._ensure_fitted()
        return self.model.predict(data[list(self.model_config.feature_columns)])

    def anomaly_scores(self, data: pd.DataFrame) -> np.ndarray:
        """Return anomaly scores (the lower, the more anomalous)."""




        self._ensure_fitted()
        return self.model.decision_function(data[list(self.model_config.feature_columns)])

    def detect_single(self, request_metrics: Dict[str, float]) -> str:
        """
        Inspect a single request represented as a dictionary of metrics.

        Returns "SAFE" for inliers and "SUSPICIOUS" for anomalies.
        """

        self._ensure_fitted()
        features = pd.DataFrame([request_metrics], columns=self.model_config.feature_columns)
        prediction = self.model.predict(features)[0]
        return "SAFE" if prediction == 1 else "SUSPICIOUS"

    def _ensure_fitted(self) -> None:
        """Fail fast when predictions are requested before training completes."""

        if not self._is_fitted:
            raise RuntimeError("Isolation Forest model is not fitted yet. Call `fit` first.")


# --------------------------------------------------------------------------------------
# Helper functions supporting evaluation, plotting, and API-ready detection wrappers.
# --------------------------------------------------------------------------------------
def evaluate_predictions(predictions: np.ndarray, labels: pd.Series) -> Dict[str, int]:
    """
    Compute core evaluation metrics describing detector accuracy on labeled data.

    Returns a dictionary with counts for detected attacks, missed attacks, and false alarms.
    """

    label_array = labels.to_numpy()
    detected_attacks = int(((predictions == -1) & (label_array == "attack")).sum())
    missed_attacks = int(((predictions == 1) & (label_array == "attack")).sum())
    false_alarms = int(((predictions == -1) & (label_array == "normal")).sum())

    return {
        "detected_attacks": detected_attacks,
        "missed_attacks": missed_attacks,
        "false_alarms": false_alarms,
    }


def plot_anomalies(
    dataset: pd.DataFrame,
    predictions: np.ndarray,
    figsize: Tuple[int, int] = (10, 6),
) -> None:
    """
    Visualize anomalies via a scatter plot.

    Requests per minute are plotted on the x-axis and response time on the y-axis.
    Normal points appear blue, while anomalies are highlighted in red.
    """

    if plt is None:
        raise RuntimeError("matplotlib is required for plotting but is not installed.")

    plt.figure(figsize=figsize)
    normal_mask = predictions == 1
    anomaly_mask = ~normal_mask

    plt.scatter(
        dataset.loc[normal_mask, "requests_per_minute"],
        dataset.loc[normal_mask, "avg_response_time_ms"],
        c="tab:blue",
        alpha=0.5,
        label="Normal",
    )
    plt.scatter(
        dataset.loc[anomaly_mask, "requests_per_minute"],
        dataset.loc[anomaly_mask, "avg_response_time_ms"],
        c="red",
        alpha=0.85,
        label="Anomaly",
        marker="x",
    )

    plt.title("Bank Server Traffic Anomalies (Isolation Forest)")
    plt.xlabel("Requests per Minute")
    plt.ylabel("Average Response Time (ms)")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    plt.show()


# --------------------------------------------------------------------------------------
# Global detector instance & lightweight helper for downstream integrations.
# --------------------------------------------------------------------------------------
DETECTOR: BankTrafficAnomalyDetector | AdvancedAnomalyDetector | None = None


def detect_request(request_metrics: Dict[str, float]) -> str:
    """
    Lightweight helper to classify a single request dictionary.

    This wrapper enables easy reuse from other modules or an HTTP controller.
    """

    if DETECTOR is None:
        raise RuntimeError("Global detector is not initialized. Run the main training pipeline first.")

    return DETECTOR.detect_single(request_metrics)


def get_anomaly_score(request_metrics: Dict[str, float]) -> float:
    """
    Return the anomaly score for a request (lower = more anomalous).
    
    Returns a float where negative values indicate anomalies.
    Typical range: -0.5 (highly anomalous) to 0.5 (very normal).
    """

    if DETECTOR is None:
        raise RuntimeError("Global detector is not initialized. Run the main training pipeline first.")

    # Handle both detector types
    if isinstance(DETECTOR, AdvancedAnomalyDetector):
        features = pd.DataFrame([request_metrics], columns=DETECTOR.config.feature_columns)
    else:
        features = pd.DataFrame([request_metrics], columns=DETECTOR.model_config.feature_columns)
    
    score = DETECTOR.anomaly_scores(features)[0]
    return float(score)


def initialize_detector(
    simulation_config: SimulationConfig | None = None,
    model_config: ModelConfig | None = None,
    *,
    show_plot: bool = False,
    verbose: bool = True,
) -> Tuple[BankTrafficAnomalyDetector, Dict[str, int]]:
    """
    Train and persist the global Isolation Forest detector using synthetic data.

    Returns a tuple of the fitted detector and evaluation metrics for convenience.
    """

    simulation_config = simulation_config or SimulationConfig()
    model_config = model_config or ModelConfig()

    normal_df = generate_normal_traffic(simulation_config)
    attack_df = generate_attack_traffic(simulation_config)
    combined_df = combine_datasets(normal_df, attack_df, random_state=simulation_config.random_state)

    feature_columns = list(model_config.feature_columns)
    detector = BankTrafficAnomalyDetector(model_config)
    detector.fit(normal_df[feature_columns])

    predictions = detector.predict(combined_df[feature_columns])
    metrics = evaluate_predictions(predictions, combined_df["label"])

    global DETECTOR
    DETECTOR = detector

    if verbose:
        print("=== Isolation Forest Anomaly Detection Summary ===")
        print(f"Total samples analysed : {len(combined_df)}")
        print(f"Total detected attacks : {metrics['detected_attacks']}")
        print(f"Missed attacks         : {metrics['missed_attacks']}")
        print(f"False alarms           : {metrics['false_alarms']}")

    if show_plot:
        if plt is None and verbose:
            print("matplotlib not available; skipping anomaly scatter plot.")
        elif plt is not None:
            plot_anomalies(combined_df, predictions)

    return detector, metrics


def initialize_advanced_detector(
    simulation_config: SimulationConfig | None = None,
    advanced_config: AdvancedModelConfig | None = None,
    *,
    show_plot: bool = False,
    verbose: bool = True,
) -> Tuple[AdvancedAnomalyDetector, Dict[str, int]]:
    """
    Train and persist the advanced ensemble detector using synthetic data.
    
    This uses Autoencoder + One-Class SVM + Isolation Forest ensemble for superior accuracy.
    Requires PyTorch for full functionality (falls back to SVM + IF if unavailable).
    
    Returns a tuple of the fitted detector and evaluation metrics.
    """

    if not ADVANCED_DETECTOR_AVAILABLE:
        raise RuntimeError(
            "Advanced detector not available. Install PyTorch for full functionality, "
            "or use initialize_detector() for basic Isolation Forest."
        )

    simulation_config = simulation_config or SimulationConfig()
    advanced_config = advanced_config or AdvancedModelConfig()

    normal_df = generate_normal_traffic(simulation_config)
    attack_df = generate_attack_traffic(simulation_config)
    combined_df = combine_datasets(normal_df, attack_df, random_state=simulation_config.random_state)

    feature_columns = list(advanced_config.feature_columns)
    
    if verbose:
        print("=== Training Advanced Ensemble Detector ===")
        if TORCH_AVAILABLE:
            print("✓ PyTorch available - Using Autoencoder + One-Class SVM + Isolation Forest")
        else:
            print("⚠ PyTorch not available - Using One-Class SVM + Isolation Forest only")
    
    detector = create_advanced_detector(normal_df[feature_columns], advanced_config)

    predictions = detector.predict(combined_df[feature_columns])
    metrics = evaluate_predictions(predictions, combined_df["label"])

    global DETECTOR
    DETECTOR = detector

    if verbose:
        print("\n=== Advanced Ensemble Anomaly Detection Summary ===")
        print(f"Total samples analysed : {len(combined_df)}")
        print(f"Total detected attacks : {metrics['detected_attacks']}")
        print(f"Missed attacks         : {metrics['missed_attacks']}")
        print(f"False alarms           : {metrics['false_alarms']}")
        if metrics['false_alarms'] > 0:
            fpr = (metrics['false_alarms'] / len(normal_df)) * 100
            print(f"False positive rate     : {fpr:.2f}%")

    if show_plot:
        if plt is None and verbose:
            print("matplotlib not available; skipping anomaly scatter plot.")
        elif plt is not None:
            plot_anomalies(combined_df, predictions)

    return detector, metrics


def get_detector() -> BankTrafficAnomalyDetector | AdvancedAnomalyDetector:
    """Return the globally initialised detector or raise if unavailable."""

    if DETECTOR is None:
        raise RuntimeError("Global detector is not initialized. Call `initialize_detector` first.")
    return DETECTOR


# --------------------------------------------------------------------------------------
# Main execution flow ties everything together for a full training & evaluation cycle.
# --------------------------------------------------------------------------------------
def main() -> None:
    """Orchestrate dataset simulation, model training, evaluation, and visualization."""

    detector, _ = initialize_detector(show_plot=True, verbose=True)

    # Display a quick sample prediction using the helper for demonstration purposes.
    sample_request = {
        "requests_per_minute": 500,
        "avg_payload_bytes": 9500,
        "avg_response_time_ms": 520,
        "error_rate_pct": 5.5,
        "status_code": 503,
    }
    print("\nSample request classification:", detect_request(sample_request))


if __name__ == "__main__":
    main()

