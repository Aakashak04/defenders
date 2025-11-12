## AegisMAS — AI-Powered Multi-Agent Cybersecurity Gateway

A stand-alone security gateway that sits in front of bank origin servers. Requests go to Envoy first, Envoy calls the AegisMAS Decision API, and then forwards or blocks based on the decision.

### Architecture

Client → Envoy → AegisMAS Decision API → allow/block → Forward to Bank Origin → Response

### Repository Structure

```
aegismas/
 ├── gateway/
 │    └── envoy.yaml
 ├── aegismas-api/
 │    ├── Dockerfile
 │    ├── main.py
 │    ├── requirements.txt
 │    ├── tenants.json
 │    └── agents/
 │         ├── __init__.py
 │         ├── signature_agent.py
 │         ├── anomaly_agent.py
 │         ├── reputation_agent.py
 │         └── coordinator.py
 ├── docker-compose.yml
 ├── banks/
 │    ├── bank-alpha/
 │    │    ├── Dockerfile
 │    │    ├── app.py
 │    │    └── requirements.txt
 │    └── bank-beta/
 │         ├── Dockerfile
 │         ├── app.py
 │         └── requirements.txt
 └── README.md
```

### Services

- envoy: security gateway on port 80
- aegismas-api: decision engine on port 8080
- redis: counters/rate limits
- bank-alpha-backend: demo bank origin
- bank-beta-backend: demo bank origin

### How to Run

1) Add hosts entries (Windows: `C:\Windows\System32\drivers\etc\hosts`, Linux/Mac: `/etc/hosts`):

```
127.0.0.1 bank-alpha.local
127.0.0.1 bank-beta.local
```

2) Start everything:

```
docker compose up --build
```

3) Test through Envoy:

```
curl http://bank-alpha.local/accounts
curl http://bank-beta.local/health
```

Expected flow:
- Envoy calls AegisMAS at `/v1/decide`
- AegisMAS responds with action and headers `x-aegis-tenant` and `x-aegis-origin`
- If allowed, Envoy routes based on `cluster_header: x-aegis-origin` to the right bank
- Client receives the bank response

### Decision API

- Endpoint: `POST /v1/decide`
- Output (JSON body for observability) includes `action`, `reason`, `origin`, `tenant`
- Envoy behavior:
  - allow → AegisMAS returns HTTP 200; Envoy forwards request, adding headers from authz response
  - block → AegisMAS returns HTTP 403
  - challenge → AegisMAS returns HTTP 429

### Multi-Tenant

Tenants configured in `aegismas-api/tenants.json`. The tenant is derived from the hostname prefix, e.g., `bank-alpha.local` → `bank-alpha`. The coordinator maps the tenant to both the origin URL and the Envoy cluster name, and sets:

- `x-aegis-tenant`: tenant name
- `x-aegis-origin`: Envoy cluster name (used for routing)
- `x-aegis-origin-url`: Origin URL for observability

### Notes

- Port 80 may require elevated privileges on some systems. If unavailable, change the published port in `docker-compose.yml` and `curl` accordingly.
- For demo purposes, agents implement simple heuristics and Redis-backed counters. Production systems should harden parsing, logging, and model decisions.





