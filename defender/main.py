# defender/main.py
from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3, time, re, os
from typing import Optional

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
conn.execute("""
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
""")
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
        (ts, ip, method, path, query, reason, sample)
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

@app.post("/v1/decide")
async def decide(req: DecideRequest):
    ip = req.ip or "unknown"
    method = (req.method or "GET").upper()
    path = req.path or "/"
    query = req.query or ""
    body = req.body_sample or ""

    # Signatures first
    s = match_any(SQLI_PATTERNS, f"{path} {query} {body}")
    if s:
        log_event(ip, method, path, query, "sqli", body)
        return {"action": "block", "reason": "sqli", "status": 403}

    s = match_any(XSS_PATTERNS, f"{path} {query} {body}")
    if s:
        log_event(ip, method, path, query, "xss", body)
        return {"action": "block", "reason": "xss", "status": 403}

    s = match_any(TRAV_PATTERNS, f"{path} {query}")
    if s:
        log_event(ip, method, path, query, "traversal", body)
        return {"action": "block", "reason": "traversal", "status": 403}

    s = match_any(RCE_PATTERNS, f"{path} {query} {body}")
    if s:
        log_event(ip, method, path, query, "rce", body)
        return {"action": "block", "reason": "rce", "status": 403}

    # default allow
    return {"action": "allow", "origin": ORIGIN}

@app.get("/events")
def events(limit: int = 100):
    cur = conn.execute(
        "SELECT id, ts, ip, method, path, query, reason FROM events ORDER BY ts DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    out = []
    for r in rows:
        out.append({"id": r[0], "ts": r[1], "ip": r[2], "method": r[3], "path": r[4], "query": r[5], "reason": r[6]})
    return out

@app.get("/health")
def health():
    return {"status": "defender_ok"}

