"""
Simple rule-based detection patterns
"""
import re
from typing import Tuple, Optional


# Malicious patterns
SQLI_PATTERNS = [
    re.compile(r"(?i)(union\s+select|select\s+.*\s+from|insert\s+into|delete\s+from|drop\s+table)", re.I),
    re.compile(r"(?i)(exec\s*\(|execute\s*\()", re.I),
    re.compile(r"(?i)(or\s+1\s*=\s*1|and\s+1\s*=\s*1)", re.I),
    re.compile(r"(?i)('|\")\s*(or|and)\s*('|\")?\d+\s*=\s*\d+", re.I),
]

XSS_PATTERNS = [
    re.compile(r"(?i)<script[^>]*>", re.I),
    re.compile(r"(?i)javascript:", re.I),
    re.compile(r"(?i)(onerror|onload|onclick)\s*=", re.I),
]

PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"(\.\./|\.\.\\)", re.I),
    re.compile(r"(%2e%2e%2f|%2e%2e%5c)", re.I),
]

RCE_PATTERNS = [
    re.compile(r"(?i)(\|\||&&)\s*(cat|ls|whoami|bash|sh|powershell|cmd)", re.I),
    re.compile(r"(?i)(`.*`|\$\(.*\))", re.I),
    re.compile(r"(?i)(eval\s*\(|exec\s*\(|system\s*\()", re.I),
]


def check_rules(method: str, path: str, query: str, body_sample: str) -> Tuple[bool, Optional[str]]:
    """
    Check request against all rules.
    
    Returns:
        (is_malicious, rule_name)
    """
    # Combine all text to check
    text_to_check = f"{method} {path} {query} {body_sample}".lower()
    
    # Check SQLi
    for pattern in SQLI_PATTERNS:
        if pattern.search(text_to_check):
            return True, "sqli"
    
    # Check XSS
    for pattern in XSS_PATTERNS:
        if pattern.search(text_to_check):
            return True, "xss"
    
    # Check Path Traversal
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if pattern.search(text_to_check):
            return True, "path_traversal"
    
    # Check RCE
    for pattern in RCE_PATTERNS:
        if pattern.search(text_to_check):
            return True, "rce"
    
    return False, None

