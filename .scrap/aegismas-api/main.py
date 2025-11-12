from typing import Any, Dict, Optional, Tuple
import json
import os
import time
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
import redis

from agents.coordinator import Coordinator


class DecisionResponse(BaseModel):
	action: str  # allow | block | challenge
	reason: str
	origin: str
	tenant: str


def load_tenants(tenants_path: str) -> Dict[str, Dict[str, Any]]:
	with open(tenants_path, "r", encoding="utf-8") as f:
		return json.load(f)


def extract_tenant_from_host(host: str) -> Optional[str]:
	# host may contain port; split and use first label as tenant (prefix until first dot)
	host_only = host.split(":")[0]
	# Handle localhost - default to "bank" tenant
	if host_only == "localhost" or host_only == "127.0.0.1":
		return "bank"
	parts = host_only.split(".")
	if not parts:
		return None
	return parts[0] if parts[0] else None


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TENANTS_FILE = os.getenv("TENANTS_FILE", os.path.join(os.getcwd(), "tenants.json"))
DEFAULT_POSTURE = os.getenv("AEGIS_POSTURE_DEFAULT", "fail-open")

rds = redis.Redis.from_url(REDIS_URL, decode_responses=True)
tenants = load_tenants(TENANTS_FILE)
coordinator = Coordinator(redis_client=rds, tenants=tenants, default_posture=DEFAULT_POSTURE)

app = FastAPI(title="AegisMAS Decision API", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, str]:
	return {"status": "ok", "time": str(int(time.time()))}


@app.post("/v1/decide")
async def decide(request: Request) -> Response:
	# This endpoint serves both Envoy ext_authz HTTP and direct JSON calls
	# Try to parse body for JSON; if not JSON, still operate using headers and path
	raw_body = await request.body()
	content_type = request.headers.get("content-type", "")

	try:
		body_json = await request.json()
	except Exception:
		body_json = None

	# Build normalized decision input
	method = request.headers.get(":method") or request.method
	path = request.headers.get(":path") or request.url.path
	authority = request.headers.get(":authority") or request.headers.get("host", "")
	ip = request.client.host if request.client else request.headers.get("x-forwarded-for", "")
	query_string = request.url.query
	headers = {k.lower(): v for k, v in request.headers.items()}
	body_sample = None
	if raw_body:
		# store a small sample to inspect; do not log entire bodies in production
		body_sample = raw_body[:512].decode(errors="ignore")

	# tenant resolution
	tenant = None
	if body_json and isinstance(body_json, dict):
		tenant = body_json.get("tenant")
	if not tenant:
		tenant = extract_tenant_from_host(authority or headers.get("host", ""))

	decision, reason, origin_url, cluster_name = coordinator.decide(
		tenant=tenant,
		ip=ip,
		method=method,
		path=path,
		query=query_string,
		headers=headers,
		body_sample=body_sample or "",
	)

	# Prepare headers for upstream (Envoy ext_authz will pass these if allowed)
	upstream_headers = {
		"x-aegis-tenant": tenant or "",
		"x-aegis-origin": cluster_name or "",  # used by Envoy cluster_header
		"x-aegis-origin-url": origin_url or "",
	}

	decision_payload = DecisionResponse(
		action=decision, reason=reason, origin=origin_url or "", tenant=tenant or ""
	).model_dump()

	# Map decision to HTTP semantics for Envoy ext_authz:
	# allow -> 200; block -> 403; challenge -> 429
	if decision == "allow":
		return JSONResponse(content=decision_payload, status_code=200, headers=upstream_headers)
	if decision == "challenge":
		return JSONResponse(content=decision_payload, status_code=429, headers=upstream_headers)
	# default block
	return JSONResponse(content=decision_payload, status_code=403, headers=upstream_headers)




