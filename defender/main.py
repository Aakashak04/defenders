# defender/main.py
from __future__ import annotations

from collections import deque
import os
import re
import sqlite3
import time
from typing import Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

try:
    from anomaly_detection.bank_traffic_anomaly_detector import (
        detect_request as ml_detect_request,
        get_anomaly_score as ml_get_anomaly_score,
        initialize_advanced_detector as initialize_ml_detector,
    )
    USE_ADVANCED_MODEL = True
except ImportError:
    # Fallback to basic model if advanced not available
    try:
        from anomaly_detection.bank_traffic_anomaly_detector import (
            detect_request as ml_detect_request,
            get_anomaly_score as ml_get_anomaly_score,
            initialize_detector as initialize_ml_detector,
        )
        USE_ADVANCED_MODEL = False
    except Exception as import_exc:
        print(f"[defender] Warning: Failed to import ML detector: {import_exc}")
        ml_detect_request = None
        ml_get_anomaly_score = None
        initialize_ml_detector = None
        ML_DETECTOR_AVAILABLE = False
        USE_ADVANCED_MODEL = False
else:
    ML_DETECTOR_AVAILABLE = True

# Initialize the detector
if ML_DETECTOR_AVAILABLE and initialize_ml_detector is not None:
    try:
        print(f"[defender] Initializing {'Advanced' if USE_ADVANCED_MODEL else 'Basic'} ML detector...")
        initialize_ml_detector(show_plot=False, verbose=True)
        ML_DETECTOR_AVAILABLE = True
        print(f"[defender] ✓ ML detector ready ({'Advanced Ensemble' if USE_ADVANCED_MODEL else 'Isolation Forest'})")
    except Exception as init_exc:  # pragma: no cover - optional dependency
        print(f"[defender] Warning: Failed to initialize ML detector: {init_exc}")
        ML_DETECTOR_AVAILABLE = False

app = FastAPI(title="Simple Defender")

DB_PATH = os.getenv("DEFENDER_DB", "/app/data/events.db")
ORIGIN = os.getenv("ORIGIN", "http://localhost:8000")  # where to forward when allowed

# Ensure DB directory exists
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    try:
        os.makedirs(db_dir, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create DB directory {db_dir}: {e}")
        # Fallback to current directory
        DB_PATH = "events.db"

# Ensure DB exists
try:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
except Exception as e:
    print(f"Error connecting to DB at {DB_PATH}: {e}")
    # Fallback to in-memory for testing
    DB_PATH = ":memory:"
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute(
    """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER,
  ip TEXT,
  method TEXT,
  path TEXT,
  query TEXT,
  reason TEXT,
  body_sample TEXT
)
"""
)
conn.commit()

# Simple signature rules (small and readable)
SQLI_PATTERNS = [
    r"(?i)union\s+select",
    r"(?i)or\s+'1'='1",
    r"(?i)drop\s+table",
    r"(?i)information_schema",
    r"(?i)sleep\(",
]
XSS_PATTERNS = [r"(?i)<script", r"(?i)onerror=", r"(?i)javascript:"]
TRAV_PATTERNS = [r"\.\./", r"\.\.\\\\"]
RCE_PATTERNS = [r"[;|&]{1,2}\s*(cat|whoami|ls|id)", r"\$\{jndi:"]


def match_any(patterns, text):
    if not text:
        return None
    for p in patterns:
        if re.search(p, text):
            return p
    return None


def log_event(ip, method, path, query, reason, body_sample):
    ts = int(time.time())
    sample = (body_sample or "")[:1024]
    conn.execute(
        "INSERT INTO events (ts, ip, method, path, query, reason, body_sample) VALUES (?,?,?,?,?,?,?)",
        (ts, ip, method, path, query, reason, sample),
    )
    conn.commit()


class DecideRequest(BaseModel):
    ts: Optional[int]
    ip: Optional[str]
    method: Optional[str]
    path: Optional[str]
    query: Optional[str]
    headers: Optional[dict]
    body_sample: Optional[str]


class RunningAverage:
    """Track a simple running average for streaming values."""

    def __init__(self) -> None:
        self.total = 0.0
        self.count = 0

    def add(self, value: float) -> float:
        self.total += value
        self.count += 1
        return self.mean(value)

    def mean(self, default: float) -> float:
        if self.count == 0:
            return default
        return self.total / self.count


class TrafficStatsTracker:
    """Maintain rolling traffic metrics required by the anomaly detector."""

    def __init__(self, window_seconds: int = 60, default_response_time_ms: float = 120.0) -> None:
        self.window_seconds = window_seconds
        self.default_response_time_ms = default_response_time_ms
        self.request_windows: Dict[str, deque] = {}
        self.payload_stats: Dict[str, RunningAverage] = {}
        self.response_stats: Dict[str, RunningAverage] = {}
        self.error_stats: Dict[str, Dict[str, int]] = {}
        self.last_status: Dict[str, int] = {}
        self.request_counts: Dict[str, int] = {}  # Track total requests per IP for ML threshold

    def snapshot(self, ip: str, payload_size: int, headers: Optional[dict]) -> Dict[str, float]:
        """Record the current request and return feature vector for detection."""

        # Increment total request count for this IP
        self.request_counts[ip] = self.request_counts.get(ip, 0) + 1

        now = time.time()
        window = self.request_windows.setdefault(ip, deque())
        window.append(now)
        while window and now - window[0] > self.window_seconds:
            window.popleft()
        # Calculate requests per minute, but cap at reasonable maximum to prevent false positives
        # from rapid-fire testing scenarios
        raw_rpm = len(window) * (60 / self.window_seconds)
        requests_per_minute = min(raw_rpm, 300.0)  # Cap at 300 req/min to avoid false positives

        payload_avg = self.payload_stats.setdefault(ip, RunningAverage())
        avg_payload_bytes = payload_avg.add(float(payload_size))

        response_observation = self._extract_response_time(headers)
        if response_observation is not None:
            response_avg = self.response_stats.setdefault(ip, RunningAverage())
            avg_response_time_ms = response_avg.add(response_observation)
        else:
            response_avg = self.response_stats.get(ip)
            avg_response_time_ms = (
                response_avg.mean(self.default_response_time_ms) if response_avg else self.default_response_time_ms
            )

        error_state = self.error_stats.get(ip)
        if error_state and error_state["total"]:
            error_rate_pct = (error_state["blocked"] / error_state["total"]) * 100.0
        else:
            error_rate_pct = 0.0

        status_code = self.last_status.get(ip, 200)

        return {
            "requests_per_minute": requests_per_minute,
            "avg_payload_bytes": avg_payload_bytes,
            "avg_response_time_ms": avg_response_time_ms,
            "error_rate_pct": error_rate_pct,
            "status_code": status_code,
        }

    def record_outcome(self, ip: str, *, blocked: bool, status_code: int) -> None:
        """Update trailing error stats and last status after a decision is made."""

        state = self.error_stats.setdefault(ip, {"blocked": 0, "total": 0})
        state["total"] += 1
        if blocked:
            state["blocked"] += 1

        self.last_status[ip] = status_code

    def get_request_count(self, ip: str) -> int:
        """Return the total number of requests seen from this IP."""
        return self.request_counts.get(ip, 0)

    @staticmethod
    def _extract_response_time(headers: Optional[dict]) -> Optional[float]:
        """Capture response time hints (if provided) from request headers in milliseconds."""

        if not headers:
            return None

        for key, value in headers.items():
            key_lower = str(key).lower()
            if key_lower in {"x-response-time", "x-response-duration", "x-latency", "x-latency-ms"}:
                try:
                    cleaned = str(value).strip().lower()
                    if cleaned.endswith("ms"):
                        cleaned = cleaned[:-2]
                    if cleaned.endswith("s"):
                        cleaned = cleaned[:-1]
                        return float(cleaned) * 1000.0
                    return float(cleaned)
                except ValueError:
                    continue
        return None


stats_tracker = TrafficStatsTracker()


@app.post("/v1/decide")
async def decide(req: DecideRequest):
    ip = req.ip or "unknown"
    method = (req.method or "GET").upper()
    path = req.path or "/"
    query = req.query or ""
    body = req.body_sample or ""
    headers = req.headers or {}

    payload_size = len(body.encode("utf-8")) if body else 0
    payload_size += len(query.encode("utf-8")) if query else 0
    metrics = stats_tracker.snapshot(ip, payload_size, headers)

    # Signatures first
    s = match_any(SQLI_PATTERNS, f"{path} {query} {body}")
    if s:
        log_event(ip, method, path, query, "sqli", body)
        stats_tracker.record_outcome(ip, blocked=True, status_code=403)
        return {"action": "block", "reason": "sqli", "status": 403}

    s = match_any(XSS_PATTERNS, f"{path} {query} {body}")
    if s:
        log_event(ip, method, path, query, "xss", body)
        stats_tracker.record_outcome(ip, blocked=True, status_code=403)
        return {"action": "block", "reason": "xss", "status": 403}

    s = match_any(TRAV_PATTERNS, f"{path} {query}")
    if s:
        log_event(ip, method, path, query, "traversal", body)
        stats_tracker.record_outcome(ip, blocked=True, status_code=403)
        return {"action": "block", "reason": "traversal", "status": 403}

    s = match_any(RCE_PATTERNS, f"{path} {query} {body}")
    if s:
        log_event(ip, method, path, query, "rce", body)
        stats_tracker.record_outcome(ip, blocked=True, status_code=403)
        return {"action": "block", "reason": "rce", "status": 403}

    # ML-based anomaly detection with safeguards to reduce false positives
    if ML_DETECTOR_AVAILABLE and ml_detect_request is not None and ml_get_anomaly_score is not None:
        # Only apply ML detection after we have enough baseline data (minimum 8 requests)
        request_count = stats_tracker.get_request_count(ip)
        if request_count >= 8:
            try:
                # Use anomaly score instead of binary prediction for finer control
                anomaly_score = ml_get_anomaly_score(metrics)
                # Only block if score is very negative (highly anomalous)
                # Typical range: -0.5 (very anomalous) to 0.5 (very normal)
                # Threshold of -0.25 means we only block clearly anomalous traffic
                if anomaly_score < -0.25:
                    log_event(ip, method, path, query, f"ml_anomaly (score: {anomaly_score:.3f})", body)
                    stats_tracker.record_outcome(ip, blocked=True, status_code=429)
                    return {"action": "block", "reason": "ml_anomaly", "status": 429}
            except Exception as ml_exc:  # pragma: no cover - defensive logging
                print(f"[defender] Warning: ML detection error: {ml_exc}")

    # default allow
    stats_tracker.record_outcome(ip, blocked=False, status_code=200)
    return {"action": "allow", "origin": ORIGIN}


@app.get("/events")
def events(limit: int = 100):
    cur = conn.execute(
        "SELECT id, ts, ip, method, path, query, reason FROM events ORDER BY ts DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    out = []
    for r in rows:
        out.append({"id": r[0], "ts": r[1], "ip": r[2], "method": r[3], "path": r[4], "query": r[5], "reason": r[6]})
    return out


@app.get("/health")
def health():
    return {"status": "defender_ok"}

