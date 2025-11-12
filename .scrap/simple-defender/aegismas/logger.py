"""
Simple event logger - stores to SQLite
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import os

DB_PATH = "/app/events.db"


def init_db():
    """Initialize SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ip TEXT,
            method TEXT,
            path TEXT,
            query TEXT,
            decision TEXT,
            reason TEXT,
            body_sample TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_event(
    ip: str,
    method: str,
    path: str,
    query: str,
    decision: str,
    reason: str,
    body_sample: str = "",
):
    """Log an event to database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO events (timestamp, ip, method, path, query, decision, reason, body_sample)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        ip,
        method,
        path,
        query,
        decision,
        reason,
        body_sample[:200],  # Limit body sample
    ))
    conn.commit()
    conn.close()


def get_events(limit: int = 100, decision: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get events from database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if decision:
        cursor.execute("""
            SELECT * FROM events 
            WHERE decision = ?
            ORDER BY id DESC 
            LIMIT ?
        """, (decision, limit))
    else:
        cursor.execute("""
            SELECT * FROM events 
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

