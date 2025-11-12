"""
AegisMAS-2Agent Main API
Simple Rule-Based Blocker
"""
import os
import time
import re
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
import redis
from redis.exceptions import ConnectionError as RedisConnectionError

from .config import config
from .events_db import init_db, store_event, get_events, get_event_count


# Initialize database
init_db()

# Initialize Redis
try:
    rds = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
    rds.ping()  # Test connection
    print(f"Connected to Redis at {config.REDIS_URL}")
except (RedisConnectionError, Exception) as e:
    print(f"Redis connection failed: {e}. Using in-memory fallback.")
    rds = None

# Malicious patterns - simple rule-based blocking
MALICIOUS_PATTERNS = [
    (r"(?i)(union\s+select|select\s+.*\s+from|insert\s+into|delete\s+from|drop\s+table|exec\s+\(|execute\s+\()", "sqli"),
    (r"(?i)(\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c)", "path_traversal"),
    (r"(?i)(<script|javascript:|onerror=|onload=|onclick=)", "xss"),
    (r"(?i)(\|\||&&|;|\$\(|`|eval\(|exec\(|system\()", "rce"),
    (r"(?i)(or\s+1\s*=\s*1|and\s+1\s*=\s*1|'or'|'and')", "sqli_boolean"),
]

# FastAPI app
app = FastAPI(
    title="AegisMAS-2Agent",
    version="2.0.0",
    description="Simple Rule-Based Blocker",
)

# Exception handler to catch 404s and handle /v1/decide requests
@app.exception_handler(StarletteHTTPException)
async def handle_404(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and request.url.path.startswith("/v1/decide"):
        # Handle the request
        method = request.headers.get(":method") or request.method
        original_path = request.url.path[len("/v1/decide"):] or "/"
        query = request.url.query
        
        # Get body
        try:
            raw_body = await request.body()
            body_sample = raw_body[:2048].decode(errors="ignore")
        except:
            body_sample = ""
        
        # Get IP
        ip = request.client.host if request.client else request.headers.get("x-forwarded-for", "127.0.0.1").split(",")[0].strip()
        
        # Combine all text to check
        text_to_check = f"{original_path} {query} {body_sample}".lower()
        
        # Check for malicious patterns
        blocked = False
        block_reason = ""
        for pattern, reason in MALICIOUS_PATTERNS:
            if re.search(pattern, text_to_check):
                blocked = True
                block_reason = reason
                break
        
        # Store event
        store_event(
            ip=ip,
            path=original_path,
            method=method,
            body_sample=body_sample[:100],
            agents_json={"rule_based": {"blocked": blocked, "reason": block_reason}},
            decision="block" if blocked else "allow",
            forwarded=not blocked,
            tenant=None,
            reason=block_reason if blocked else "rule_check_passed",
        )
        
        # Return response - 403 = block, 200 = allow
        if blocked:
            return JSONResponse(
                content={"action": "block", "reason": block_reason},
                status_code=403,
            )
        else:
            return JSONResponse(
                content={"action": "allow", "reason": "rule_check_passed"},
                status_code=200,
            )
    
    # For other 404s, return normal 404
    return JSONResponse(
        content={"detail": exc.detail},
        status_code=exc.status_code,
    )

# Request/Response Models
class DecideRequest(BaseModel):
    tenant: Optional[str] = None
    client_ip: str
    method: str
    path: str
    query: str = ""
    headers: Dict[str, str] = {}
    body_sample: str = ""


class DecideResponse(BaseModel):
    action: str  # allow | block | challenge
    reason: str
    signals: Dict[str, Any]
    origin: str


class FeedbackRequest(BaseModel):
    event_id: int
    malicious: bool


class TrainRequest(BaseModel):
    epochs: int = 3


# Helper function to get recent RPS
def get_recent_rps(ip: str, window_seconds: int = 60) -> float:
    """Get recent requests per second for IP."""
    if rds is None:
        return 0.0
    
    try:
        now = int(time.time())
        key = f"rps:{ip}:{now // window_seconds}"
        count = rds.incr(key)
        rds.expire(key, window_seconds * 2)
        return count / window_seconds
    except:
        return 0.0


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "redis": "connected" if rds else "disconnected",
    }


@app.get("/metrics")
def metrics():
    """Metrics endpoint."""
    total_events = get_event_count()
    blocked_count = get_event_count(decision="block")
    allowed_count = get_event_count(decision="allow")
    challenge_count = get_event_count(decision="challenge")
    
    return {
        "total_events": total_events,
        "blocked": blocked_count,
        "allowed": allowed_count,
        "challenge": challenge_count,
        "block_rate": blocked_count / max(total_events, 1),
    }




@app.get("/v1/events")
def list_events(
    limit: int = 100,
    offset: int = 0,
    ip: Optional[str] = None,
    decision: Optional[str] = None,
):
    """Get recent events."""
    events = get_events(limit=limit, offset=offset, ip=ip, decision=decision)
    total = get_event_count(ip=ip, decision=decision)
    
    return {
        "events": events,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.post("/v1/feedback")
def feedback(feedback_req: FeedbackRequest):
    """Provide feedback on an event (for training)."""
    # TODO: Store feedback for training
    # For now, just acknowledge
    return {
        "status": "received",
        "event_id": feedback_req.event_id,
        "label": "malicious" if feedback_req.malicious else "benign",
    }


@app.post("/v1/train")
def train(train_req: TrainRequest):
    """Trigger training job (admin only in PoC)."""
    # TODO: Implement training
    return {
        "status": "training_initiated",
        "epochs": train_req.epochs,
        "message": "Training not yet implemented. Use scripts/train_lstm.py",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "aegismas_api.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
    )

