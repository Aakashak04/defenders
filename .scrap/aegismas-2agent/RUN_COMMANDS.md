# 🚀 Run Commands - With & Without Defender

## Prerequisites

Make sure your bank is running at `http://localhost:8000`

---

## ⚙️ WITHOUT Defender (Direct to Bank)

### Step 1: Stop Defender (if running)
```powershell
cd aegismas-2agent
docker compose down
```

### Step 2: Run Attack Simulator
```powershell
python attack_simulator.py --defender off
```

**Expected Result:**
- Most/all attacks reach your bank directly
- Many ✅ ALLOWED responses
- Bank receives attack traffic

---

## 🛡️ WITH Defender (Through Envoy Gateway)

### Step 1: Start Defender
```powershell
cd aegismas-2agent
docker compose up -d
```

### Step 2: Wait for Services (10 seconds)
```powershell
Start-Sleep -Seconds 10
```

### Step 3: Verify Defender is Running
```powershell
curl http://localhost:8080/health
```

**Expected Response:**
```json
{"status":"ok","timestamp":"...","redis":"connected"}
```

### Step 4: Run Attack Simulator
```powershell
python attack_simulator.py --defender on
```

**Expected Result:**
- Many attacks blocked by defender
- Many 🛑 BLOCKED responses (403/429)
- Only safe requests reach your bank

---

## 📊 View Results

### View All Events
```powershell
curl http://localhost:8080/v1/events
```

### View Only Blocked Events
```powershell
curl "http://localhost:8080/v1/events?decision=block"
```

### View Metrics
```powershell
curl http://localhost:8080/metrics
```

### PowerShell Alternative (View Blocked Events)
```powershell
$response = Invoke-WebRequest -Uri "http://localhost:8080/v1/events?decision=block"
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

---

## 🔄 Complete Test Cycle

### Test WITHOUT Defender
```powershell
# Stop defender
docker compose down

# Run attacks
python attack_simulator.py --defender off

# Check: Should see many ALLOWED
```

### Test WITH Defender
```powershell
# Start defender
docker compose up -d

# Wait
Start-Sleep -Seconds 10

# Run attacks
python attack_simulator.py --defender on

# View blocked events
curl "http://localhost:8080/v1/events?decision=block"

# Check: Should see many BLOCKED
```

---

## 🎯 Quick Comparison

### Defender OFF
```powershell
docker compose down
python attack_simulator.py --defender off
```
**Result:** ~60-70 ALLOWED, ~0-5 BLOCKED

### Defender ON
```powershell
docker compose up -d
Start-Sleep -Seconds 10
python attack_simulator.py --defender on
```
**Result:** ~20-30 ALLOWED, ~40-50 BLOCKED

---

## 🛑 Stop Defender When Done

```powershell
docker compose down
```

---

## 📝 Quiet Mode (Summary Only)

If you want just the summary without detailed output:

```powershell
# Without defender
python attack_simulator.py --defender off --quiet

# With defender
python attack_simulator.py --defender on --quiet
```

---

## ✅ Verification Checklist

- [ ] Bank running at `http://localhost:8000`
- [ ] Defender stopped for "without" test
- [ ] Defender started for "with" test
- [ ] Services healthy (`curl http://localhost:8080/health`)
- [ ] Attack simulator runs successfully
- [ ] Can view events at `/v1/events`

---

**Ready to test! 🚀**

