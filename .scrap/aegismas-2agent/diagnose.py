#!/usr/bin/env python3
"""Diagnostic script to check defender status"""
import requests
import sys

def check_service(name, url, expected_status=None):
    """Check if a service is responding."""
    try:
        response = requests.get(url, timeout=2)
        status = response.status_code
        
        # For Envoy, 404 might mean it's running but route doesn't exist (which is OK for health check)
        # For API, 200 is expected
        if expected_status:
            if status == expected_status:
                print(f"✅ {name}: OK (Status {status})")
                return True
            else:
                print(f"⚠️  {name}: Unexpected status {status} (expected {expected_status})")
                return False
        else:
            # Default: 200-299 is OK, 404 might be OK for some services
            if 200 <= status < 300:
                print(f"✅ {name}: OK (Status {status})")
                return True
            elif status == 404 and "envoy" in name.lower():
                print(f"⚠️  {name}: Responding but route not found (Status 404) - Envoy may need route config")
                return True  # Envoy is running, just route issue
            else:
                print(f"⚠️  {name}: Status {status}")
                return status < 500  # Not a server error
    except requests.exceptions.ConnectionError:
        print(f"❌ {name}: NOT RUNNING (Connection refused)")
        return False
    except requests.exceptions.Timeout:
        print(f"⚠️  {name}: TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {name}: ERROR - {e}")
        return False

def main():
    print("=" * 60)
    print("AegisMAS-2Agent Diagnostic Check")
    print("=" * 60)
    print()
    
    # Check services
    services_ok = True
    
    print("Checking Services:")
    print("-" * 60)
    services_ok &= check_service("AegisMAS API", "http://localhost:9000/health", expected_status=200)
    # Envoy doesn't have /health, test with a request that should go through
    services_ok &= check_service("Envoy Gateway", "http://localhost:8085/", expected_status=None)
    services_ok &= check_service("Bank (Origin)", "http://localhost:8000/health", expected_status=200)
    
    print()
    print("=" * 60)
    
    if services_ok:
        print("✅ All services are running!")
        print()
        print("Test the defender:")
        print("  python attack_simulator.py --defender on")
    else:
        print("❌ Some services are not running!")
        print()
        print("To start the defender:")
        print("  docker compose up -d")
        print()
        print("Wait 10 seconds, then check again:")
        print("  python diagnose.py")
        sys.exit(1)

if __name__ == "__main__":
    main()

