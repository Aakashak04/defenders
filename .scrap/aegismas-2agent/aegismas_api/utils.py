"""
Utility functions for AegisMAS-2Agent
"""
import re
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime


def sanitize_body(body: str, max_length: int = 2048) -> str:
    """
    Sanitize request body by masking PII and tokens.
    """
    if not body:
        return ""
    
    # Truncate
    body = body[:max_length]
    
    # Mask emails
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    body = re.sub(email_pattern, lambda m: f"email_{hashlib.md5(m.group().encode()).hexdigest()[:8]}", body)
    
    # Mask bearer tokens
    bearer_pattern = r'Bearer\s+[A-Za-z0-9\-._~+/]+=*'
    body = re.sub(bearer_pattern, lambda m: f"Bearer_TOKEN_{hashlib.md5(m.group().encode()).hexdigest()[:8]}", body, flags=re.IGNORECASE)
    
    # Mask long numbers (potential credit cards, SSNs, etc.)
    long_number_pattern = r'\b\d{7,}\b'
    body = re.sub(long_number_pattern, lambda m: f"NUMBER_{hashlib.md5(m.group().encode()).hexdigest()[:8]}", body)
    
    return body


def extract_features(
    method: str,
    path: str,
    body_sample: str,
    query: str = "",
    hour_of_day: Optional[int] = None,
    recent_rps: float = 0.0,
) -> list:
    """
    Extract feature vector for ML agents.
    Returns: [path_hash, method_id, body_len, nonalpha_ratio, hour, rps, query_len, header_count_estimate]
    """
    import time
    
    # Path hash (simple hash to int, normalize to 0-1)
    path_hash = abs(hash(path)) % 10000 / 10000.0
    
    # Method ID (GET=0, POST=1, PUT=2, PATCH=3, DELETE=4, other=5)
    method_map = {"GET": 0, "POST": 1, "PUT": 2, "PATCH": 3, "DELETE": 4}
    method_id = method_map.get(method.upper(), 5) / 5.0
    
    # Body length (normalized, assuming max ~10KB)
    body_len = min(len(body_sample or ""), 10000) / 10000.0
    
    # Non-alphanumeric ratio in body
    body_text = body_sample or ""
    if body_text:
        nonalpha_count = sum(1 for c in body_text if not c.isalnum() and not c.isspace())
        nonalpha_ratio = nonalpha_count / max(len(body_text), 1)
    else:
        nonalpha_ratio = 0.0
    
    # Hour of day (0-23, normalize to 0-1)
    if hour_of_day is None:
        hour_of_day = datetime.now().hour
    hour_norm = hour_of_day / 23.0
    
    # Recent RPS (normalize, assuming max 100 RPS)
    rps_norm = min(recent_rps, 100.0) / 100.0
    
    # Query string length
    query_len = min(len(query or ""), 1000) / 1000.0
    
    # Estimate header count (we don't have full headers, use method/path as proxy)
    # Simple heuristic: POST/PUT usually have more headers
    header_estimate = 1.0 if method.upper() in ["POST", "PUT", "PATCH"] else 0.5
    
    return [
        path_hash,
        method_id,
        body_len,
        nonalpha_ratio,
        hour_norm,
        rps_norm,
        query_len,
        header_estimate,
    ]


def get_path_hash(path: str) -> int:
    """Get consistent hash for path."""
    return abs(hash(path)) % 100000


def format_timestamp(ts: Optional[datetime] = None) -> str:
    """Format timestamp for storage."""
    if ts is None:
        ts = datetime.utcnow()
    return ts.isoformat()


def parse_timestamp(ts_str: str) -> datetime:
    """Parse timestamp from string."""
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

