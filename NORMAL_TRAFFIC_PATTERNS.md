# Normal Traffic Patterns Learned by the Model

## Overview

The model is trained on **synthetic normal traffic** that represents healthy bank server behavior. During training, the model learns what "normal" looks like, and anything that deviates significantly from these patterns is flagged as anomalous.

## Normal Traffic Characteristics (Training Data)

The model is trained on **800 normal samples** with the following distributions:

### 1. Requests Per Minute
- **Mean (Average)**: 180 requests/minute
- **Standard Deviation**: ±25 requests/minute
- **Range**: 60-300+ requests/minute (clipped minimum at 60)
- **Interpretation**: Normal traffic has moderate, steady request rates

### 2. Average Payload Bytes
- **Mean**: 3,500 bytes per request
- **Standard Deviation**: ±600 bytes
- **Range**: 500-5,000+ bytes (clipped minimum at 500)
- **Interpretation**: Normal requests have modest payload sizes (typical API requests)

### 3. Average Response Time
- **Mean**: 120 milliseconds
- **Standard Deviation**: ±20 ms
- **Range**: 40-200+ ms (clipped minimum at 40)
- **Interpretation**: Normal responses are fast and consistent

### 4. Error Rate Percentage
- **Mean**: 0.5% error rate
- **Standard Deviation**: ±0.2%
- **Range**: 0-1% (clipped minimum at 0)
- **Interpretation**: Normal traffic has very low error rates (< 1%)

### 5. HTTP Status Codes
- **200 OK**: 50% of requests
- **201 Created**: 20% of requests
- **202 Accepted**: 20% of requests
- **204 No Content**: 10% of requests
- **Interpretation**: Normal traffic returns successful 2xx status codes

## Summary Table

| Feature | Normal Range | Typical Value |
|---------|-------------|---------------|
| Requests/min | 60-300 | ~180 |
| Payload bytes | 500-5,000 | ~3,500 |
| Response time (ms) | 40-200 | ~120 |
| Error rate (%) | 0-1% | ~0.5% |
| Status codes | 200, 201, 202, 204 | Mostly 200 |

## What Gets Flagged as Anomalous

The model flags traffic that deviates significantly from normal patterns:

### Attack Traffic Patterns (for comparison):
- **Requests/min**: 180-500+ (high rate attacks)
- **Payload bytes**: 3,000-12,000+ (large payloads)
- **Response time**: 160-600+ ms (slow responses)
- **Error rate**: 1-10%+ (high error rates)
- **Status codes**: 400, 401, 403, 429, 500, 502, 503, 504 (error codes)

## Real-World Implications

### Requests That Should Pass (Normal):
✅ **Low to moderate request rates** (60-300 req/min)
✅ **Small to medium payloads** (500-5,000 bytes)
✅ **Fast response times** (40-200 ms)
✅ **Low error rates** (< 1%)
✅ **Successful status codes** (200, 201, 202, 204)

### Requests That May Be Flagged:
⚠️ **High request rates** (> 300 req/min) - Could indicate DDoS
⚠️ **Large payloads** (> 5,000 bytes) - Could indicate data exfiltration
⚠️ **Slow responses** (> 200 ms) - Could indicate resource exhaustion
⚠️ **High error rates** (> 1%) - Could indicate attack attempts
⚠️ **Error status codes** (4xx, 5xx) - Could indicate failed attacks or issues

## Important Notes

1. **First 8 Requests**: The defender allows the first 8 requests from any IP without ML checks to establish a baseline.

2. **Ensemble Voting**: The advanced model requires 2+ models to agree before flagging an anomaly, reducing false positives.

3. **Score Threshold**: Only requests with anomaly score < -0.25 are blocked (very anomalous).

4. **Feature Engineering**: The advanced model adds derived features:
   - Normalized status codes (2xx=0.0, 4xx=0.5, 5xx=1.0)
   - Request efficiency (req/byte ratio)
   - Latency efficiency (ms/request)
   - Error severity (combines error rate + status code)

## Example Normal Request

```python
{
    "requests_per_minute": 180,      # Normal rate
    "avg_payload_bytes": 3500,      # Typical payload
    "avg_response_time_ms": 120,     # Fast response
    "error_rate_pct": 0.5,           # Low errors
    "status_code": 200               # Success
}
```

## Example Anomalous Request

```python
{
    "requests_per_minute": 500,      # Very high rate
    "avg_payload_bytes": 9500,       # Large payload
    "avg_response_time_ms": 520,     # Slow response
    "error_rate_pct": 5.5,           # High errors
    "status_code": 503               # Server error
}
```

## Adjusting Normal Patterns

If your bank server has different normal patterns, you can adjust the training data in `generate_normal_traffic()`:

```python
# Example: Higher normal request rate
"requests_per_minute": rng.normal(loc=300, scale=50, ...)  # Instead of 180

# Example: Larger normal payloads
"avg_payload_bytes": rng.normal(loc=5000, scale=1000, ...)  # Instead of 3500
```

The model will learn these new patterns as "normal" during training.

