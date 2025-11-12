# AegisMAS-2Agent — Lightweight 2-Agent Inline Defender

A minimal, defensive-only security gateway that sits inline (via Envoy) and protects an existing bank running at `http://localhost:8000`. The Defender exposes a Decision API that Envoy calls for each request.

## Architecture

```
Client → Envoy (port 8085) → AegisMAS Decision API → allow/block → Forward to Bank (localhost:8000) → Response
```

## Features

- **2-Agent System:**
  - **LSTM Agent**: PyTorch-based LSTM Autoencoder for sequence anomaly detection
  - **Statistical Agent**: IsolationForest (scikit-learn) for quick unsupervised scoring
  - **Signature Agent**: Fast regex-based pattern matching (SQLi, path traversal, XSS, RCE)

- **Decision Logic**: Weighted combination of agents with hard signature rules first
- **Event Logging**: SQLite database with PII sanitization
- **Training Support**: Synthetic data generation and model training scripts

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Bank running at `http://localhost:8000`

### 1. Start the Defender

```bash
cd aegismas-2agent
docker compose up --build
```

This starts:
- **Envoy** on port `8085` (gateway)
- **AegisMAS API** on port `8080` (decision engine)
- **Redis** (for rate limiting and sequence buffers)

### 2. Test with Defender OFF

Stop the defender and run the attack simulator directly against your bank:

```bash
# Stop defender
docker compose down

# Run attack simulator
python attack_simulator.py --defender off
```

Expected: Most/all attacks reach your bank directly.

### 3. Test with Defender ON

Start the defender and run attacks through the gateway:

```bash
# Start defender
docker compose up

# Run attack simulator
python attack_simulator.py --defender on
```

Expected: Many attacks should be blocked (403/429) by the defender.

### 4. View Blocked Events

```bash
# View recent events
curl http://localhost:8080/v1/events

# View only blocked events
curl "http://localhost:8080/v1/events?decision=block"

# View events from specific IP
curl "http://localhost:8080/v1/events?ip=192.168.1.100"
```

## Running Locally (Without Docker)

If you prefer to run `aegismas-api` outside Docker:

```bash
cd aegismas-2agent/aegismas_api

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export REDIS_URL=redis://localhost:6379/0
export AEGIS_ORIGIN_URL=http://localhost:8000
export EVENTS_DB_PATH=events.db

# Run API
python -m aegismas_api
```

Then update `docker-compose.yml` to remove `aegismas-api` service, or run Envoy separately pointing to `localhost:8080`.

## Training Models

### Generate Synthetic Data

```bash
cd aegismas-2agent
python scripts/gen_synthetic.py
```

This creates `training_data/synthetic_dataset.json` with benign and malicious samples.

### Train LSTM Model

```bash
python scripts/train_lstm.py --epochs 5 --batch-size 32
```

This trains the LSTM autoencoder and saves to `aegismas_api/models/lstm_model.pt`.

### Train Statistical Model

```python
# In Python
from aegismas_api.agents.stats_agent import StatsAgent
import numpy as np

# Load your training data
# ... extract features ...

agent = StatsAgent()
agent.fit(X_train)  # X_train is numpy array of feature vectors
agent.save_model()
```

## API Endpoints

### Decision API

**POST** `/v1/decide`

Called by Envoy for each request. Returns:
- `action`: `"allow"` | `"block"` | `"challenge"`
- `reason`: Explanation string
- `signals`: Agent signals and scores
- `origin`: Origin URL to forward to

### Events API

**GET** `/v1/events`

Query parameters:
- `limit`: Number of events (default: 100)
- `offset`: Pagination offset (default: 0)
- `ip`: Filter by IP address
- `decision`: Filter by decision (`allow`, `block`, `challenge`)

### Feedback API

**POST** `/v1/feedback`

Provide labels for training:
```json
{
  "event_id": 123,
  "malicious": true
}
```

### Training API

**POST** `/v1/train`

Trigger training job (admin only in PoC):
```json
{
  "epochs": 3
}
```

### Health & Metrics

- **GET** `/health` - Health check
- **GET** `/metrics` - System metrics (total events, block rate, etc.)

## Configuration

Environment variables (set in `docker-compose.yml` or `.env`):

- `REDIS_URL`: Redis connection string
- `AEGIS_ORIGIN_URL`: Bank origin URL (default: `http://host.docker.internal:8000`)
- `EVENTS_DB_PATH`: SQLite database path
- `MODELS_DIR`: Directory for model checkpoints
- `FAILURE_MODE_ALLOW`: Allow traffic on defender failure (default: `true`)

## Decision Logic

1. **Signature Agent** (weight: 0.5): Fast regex checks. If match → immediate block.
2. **Statistical Agent** (weight: 0.35): IsolationForest anomaly score.
3. **LSTM Agent** (weight: 0.15): Sequence-based anomaly detection.

**Combined Score:**
- `>= 0.7` → **BLOCK** (403)
- `0.5 - 0.7` → **CHALLENGE** (429)
- `< 0.5` → **ALLOW** (200)

## Project Structure

```
aegismas-2agent/
├── gateway/
│   └── envoy.yaml              # Envoy configuration
├── aegismas_api/
│   ├── agents/
│   │   ├── signature_agent.py  # Regex-based detection
│   │   ├── stats_agent.py      # IsolationForest
│   │   └── lstm_agent.py       # LSTM Autoencoder
│   ├── coordinator.py          # Decision coordinator
│   ├── events_db.py            # SQLite event storage
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration
│   ├── utils.py                # Utilities (sanitization, features)
│   ├── models/                 # Model checkpoints
│   └── events.db              # SQLite database
├── scripts/
│   ├── gen_synthetic.py        # Generate training data
│   └── train_lstm.py          # Train LSTM model
├── docker-compose.yml          # Docker services
├── attack_simulator.py         # Attack testing script
└── README.md                   # This file
```

## Verification Commands

### Defender OFF

```powershell
# Windows PowerShell
docker compose down
python attack_simulator.py --defender off
```

Expected: Bank receives attack traffic.

### Defender ON

```powershell
# Windows PowerShell
docker compose up --build
python attack_simulator.py --defender on
```

Expected: Many requests blocked.

### View Events

```powershell
# PowerShell
Invoke-WebRequest -Uri "http://localhost:8080/v1/events" | Select-Object -ExpandProperty Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

Or using curl (if available):
```bash
curl http://localhost:8080/v1/events | python -m json.tool
```

## Notes

- **host.docker.internal**: Used to access host's `localhost:8000` from Docker containers. Works on Windows/Mac. On Linux, you may need to use `172.17.0.1:8000` or run `aegismas-api` outside Docker.

- **Bootstrap Mode**: If models aren't trained, agents run in bootstrap mode with conservative scoring.

- **PII Sanitization**: Request bodies are sanitized before storage (emails, tokens, long numbers are hashed).

## Success Criteria

✅ Envoy calls `/v1/decide` for each HTTP request on port 8085  
✅ Allowed requests are forwarded to real bank at `http://localhost:8000`  
✅ Blocked decisions return 403/429 and are logged to `/v1/events`  
✅ Attack script shows clear difference between defender OFF (bank receives traffic) and defender ON (many requests blocked)  
✅ LSTM and IsolationForest agents provide anomaly scores and contribute to coordinator decision

## Troubleshooting

**Issue**: All requests show as errors when defender is ON  
**Solution**: Check that Envoy can reach `aegismas-api:8080`. Verify Redis is running.

**Issue**: Models not loading  
**Solution**: Run training scripts to generate model checkpoints, or agents will use bootstrap mode.

**Issue**: Can't access `host.docker.internal:8000`  
**Solution**: On Linux, use `172.17.0.1:8000` or run `aegismas-api` outside Docker and point Envoy to `host.docker.internal:8080`.

## License

Defensive-only security tooling. For authorized testing only.

