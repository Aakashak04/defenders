"""
Simple Rule-Based Defender API
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict
import uvicorn

from .rules import check_rules
from .logger import init_db, log_event, get_events


# Initialize database
init_db()

app = FastAPI(
    title="Simple Rule-Based Defender",
    version="1.0.0",
)


class DecideRequest(BaseModel):
    method: str
    path: str
    query: str = ""
    headers: Dict[str, str] = {}
    body_sample: str = ""


@app.post("/v1/decide")
@app.post("/v1/decide/{path:path}")
async def decide(request: Request, path: str = ""):
    """
    Decision endpoint called by Envoy ext_authz.
    Extracts request details from Envoy headers and body.
    """
    # Extract from Envoy headers
    method = request.headers.get(":method") or request.method
    
    # Get path from header or URL
    path = request.headers.get(":path", "")
    if not path:
        # Try to extract from URL if Envoy sent it
        url_path = request.url.path
        if url_path.startswith("/v1/decide/"):
            path = url_path[11:]  # Remove /v1/decide prefix
        else:
            path = url_path or "/"
    
    # Get query string
    query = request.url.query
    if not query:
        # Try to extract from path if it contains query params
        if "?" in path:
            path, query = path.split("?", 1)
    
    # Get IP
    ip = request.headers.get("x-forwarded-for", "")
    if not ip and request.client:
        ip = request.client.host
    if not ip:
        ip = "127.0.0.1"
    else:
        ip = ip.split(",")[0].strip()
    
    # Get body sample
    try:
        raw_body = await request.body()
        body_sample = raw_body[:2048].decode(errors="ignore")
    except:
        body_sample = ""
    
    # Check rules
    is_malicious, rule_name = check_rules(method, path, query, body_sample)
    
    # Log event
    log_event(
        ip=ip,
        method=method,
        path=path,
        query=query,
        decision="block" if is_malicious else "allow",
        reason=rule_name or "rule_check_passed",
        body_sample=body_sample,
    )
    
    # Return decision
    if is_malicious:
        return JSONResponse(
            content={"action": "block", "reason": rule_name},
            status_code=403,
        )
    else:
        return JSONResponse(
            content={"action": "allow", "origin": "http://host.docker.internal:8000"},
            status_code=200,
        )


@app.get("/events")
def events(limit: int = 100, decision: Optional[str] = None):
    """Get logged events."""
    events_list = get_events(limit=limit, decision=decision)
    return {
        "events": events_list,
        "total": len(events_list),
    }


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("aegismas.main:app", host="0.0.0.0", port=8080, reload=True)

