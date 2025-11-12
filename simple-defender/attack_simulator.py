"""
Simple attack simulator for testing defender
"""
import asyncio
import aiohttp
import sys
import argparse
from datetime import datetime


ATTACKS = [
    # SQL Injection
    ("GET", "/accounts?id=1 UNION SELECT * FROM users", None, "sqli"),
    ("GET", "/accounts?id=1' OR '1'='1", None, "sqli"),
    ("POST", "/login", '{"username":"admin","password":"1 OR 1=1"}', "sqli"),
    
    # XSS
    ("GET", "/search?q=<script>alert(1)</script>", None, "xss"),
    ("GET", "/profile?name=javascript:alert(1)", None, "xss"),
    
    # Path Traversal
    ("GET", "/files/../../../etc/passwd", None, "path_traversal"),
    ("GET", "/download?file=..%2F..%2Fetc%2Fpasswd", None, "path_traversal"),
    
    # RCE
    ("GET", "/exec?cmd=cat /etc/passwd", None, "rce"),
    ("GET", "/run?script=`whoami`", None, "rce"),
]


async def attack(session, url, method, path, body=None, attack_type=""):
    """Send attack request."""
    try:
        full_url = f"{url}{path}"
        if method == "GET":
            async with session.get(full_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                status = resp.status
                if status == 403:
                    return "blocked", attack_type
                elif status < 400:
                    return "allowed", attack_type
                else:
                    return "allowed", attack_type  # 4xx/5xx still means request reached server
        else:
            async with session.post(
                full_url,
                json=body if body else {},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                status = resp.status
                if status == 403:
                    return "blocked", attack_type
                elif status < 400:
                    return "allowed", attack_type
                else:
                    return "allowed", attack_type
    except Exception as e:
        return "error", str(e)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--defender", choices=["on", "off"], default="off")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    
    if args.defender == "on":
        target = "http://localhost:8085"
        print("=" * 80)
        print("🔴 ATTACK SIMULATOR - DEFENDER ON (via Envoy Gateway)")
        print("=" * 80)
    else:
        target = "http://localhost:8000"
        print("=" * 80)
        print("🟢 ATTACK SIMULATOR - DEFENDER OFF (Direct to Bank)")
        print("=" * 80)
    
    print(f"Target: {target}")
    print("=" * 80)
    print()
    
    async with aiohttp.ClientSession() as session:
        results = {"blocked": 0, "allowed": 0, "error": 0}
        
        for method, path, body, attack_type in ATTACKS:
            if not args.quiet:
                print(f"📌 {attack_type.upper()}: {method} {path}")
            
            result, _ = await attack(session, target, method, path, body, attack_type)
            results[result] = results.get(result, 0) + 1
            
            if not args.quiet:
                if result == "blocked":
                    print(f"   🛑 BLOCKED")
                elif result == "allowed":
                    print(f"   ✅ ALLOWED")
                else:
                    print(f"   ❌ ERROR")
        
        print()
        print("=" * 80)
        print("📊 ATTACK SUMMARY")
        print("=" * 80)
        total = sum(results.values())
        print(f"Total Attacks: {total}")
        print(f"  ✅ Allowed: {results.get('allowed', 0)} ({results.get('allowed', 0)/total*100:.1f}%)")
        print(f"  🛑 Blocked: {results.get('blocked', 0)} ({results.get('blocked', 0)/total*100:.1f}%)")
        print(f"  ❌ Errors: {results.get('error', 0)} ({results.get('error', 0)/total*100:.1f}%)")
        print("=" * 80)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

