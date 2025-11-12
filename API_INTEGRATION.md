# Virtual Bank API Integration

## Overview

The attack simulator and legitimate request patterns have been updated to match your actual **Virtual Bank API** endpoints based on the OpenAPI specification.

## Updated Legitimate Requests

The simulator now tests these real API endpoints:

### Authentication Endpoints
- ✅ `/health` - Health check
- ✅ `/auth/register` - User registration
- ✅ `/auth/login` - User login
- ✅ `/auth/refresh` - Token refresh

### Account Endpoints
- ✅ `/accounts` - List accounts (GET)
- ✅ `/accounts` - Create account (POST)
- ✅ `/accounts/{account_id}` - Get specific account
- ✅ `/accounts/{from_id}/transfer` - Transfer funds

### Transaction Endpoints
- ✅ `/transactions` - Get transaction history (with query parameters)
- ✅ `/transactions` - Filtered transactions (date range, type)

## Updated Attack Patterns

### SQL Injection Attacks
- Targets: `/accounts/{account_id}` (path parameter)
- Targets: `/transactions?account_id={payload}` (query parameter)
- Targets: `/auth/login` (POST body)

### Path Traversal Attacks
- Targets: `/accounts/{payload}` (path traversal in account ID)

### RCE Attacks
- Targets: `/admin/audit-logs?user_id={payload}` (admin endpoints)

### XSS Attacks
- Targets: `/transactions?note={payload}` (query parameters)

## API Endpoints Covered

Based on your OpenAPI spec, the simulator now covers:

| Endpoint | Method | Tested As |
|----------|--------|-----------|
| `/health` | GET | ✅ Legitimate |
| `/auth/register` | POST | ✅ Legitimate |
| `/auth/login` | POST | ✅ Legitimate + SQL Injection |
| `/auth/refresh` | POST | ✅ Legitimate |
| `/auth/logout` | POST | - |
| `/accounts` | GET | ✅ Legitimate |
| `/accounts` | POST | ✅ Legitimate |
| `/accounts/{account_id}` | GET | ✅ Legitimate + SQL Injection + Path Traversal |
| `/accounts/{account_id}/freeze` | PATCH | - |
| `/accounts/{account_id}/unfreeze` | PATCH | - |
| `/accounts/{from_id}/transfer` | POST | ✅ Legitimate |
| `/transactions` | GET | ✅ Legitimate + SQL Injection + XSS |
| `/admin/audit-logs` | GET | RCE Attacks |
| `/admin/analytics` | GET | - |

## Testing Your API

When you run the attack simulator:

```bash
python attack.py --defender on
```

You'll see:

1. **Legitimate Requests** - Real API calls that should pass through
2. **SQL Injection** - Targeting account IDs and transaction queries
3. **Path Traversal** - In account ID paths
4. **RCE** - In admin endpoint queries
5. **XSS** - In transaction query parameters

## Expected Behavior

### Legitimate Requests Should:
- ✅ Pass through the gateway (status 200, 201, 204)
- ✅ Not trigger ML anomaly detection (after first 8 requests)
- ✅ Not match signature-based rules

### Attack Requests Should:
- 🛑 Be blocked by signature rules (status 403)
- 🛑 Be blocked by ML anomaly detection (status 429)
- 🛑 Not reach your bank server

## Customization

If you want to add more legitimate requests or attack patterns, edit `attack.py`:

```python
LEGITIMATE_REQUESTS = [
    {"path": "/your/endpoint", "method": "GET", "payload": None, "description": "Your description"},
    # Add more...
]
```

## Notes

- The simulator uses realistic request patterns matching your API structure
- All legitimate requests include proper headers (`X-Response-Time`, `Accept: application/json`)
- Attack patterns target actual vulnerable points in your API
- The defender learns normal patterns from these legitimate requests

