"""
Configuration for AegisMAS-2Agent
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    # API Configuration
    API_HOST: str = os.getenv("AEGIS_API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("AEGIS_API_PORT", "8080"))
    
    # Origin Bank
    ORIGIN_URL: str = os.getenv("AEGIS_ORIGIN_URL", "http://host.docker.internal:8000")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Database
    EVENTS_DB_PATH: str = os.getenv("EVENTS_DB_PATH", "events.db")
    
    # Models
    MODELS_DIR: str = os.getenv("MODELS_DIR", "models")
    LSTM_MODEL_PATH: str = os.getenv("LSTM_MODEL_PATH", "models/lstm_model.pt")
    STATS_MODEL_PATH: str = os.getenv("STATS_MODEL_PATH", "models/stats_model.pkl")
    
    # Agent Configuration
    SIGNATURE_WEIGHT: float = 0.5
    STATS_WEIGHT: float = 0.35
    LSTM_WEIGHT: float = 0.15
    
    # Decision Thresholds
    BLOCK_THRESHOLD: float = 0.7
    CHALLENGE_THRESHOLD: float = 0.5
    
    # LSTM Configuration
    LSTM_HIDDEN_SIZE: int = 64
    LSTM_NUM_LAYERS: int = 2
    LSTM_SEQ_LENGTH: int = 20
    LSTM_FEATURE_DIM: int = 8  # path_hash, method, body_len, nonalpha_ratio, hour, rps, etc.
    
    # Statistical Agent
    STATS_CONTAMINATION: float = 0.1  # IsolationForest contamination
    
    # Request Body
    MAX_BODY_SAMPLE: int = 2048
    
    # Envoy Failure Mode
    FAILURE_MODE_ALLOW: bool = os.getenv("FAILURE_MODE_ALLOW", "true").lower() == "true"
    
    # Training
    TRAINING_DATA_DIR: str = os.getenv("TRAINING_DATA_DIR", "training_data")
    
    # Sanitization
    SANITIZE_EMAILS: bool = True
    SANITIZE_TOKENS: bool = True
    SANITIZE_NUMBERS: bool = True


config = Config()

