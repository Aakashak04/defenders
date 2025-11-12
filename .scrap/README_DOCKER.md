# Simple Defender - Docker Setup

Minimal Docker setup for the Simple Defender demo.

## Quick Start

### 1. Build and Start Services

```bash
docker-compose up --build
```

This starts:
- **Defender** on `http://localhost:8081`
- **Gateway** on `http://localhost:8086`

### 2. Ensure Your Bank is Running

Make sure your bank application is running on `http://localhost:8000` (on your host machine).

### 3. Test with Attack Script

**Defender OFF** (direct to bank):
```bash
python attack.py --defender off
```

**Defender ON** (through gateway):
```bash
python attack.py --defender on
```

### 4. View Blocked Events

```bash
curl http://localhost:8081/events
```

Or in browser: `http://localhost:8081/events`

## Manual Testing

**Benign request** (should forward to bank):
```bash
curl http://localhost:8086/health
```

**SQLi attack** (should be blocked):
```bash
curl "http://localhost:8086/accounts?account_id=1' OR '1'='1"
```

**Path traversal** (should be blocked):
```bash
curl "http://localhost:8086/accounts/../../../etc/passwd"
```

## Stop Services

```bash
docker-compose down
```

## Troubleshooting

- If gateway can't reach defender: Check that both containers are running with `docker ps`
- If gateway can't reach bank: On Windows/Mac, `host.docker.internal` should work. On Linux, you may need to use `172.17.0.1` or your host IP
- To view logs: `docker-compose logs -f`
- To rebuild: `docker-compose up --build --force-recreate`

