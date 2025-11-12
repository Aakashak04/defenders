#!/usr/bin/env python3
"""
Standalone training script for the anomaly detection model.
Run this before starting the defender to pre-train the model.

Uses the advanced ensemble model (Autoencoder + One-Class SVM + Isolation Forest)
if PyTorch is available, otherwise falls back to basic Isolation Forest.
"""
import sys
import os

# Add parent directory to path so we can import the detector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anomaly_detection.bank_traffic_anomaly_detector import (
    initialize_advanced_detector,
    initialize_detector,
    ADVANCED_DETECTOR_AVAILABLE,
    TORCH_AVAILABLE,
)

if __name__ == "__main__":
    print("=" * 80)
    
    # Try to use advanced model first
    if ADVANCED_DETECTOR_AVAILABLE:
        print("Training Advanced Ensemble Anomaly Detection Model")
        print("(Autoencoder + One-Class SVM + Isolation Forest)")
        if TORCH_AVAILABLE:
            print("✓ PyTorch available - Full ensemble will be used")
        else:
            print("⚠ PyTorch not available - Using One-Class SVM + Isolation Forest")
        print("=" * 80)
        
        try:
            detector, metrics = initialize_advanced_detector(show_plot=False, verbose=True)
            model_type = "Advanced Ensemble"
        except Exception as e:
            print(f"\n⚠ Advanced model failed: {e}")
            print("Falling back to basic Isolation Forest...")
            detector, metrics = initialize_detector(show_plot=False, verbose=True)
            model_type = "Isolation Forest (Fallback)"
    else:
        print("Training Isolation Forest Anomaly Detection Model")
        print("=" * 80)
        detector, metrics = initialize_detector(show_plot=False, verbose=True)
        model_type = "Isolation Forest"
    
    print("\n" + "=" * 80)
    print("✅ Training Complete!")
    print("=" * 80)
    print(f"Model Type: {model_type}")
    print(f"Total attack samples: {metrics['detected_attacks'] + metrics['missed_attacks']}")
    print(f"Detected attacks: {metrics['detected_attacks']}")
    print(f"Missed attacks: {metrics['missed_attacks']}")
    print(f"False alarms: {metrics['false_alarms']}")
    
    if metrics['false_alarms'] > 0:
        fpr = (metrics['false_alarms'] / 800) * 100  # Assuming 800 normal samples
        print(f"False positive rate: {fpr:.2f}%")
    
    print("\nThe model is now ready to use in the defender.")
    print("Start the defender stack with: docker compose up --build")
    print("=" * 80)

