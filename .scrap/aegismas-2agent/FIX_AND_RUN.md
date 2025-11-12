# 🔧 Fix: Defender Errors - Step by Step

## Problem
When running with defender ON, everything shows as errors (no allowed/blocked).

## Solution

### Step 1: Stop Everything
```powershell
# Stop any running containers
docker compose down

# Stop any local Python processes (if API is running locally)
# Press Ctrl+C in any terminal running the API
```

### Step 2: Start Defender Properly
```powershell
cd aegismas-2agent

# Start all services
docker compose up -d

# Wait 15 seconds for everything to start
Start-Sleep -Seconds 15
```

### Step 3: Verify Services
```powershell
# Run diagnostic
python diagnose.py
```

**Expected Output:**
```
✅ AegisMAS API: OK (Status 200)
✅ Envoy Gateway: OK (Status 200)
✅ Bank (Origin): OK (Status 200)
```

### Step 4: Test Again
```powershell
python attack_simulator.py --defender on
```

---

## If Still Getting Errors

### Check Logs
```powershell
# View all logs
docker compose logs

# View API logs
docker compose logs aegismas-api

# View Envoy logs
docker compose logs envoy
```

### Common Issues:

1. **Port Already in Use**
   ```powershell
   # Check what's using port 8080
   netstat -ano | findstr :8080
   
   # Check what's using port 8085
   netstat -ano | findstr :8085
   ```

2. **Redis Not Connected**
   ```powershell
   # Check Redis logs
   docker compose logs redis
   ```

3. **Rebuild Everything**
   ```powershell
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```

---

## Quick Fix Command
```powershell
# Complete reset and restart
cd aegismas-2agent
docker compose down
docker compose up --build -d
Start-Sleep -Seconds 15
python diagnose.py
python attack_simulator.py --defender on
```

