# Quick Command Reference

## 🏗️ BUILD

```powershell
cd aegismas-2agent
docker compose build
```

## 🎓 TRAIN

```powershell
# 1. Generate training data
python scripts/gen_synthetic.py

# 2. Train LSTM model
python scripts/train_lstm.py --epochs 5 --batch-size 32
```

## 🚀 RUN DEFENDER

```powershell
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop defender
docker compose down
```

## ⚔️ RUN ATTACKER

```powershell
# Test WITHOUT defender (direct to bank)
python attack_simulator.py --defender off

# Test WITH defender (through Envoy gateway)
python attack_simulator.py --defender on

# Quiet mode (summary only)
python attack_simulator.py --defender on --quiet
```

## 📊 VIEW EVENTS

```powershell
# All events
curl http://localhost:8080/v1/events

# Only blocked events
curl "http://localhost:8080/v1/events?decision=block"

# Metrics
curl http://localhost:8080/metrics
```

## ✅ VERIFY

```powershell
# Health check
curl http://localhost:8080/health

# Check services
docker compose ps
```

