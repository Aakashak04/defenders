#!/usr/bin/env python3
"""
Endpoint Discovery Script
Discovers accessible URLs/endpoints on localhost:8000
"""

import asyncio
import aiohttp
from typing import List, Dict, Set
import json

BASE_URL = "http://localhost:8000"

# Common endpoint patterns to try
COMMON_PATHS = [
    # Root and health
    "/",
    "/health",
    "/healthz",
    "/status",
    "/ping",
    "/api",
    "/api/health",
    
    # REST API patterns
    "/api/users",
    "/api/user",
    "/api/accounts",
    "/api/account",
    "/api/transactions",
    "/api/transaction",
    "/api/auth",
    "/api/login",
    "/api/logout",
    "/api/register",
    "/api/profile",
    "/api/balance",
    "/api/transfer",
    "/api/deposit",
    "/api/withdraw",
    
    # Admin endpoints
    "/admin",
    "/admin/users",
    "/admin/accounts",
    "/api/admin",
    
    # Documentation
    "/docs",
    "/swagger",
    "/swagger.json",
    "/openapi.json",
    "/api/docs",
    "/redoc",
    
    # Other common patterns
    "/v1",
    "/v1/health",
    "/v1/users",
    "/v1/accounts",
    "/version",
    "/info",
]


async def probe_endpoint(
    session: aiohttp.ClientSession,
    path: str,
    method: str = "GET"
) -> Dict:
    """Probe a single endpoint and return result."""
    url = f"{BASE_URL}{path}"
    
    try:
        async with session.request(
            method,
            url,
            timeout=aiohttp.ClientTimeout(total=3),
            allow_redirects=False,
        ) as resp:
            status = resp.status
            headers = dict(resp.headers)
            
            # Try to get response body
            try:
                if 'application/json' in headers.get('content-type', ''):
                    body = await resp.json()
                else:
                    body_text = await resp.text()
                    body = body_text[:500]  # Limit size
            except:
                body = None
            
            return {
                "path": path,
                "method": method,
                "status": status,
                "accessible": status < 500,
                "headers": {k: v for k, v in headers.items() if k.lower() in ['content-type', 'location', 'server']},
                "body_sample": str(body)[:200] if body else None,
            }
    except asyncio.TimeoutError:
        return {
            "path": path,
            "method": method,
            "status": "timeout",
            "accessible": False,
            "error": "Request timeout"
        }
    except aiohttp.ClientConnectorError:
        return {
            "path": path,
            "method": method,
            "status": "connection_error",
            "accessible": False,
            "error": "Connection refused - is the server running?"
        }
    except Exception as e:
        return {
            "path": path,
            "method": method,
            "status": "error",
            "accessible": False,
            "error": str(e)[:100]
        }


async def discover_from_docs(session: aiohttp.ClientSession) -> List[str]:
    """Try to discover endpoints from OpenAPI/Swagger docs."""
    doc_endpoints = [
        "/docs",
        "/swagger.json",
        "/openapi.json",
        "/api/docs",
        "/swagger",
    ]
    
    discovered = []
    
    for doc_path in doc_endpoints:
        try:
            async with session.get(
                f"{BASE_URL}{doc_path}",
                timeout=aiohttp.ClientTimeout(total=3)
            ) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        data = await resp.json()
                        # Try to extract paths from OpenAPI spec
                        if isinstance(data, dict):
                            paths = data.get('paths', {})
                            for path in paths.keys():
                                discovered.append(path)
        except:
            pass
    
    return list(set(discovered))


async def discover_endpoints():
    """Discover all accessible endpoints."""
    print("\n" + "=" * 80)
    print("🔍 ENDPOINT DISCOVERY - localhost:8000")
    print("=" * 80)
    print(f"Target: {BASE_URL}\n")
    
    accessible = []
    inaccessible = []
    errors = []
    
    async with aiohttp.ClientSession() as session:
        # First, try to get OpenAPI/Swagger docs
        print("📋 Checking for API documentation...")
        doc_paths = await discover_from_docs(session)
        if doc_paths:
            print(f"  ✅ Found {len(doc_paths)} endpoints from documentation:")
            for path in doc_paths[:10]:  # Show first 10
                print(f"     - {path}")
            if len(doc_paths) > 10:
                print(f"     ... and {len(doc_paths) - 10} more")
            print()
        
        # Probe common paths
        print(f"🔍 Probing {len(COMMON_PATHS)} common endpoints...\n")
        
        tasks = [probe_endpoint(session, path) for path in COMMON_PATHS]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if result.get("error"):
                errors.append(result)
            elif result.get("accessible"):
                accessible.append(result)
            else:
                inaccessible.append(result)
    
    # Display results
    print("=" * 80)
    print("📊 DISCOVERY RESULTS")
    print("=" * 80)
    
    if accessible:
        print(f"\n✅ ACCESSIBLE ENDPOINTS ({len(accessible)}):")
        print("-" * 80)
        for ep in accessible:
            status = ep['status']
            method = ep['method']
            path = ep['path']
            content_type = ep.get('headers', {}).get('content-type', 'N/A')
            print(f"  [{method}] {path:<40} Status: {status:<6} Type: {content_type}")
            if ep.get('body_sample'):
                sample = str(ep['body_sample'])[:60]
                print(f"    └─ Response: {sample}...")
    
    if inaccessible:
        print(f"\n❌ INACCESSIBLE/NOT FOUND ({len(inaccessible)}):")
        print("-" * 80)
        for ep in inaccessible[:10]:  # Show first 10
            status = ep.get('status', 'N/A')
            path = ep['path']
            print(f"  {path:<50} Status: {status}")
        if len(inaccessible) > 10:
            print(f"  ... and {len(inaccessible) - 10} more")
    
    if errors:
        print(f"\n⚠️  ERRORS ({len(errors)}):")
        print("-" * 80)
        for ep in errors:
            error = ep.get('error', 'Unknown error')
            path = ep['path']
            print(f"  {path:<50} Error: {error}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    print(f"Total probed: {len(COMMON_PATHS)}")
    print(f"✅ Accessible: {len(accessible)}")
    print(f"❌ Inaccessible: {len(inaccessible)}")
    print(f"⚠️  Errors: {len(errors)}")
    
    if doc_paths:
        print(f"📋 Found in docs: {len(doc_paths)}")
    
    # Save results to file
    output = {
        "base_url": BASE_URL,
        "accessible": accessible,
        "discovered_from_docs": doc_paths,
        "summary": {
            "total_probed": len(COMMON_PATHS),
            "accessible": len(accessible),
            "inaccessible": len(inaccessible),
            "errors": len(errors),
        }
    }
    
    with open("discovered_endpoints.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Results saved to: discovered_endpoints.json")
    print("=" * 80 + "\n")
    
    return accessible


if __name__ == "__main__":
    try:
        asyncio.run(discover_endpoints())
    except KeyboardInterrupt:
        print("\n\n⚠️  Discovery interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")


