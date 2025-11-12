# Attack Simulator

This script attacks your bank at `localhost:8000` either directly (defender OFF) or through the Envoy gateway (defender ON).

## Setup

Install dependencies:
```bash
pip install aiohttp
```

## Usage

### Attack with Defender OFF (Direct to Bank)
```bash
python attacker.py --defender off
```
This attacks `http://localhost:8000` directly, bypassing the defender.

### Attack with Defender ON (Through Envoy)
```bash
python attacker.py --defender on
```
This attacks `http://localhost:8085` which goes through:
- Envoy Gateway → AegisMAS Defender → Your Bank (localhost:8000)

### Quiet Mode (Summary Only)
```bash
python attacker.py --defender on --quiet
```

## What It Tests

1. **SQL Injection** - Various SQLi payloads
2. **Path Traversal** - Directory traversal attempts
3. **Command Injection** - RCE attempts
4. **XSS** - Cross-site scripting payloads
5. **Rate Limiting** - Rapid fire requests (50 requests)

## Expected Results

- **Defender OFF**: Most/all attacks should be ALLOWED (reach your bank)
- **Defender ON**: Malicious attacks should be BLOCKED (403/429), normal requests ALLOWED

## Starting the Defender

Make sure your bank is running on `localhost:8000`, then:

```bash
docker compose up --build
```

The defender will be available at `http://localhost:8085`

