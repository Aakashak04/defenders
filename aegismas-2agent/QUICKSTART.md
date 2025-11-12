# AegisMAS-2Agent Quick Start Guide

## 🚀 Complete Command Reference

### Step 1: Generate Training Data

```powershell
# Navigate to project directory
cd aegismas-2agent

# Generate synthetic training data
python scripts/gen_synthetic.py
```

**Expected Output:**
```
Generated 500 benign and 200 malicious samples
Saved to training_data/synthetic_dataset.json
Also saved to training_data/synthetic_dataset.csv
```

---

### Step 2: Train the LSTM Model

```powershell
# Train LSTM Autoencoder (this will take a few minutes)
python scripts/train_lstm.py --epochs 5 --batch-size 32
```

**Options:**
- `--epochs`: Number of training epochs (default: 3, recommended: 5-10)
- `--batch-size`: Batch size (default: 32)
- `--lr`: Learning rate (default: 0.001)

**Expected Output:**
```
Loaded 700 samples
Using 500 benign samples for training
Training on cpu...
Epoch 1/5, Loss: 0.023456
Epoch 2/5, Loss: 0.012345
...
Saved model to models/lstm_model.pt
```

---

### Step 3: Train the Statistical Model (Optional)

If you want to train the IsolationForest model with custom data:

```python
# Run in Python
python
```

```python
from aegismas_api.agents.stats_agent import StatsAgent
from aegismas_api.utils import extract_features
import json
import numpy as np

# Load training data
with open("training_data/synthetic_dataset.json", "r") as f:
    samples = json.load(f)

# Extract features
X_train = []
for sample in samples:
    features = extract_features(
        method=sample["method"],
        path=sample["path"],
        body_sample=sample.get("body_sample", ""),
        query=sample.get("query", ""),
    )
    X_train.append(features)

X_train = np.array(X_train)

# Train model
agent = StatsAgent()
agent.fit(X_train)
agent.save_model()

print("Statistical model trained and saved!")
```

**Note:** The system works in bootstrap mode without training, but training improves accuracy.

---

### Step 4: Start the Defender

```powershell
# Start all services (Envoy, AegisMAS API, Redis)
docker compose up
```

**Or run in detached mode:**
```powershell
docker compose up -d
```

**Services:**
- **Envoy Gateway**: `http://localhost:8085` (entry point)
- **AegisMAS API**: `http://localhost:8080` (decision engine)
- **Redis**: Internal (for rate limiting and sequences)

**Verify it's running:**
```powershell
# Check health
curl http://localhost:8080/health

# Or in PowerShell
Invoke-WebRequest -Uri "http://localhost:8080/health"
```

**Expected Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-11-12T...",
  "redis": "connected"
}
```

---

### Step 5: Test with Defender OFF

```powershell
# Stop the defender
docker compose down

# Run attack simulator directly against bank
python attack_simulator.py --defender off
```

**Expected:** Most/all attacks reach your bank at `localhost:8000` (you should see many "✅ ALLOWED" responses)

---

### Step 6: Test with Defender ON

```powershell
# Start the defender
docker compose up -d

# Wait a few seconds for services to start, then run attacks
python attack_simulator.py --defender on
```

**Expected:** Many attacks should be blocked (you should see "🛑 BLOCKED" responses with 403/429 status codes)

**With detailed output:**
```powershell
python attack_simulator.py --defender on
```

**Quiet mode (summary only):**
```powershell
python attack_simulator.py --defender on --quiet
```

---

### Step 7: View Blocked Events

```powershell
# View all recent events
curl http://localhost:8080/v1/events

# View only blocked events
curl "http://localhost:8080/v1/events?decision=block"

# View events from specific IP
curl "http://localhost:8080/v1/events?ip=192.168.1.100"

# View with pagination
curl "http://localhost:8080/v1/events?limit=50&offset=0"
```

**PowerShell alternative:**
```powershell
# View all events
$response = Invoke-WebRequest -Uri "http://localhost:8080/v1/events"
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10

# View blocked events only
$response = Invoke-WebRequest -Uri "http://localhost:8080/v1/events?decision=block"
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

---

### Step 8: View Metrics

```powershell
# Get system metrics
curl http://localhost:8080/metrics
```

**Expected Response:**
```json
{
  "total_events": 150,
  "blocked": 45,
  "allowed": 100,
  "challenge": 5,
  "block_rate": 0.3
}
```

---

## 📋 Complete Workflow Example

```powershell
# 1. Navigate to project
cd aegismas-2agent

# 2. Generate training data
python scripts/gen_synthetic.py

# 3. Train LSTM model
python scripts/train_lstm.py --epochs 5

# 4. Start defender
docker compose up -d

# 5. Wait for services to be ready (5-10 seconds)
Start-Sleep -Seconds 10

# 6. Test with defender ON
python attack_simulator.py --defender on

# 7. View blocked events
curl "http://localhost:8080/v1/events?decision=block"

# 8. View metrics
curl http://localhost:8080/metrics

# 9. Stop defender when done
docker compose down
```

---

## 🔧 Troubleshooting Commands

### Check if services are running:
```powershell
docker compose ps
```

### View logs:
```powershell
# All services
docker compose logs

# Just AegisMAS API
docker compose logs aegismas-api

# Just Envoy
docker compose logs envoy

# Follow logs in real-time
docker compose logs -f
```

### Restart services:
```powershell
docker compose restart
```

### Rebuild and restart:
```powershell
docker compose up --build -d
```

### Check if bank is accessible:
```powershell
curl http://localhost:8000/health
```

### Test Envoy directly:
```powershell
curl http://localhost:8085/health
```

---

## 🎯 Expected Results

### Defender OFF:
- **Total Attacks**: ~74
- **Allowed**: ~60-70 (80-95%)
- **Blocked**: 0-5 (0-7%)
- **Errors**: 0-10 (0-13%)

### Defender ON:
- **Total Attacks**: ~74
- **Allowed**: ~20-30 (30-40%)
- **Blocked**: ~40-50 (55-70%)
- **Errors**: 0-5 (0-7%)

The defender should block:
- ✅ SQL injection attacks (signature agent)
- ✅ Path traversal attempts (signature agent)
- ✅ Rapid fire requests (rate limiting + anomaly detection)
- ✅ Suspicious patterns (LSTM + Statistical agents)

---

## 📝 Notes

1. **First Run**: Models will run in "bootstrap mode" (conservative scoring) until trained
2. **Training Time**: LSTM training takes 2-5 minutes on CPU
3. **Bank Required**: Make sure your bank is running at `http://localhost:8000` before testing
4. **Windows**: Use `host.docker.internal` to access host's localhost from Docker (already configured)
5. **Linux**: If `host.docker.internal` doesn't work, use `172.17.0.1:8000` or run API outside Docker

---

## 🚨 Quick Commands Cheat Sheet

```powershell
# TRAINING
python scripts/gen_synthetic.py                    # Generate data
python scripts/train_lstm.py --epochs 5            # Train LSTM

# DEFENDER
docker compose up -d                               # Start defender
docker compose down                                # Stop defender
docker compose logs -f                             # View logs

# TESTING
python attack_simulator.py --defender off          # Test without defender
python attack_simulator.py --defender on          # Test with defender
python attack_simulator.py --defender on --quiet  # Quiet mode

# MONITORING
curl http://localhost:8080/health                  # Health check
curl http://localhost:8080/metrics                 # Metrics
curl "http://localhost:8080/v1/events?decision=block"  # Blocked events
```

---

**Ready to protect your bank! 🛡️**

