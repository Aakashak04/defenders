# gateway/proxy.py
import asyncio
import time
from aiohttp import web, ClientSession
import json, os

DEFENDER_URL = os.getenv("DEFENDER_URL", "http://localhost:8080/v1/decide")
ORIGIN = os.getenv("ORIGIN", "http://localhost:8000")  # real bank

async def forward_request(request):
    # gather request info
    method = request.method
    path_q = request.rel_url.path
    query = str(request.rel_url.query) or ""
    headers = {k: v for k, v in request.headers.items() if k.lower() in ("user-agent", "referer", "content-type", "x-forwarded-for")}
    body = None
    try:
        body = await request.text()
    except:
        body = ""

    client_ip = request.remote or request.headers.get("X-Forwarded-For", "unknown")

    probe = {
        "ts": int(time.time()),
        "ip": client_ip,
        "method": method,
        "path": path_q,
        "query": query,
        "headers": headers,
        "body_sample": (body or "")[:1024]
    }

    async with ClientSession() as sess:
        try:
            async with sess.post(DEFENDER_URL, json=probe, timeout=2) as resp:
                d = await resp.json()
        except Exception as e:
            # Defender unreachable => fail-open (forward)
            print("Defender unreachable:", e)
            d = {"action": "allow", "origin": ORIGIN}

    action = d.get("action", "allow")
    if action == "block":
        status = d.get("status", 403)
        return web.json_response({"detail": "Blocked by Defender", "reason": d.get("reason")}, status=status)
    if action == "challenge":
        return web.json_response({"detail": "Challenge required"}, status=d.get("status", 429))

    # allowed -> forward to origin
    origin = d.get("origin", ORIGIN)
    forward_url = origin.rstrip("/") + path_q
    if query:
        forward_url += "?" + query

    # forward method and body, copy some headers
    fwd_headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    fwd_headers["X-Forwarded-For"] = probe["ip"]

    try:
        async with ClientSession() as sess:
            async with sess.request(method, forward_url, headers=fwd_headers, data=body, timeout=10) as upstream:
                text = await upstream.read()
                return web.Response(status=upstream.status, headers=dict(upstream.headers), body=text)
    except Exception as e:
        return web.json_response({"detail": "Upstream error", "error": str(e)}, status=502)

app = web.Application()
app.router.add_route('*', '/{tail:.*}', forward_request)

if __name__ == '__main__':
    web.run_app(app, port=8085)

