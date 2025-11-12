# Train and Test the ML Defender

## Step 1: Train the Model (Optional - Defender auto-trains on startup)

Train the model explicitly to verify it works:

```bash
cd anomaly_detection
python train.py
```

Or use the main script:

```bash
cd anomaly_detection
python bank_traffic_anomaly_detector.py
```

**Note:** The defender will automatically train the model when it starts, so this step is optional but useful for verification.

## Step 2: Start the Defender Stack

From the project root:

```bash
docker compose up --build
```

This will:
- Build the defender container with ML dependencies
- Start the defender API (port 8081)
- Start the gateway (port 8086)
- Auto-train the ML model on startup

Wait for the logs to show:
```
[defender] === Isolation Forest Anomaly Detection Summary ===
```

## Step 3: Ensure Bank Server is Running

Make sure your bank server is running on `localhost:8000`. If not, start it:

```bash
# Example (adjust based on your bank server setup)
python -m uvicorn gateway.proxy:app --reload --port 8000
```

## Step 4: Test with Attack Script

Run the attack simulator to test both legitimate and malicious requests:

```bash
# Test with defender ON (through gateway)
python attack.py --defender on

# Test with defender OFF (direct to bank - for comparison)
python attack.py --defender off
```

## Expected Results

### With Defender ON:
- ✅ **Legitimate requests** (first 10): Should pass through (ALLOWED)
- 🛑 **Malicious requests**: Should be blocked (403 for signatures, 429 for ML anomalies)

### What to Look For:
1. First 8 legitimate requests: Should pass (ML not active yet)
2. Remaining legitimate requests: Should pass (ML active but score > -0.25)
3. SQL Injection attacks: Blocked with 403 (signature-based)
4. XSS/Path Traversal/RCE: Blocked with 403 (signature-based)
5. High-rate attacks: May be blocked with 429 (ML anomaly detection)

## View Defender Logs

Check what the defender detected:

```bash
curl http://localhost:8081/events
```

## Troubleshooting

If legitimate requests are still being blocked:
- Check defender logs for ML initialization errors
- Verify the model trained successfully (look for "Training Complete" in logs)
- The first 8 requests from each IP bypass ML detection
- ML only blocks if anomaly score < -0.25

If attacks are not being blocked:
- Check that signature patterns match
- Verify ML model initialized correctly
- Check defender logs for errors

