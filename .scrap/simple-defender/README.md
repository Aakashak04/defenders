# Simple Rule-Based Defender

Minimal inline defender protecting bank at `localhost:8000`.

## Architecture

- **Envoy Gateway** (port 8085): Receives all requests, calls Decision API
- **Defender API** (port 8080): FastAPI service with rule-based detection

## Quick Start

### Start Defender
```bash
docker compose up -d
```

### Test Without Defender (Direct to Bank)
```bash
# Attack simulator hits bank directly
python attack_simulator.py --defender off
```

### Test With Defender (Through Envoy)
```bash
# Attack simulator hits Envoy gateway
python attack_simulator.py --defender on
```

### View Logs
```bash
curl http://localhost:8080/events
```

## How It Works

1. Attacker sends request to `localhost:8085`
2. Envoy calls `POST http://defender_api:8080/v1/decide` with request details
3. Defender API checks rules:
   - SQL Injection patterns
   - XSS patterns
   - Path Traversal patterns
   - RCE patterns
4. If malicious → Returns `{"action": "block"}` → Envoy returns 403
5. If safe → Returns `{"action": "allow"}` → Envoy forwards to `localhost:8000`

## Rules

The defender blocks requests matching:
- **SQLi**: `UNION SELECT`, `OR 1=1`, `DROP TABLE`, etc.
- **XSS**: `<script>`, `javascript:`, event handlers
- **Path Traversal**: `../`, `..\\`, URL encoded variants
- **RCE**: Command injection, eval, system calls

## Endpoints

- `POST /v1/decide` - Decision endpoint (called by Envoy)
- `GET /events` - View blocked/allowed events
- `GET /health` - Health check

