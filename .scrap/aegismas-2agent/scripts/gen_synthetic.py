#!/usr/bin/env python3
"""
Generate synthetic training data for LSTM and Statistical agents
"""
import json
import random
from datetime import datetime
from pathlib import Path

# SQLi patterns
SQLI_PATTERNS = [
    "1' OR '1'='1",
    "1' UNION SELECT NULL, username, password FROM users--",
    "admin' OR '1'='1'--",
    "1'; DROP TABLE users--",
]

# Path traversal
PATH_TRAVERSAL = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32",
]

# Normal paths
NORMAL_PATHS = [
    "/health",
    "/api/accounts",
    "/api/transactions",
    "/auth/login",
    "/auth/register",
    "/dashboard",
]

# Normal methods
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


def generate_benign_sample():
    """Generate a benign request sample."""
    method = random.choice(METHODS)
    path = random.choice(NORMAL_PATHS)
    body_len = random.randint(0, 500)
    body = "x" * body_len if body_len > 0 else ""
    
    return {
        "method": method,
        "path": path,
        "body_sample": body,
        "query": "",
        "malicious": False,
    }


def generate_malicious_sample():
    """Generate a malicious request sample."""
    method = random.choice(["GET", "POST"])
    
    # 70% SQLi, 20% path traversal, 10% other
    attack_type = random.choices(
        ["sqli", "path_traversal", "rce"],
        weights=[0.7, 0.2, 0.1],
    )[0]
    
    if attack_type == "sqli":
        path = "/api/users"
        query = f"?id={random.choice(SQLI_PATTERNS)}"
        body = ""
    elif attack_type == "path_traversal":
        path = f"/files/{random.choice(PATH_TRAVERSAL)}"
        query = ""
        body = ""
    else:  # rce
        path = "/api/execute"
        query = ""
        body = "; cat /etc/passwd"
    
    return {
        "method": method,
        "path": path,
        "body_sample": body,
        "query": query,
        "malicious": True,
    }


def main():
    """Generate synthetic dataset."""
    output_dir = Path("training_data")
    output_dir.mkdir(exist_ok=True)
    
    # Generate samples
    benign_samples = [generate_benign_sample() for _ in range(500)]
    malicious_samples = [generate_malicious_sample() for _ in range(200)]
    
    all_samples = benign_samples + malicious_samples
    random.shuffle(all_samples)
    
    # Save to JSON
    output_file = output_dir / "synthetic_dataset.json"
    with open(output_file, "w") as f:
        json.dump(all_samples, f, indent=2)
    
    print(f"Generated {len(benign_samples)} benign and {len(malicious_samples)} malicious samples")
    print(f"Saved to {output_file}")
    
    # Also save as CSV for easy inspection
    import csv
    csv_file = output_dir / "synthetic_dataset.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["method", "path", "body_sample", "query", "malicious"])
        writer.writeheader()
        writer.writerows(all_samples)
    
    print(f"Also saved to {csv_file}")


if __name__ == "__main__":
    main()

