"""
Events Database - SQLite storage for security events
"""
import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime
from contextlib import contextmanager

from .config import config
from .utils import sanitize_body, format_timestamp


@contextmanager
def get_db_connection():
    """Get database connection with context manager."""
    # Ensure directory exists
    db_path = config.EVENTS_DB_PATH
    import os
    db_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else "."
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception:
            # If can't create directory, use current directory
            db_path = os.path.basename(db_path) or "events.db"
    
    # Try to connect, if fails use simple filename
    try:
        conn = sqlite3.connect(db_path)
    except Exception:
        # Fallback to simple filename in current directory
        db_path = "events.db"
        conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database schema."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                ip TEXT NOT NULL,
                path TEXT,
                method TEXT,
                body_sample_hash TEXT,
                agents_json TEXT,
                decision TEXT,
                forwarded BOOLEAN,
                tenant TEXT,
                reason TEXT
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ts ON events(ts)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ip ON events(ip)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_decision ON events(decision)
        """)


def store_event(
    ip: str,
    path: str,
    method: str,
    body_sample: str,
    agents_json: Dict,
    decision: str,
    forwarded: bool,
    tenant: Optional[str] = None,
    reason: str = "",
):
    """Store event in database."""
    # Sanitize body
    sanitized = sanitize_body(body_sample)
    body_hash = str(hash(sanitized)) if sanitized else None
    
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO events 
            (ts, ip, path, method, body_sample_hash, agents_json, decision, forwarded, tenant, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            format_timestamp(),
            ip,
            path,
            method,
            body_hash,
            json.dumps(agents_json),
            decision,
            forwarded,
            tenant,
            reason,
        ))


def get_events(
    limit: int = 100,
    offset: int = 0,
    ip: Optional[str] = None,
    decision: Optional[str] = None,
) -> List[Dict]:
    """Retrieve events from database."""
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    
    if ip:
        query += " AND ip = ?"
        params.append(ip)
    
    if decision:
        query += " AND decision = ?"
        params.append(decision)
    
    query += " ORDER BY ts DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    with get_db_connection() as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        events = []
        for row in rows:
            events.append({
                "id": row["id"],
                "ts": row["ts"],
                "ip": row["ip"],
                "path": row["path"],
                "method": row["method"],
                "body_sample_hash": row["body_sample_hash"],
                "agents_json": json.loads(row["agents_json"] or "{}"),
                "decision": row["decision"],
                "forwarded": bool(row["forwarded"]),
                "tenant": row["tenant"],
                "reason": row["reason"],
            })
        
        return events


def get_event_count(ip: Optional[str] = None, decision: Optional[str] = None) -> int:
    """Get total event count."""
    query = "SELECT COUNT(*) as count FROM events WHERE 1=1"
    params = []
    
    if ip:
        query += " AND ip = ?"
        params.append(ip)
    
    if decision:
        query += " AND decision = ?"
        params.append(decision)
    
    with get_db_connection() as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchone()["count"]

