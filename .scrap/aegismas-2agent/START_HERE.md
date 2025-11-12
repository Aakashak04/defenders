# 🚀 START HERE - AegisMAS-2Agent

## ✅ Build Status: COMPLETE

The Docker image has been built successfully! You're ready to train and run.

---

## 📋 Step-by-Step Commands

### 1️⃣ Generate Training Data (DONE ✅)
```powershell
python scripts/gen_synthetic.py
```
**Status:** ✅ Already generated! (500 benign + 200 malicious samples)

---

### 2️⃣ Train LSTM Model
```powershell
python scripts/train_lstm.py --epochs 5
```
**Time:** ~2-5 minutes  
**Output:** `aegismas_api/models/lstm_model.pt`

---

### 3️⃣ Start Defender
```powershell
docker compose up -d
```
**Services Started:**
- Envoy Gateway: `http://localhost:8085`
- AegisMAS API: `http://localhost:8080`
- Redis: Internal

**Verify:**
```powershell
curl http://localhost:8080/health
```

---

### 4️⃣ Test WITHOUT Defender
```powershell
python attack_simulator.py --defender off
```
**Expected:** Most attacks reach your bank (many ✅ ALLOWED)

---

### 5️⃣ Test WITH Defender
```powershell
python attack_simulator.py --defender on
```
**Expected:** Many attacks blocked (many 🛑 BLOCKED with 403/429)

---

### 6️⃣ View Blocked Events
```powershell
curl "http://localhost:8080/v1/events?decision=block"
```

---

## 🎯 Quick Copy-Paste Workflow

```powershell
# Navigate to project
cd aegismas-2agent

# Train LSTM (if not done)
python scripts/train_lstm.py --epochs 5

# Start defender
docker compose up -d

# Wait 10 seconds
Start-Sleep -Seconds 10

# Test with defender
python attack_simulator.py --defender on

# View results
curl "http://localhost:8080/v1/events?decision=block"
```

---

## 📚 Full Documentation

- **QUICKSTART.md** - Complete guide with all commands
- **COMMANDS.md** - Quick reference cheat sheet
- **README.md** - Full project documentation

---

## ⚠️ Prerequisites

1. ✅ Docker and Docker Compose installed
2. ✅ Python 3.11+ installed
3. ✅ Bank running at `http://localhost:8000`
4. ✅ Training data generated (DONE ✅)

---

## 🆘 Troubleshooting

**Defender won't start?**
```powershell
docker compose logs
```

**Can't connect to bank?**
```powershell
curl http://localhost:8000/health
```

**Models not loading?**
- Models work in bootstrap mode without training
- Training improves accuracy but isn't required

---

**Ready to protect! 🛡️**

