"""
Signature-based Agent - Fast regex pattern matching
"""
import re
from typing import Dict, Tuple, Optional


# SQL Injection patterns
SQLI_PATTERNS = [
    re.compile(r"(?i)(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b).*", re.S),
    re.compile(r"(?i)(\bor\b|\band\b)\s+1\s*=\s*1", re.I),
    re.compile(r"(?i)('|\")\s*(or|and)\s*('|\")?\d+\s*=\s*\d+('|\")?", re.I),
    re.compile(r"(?i)(--|#|/\*|\*/)", re.I),
    re.compile(r"(?i)(\bDROP\b|\bTRUNCATE\b|\bALTER\b)", re.I),
]

# Path Traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"(\.\./|\.\.\\)", re.I),
    re.compile(r"(\.\.%2F|\.\.%5C)", re.I),  # URL encoded
    re.compile(r"(\.\.%252F|\.\.%255C)", re.I),  # Double encoded
]

# Command Injection patterns
RCE_PATTERNS = [
    re.compile(r"(?i)(;|\|\||&&)\s*(cat|ls|whoami|bash|sh|powershell|cmd)", re.I),
    re.compile(r"(?i)\$\{.*\}", re.I),  # Template injection
    re.compile(r"(?i)(`.*`|\$\(.*\))", re.I),  # Command substitution
]

# XSS patterns (basic)
XSS_PATTERNS = [
    re.compile(r"(?i)<script[^>]*>", re.I),
    re.compile(r"(?i)javascript:", re.I),
    re.compile(r"(?i)onerror\s*=", re.I),
    re.compile(r"(?i)onclick\s*=", re.I),
]


class SignatureAgent:
    """Fast signature-based detection using regex patterns."""
    
    def __init__(self):
        self.patterns = {
            "sqli": SQLI_PATTERNS,
            "path_traversal": PATH_TRAVERSAL_PATTERNS,
            "rce": RCE_PATTERNS,
            "xss": XSS_PATTERNS,
        }
    
    def evaluate(
        self,
        method: str,
        path: str,
        query: str = "",
        headers: Optional[Dict[str, str]] = None,
        body_sample: str = "",
    ) -> Tuple[bool, Dict[str, str]]:
        """
        Evaluate request for signature matches.
        
        Returns:
            (is_malicious, signals_dict)
        """
        signals = {}
        is_malicious = False
        
        # Combine all input into search space
        search_space = " ".join([
            method or "",
            path or "",
            query or "",
            body_sample or "",
        ])[:5000]  # Limit search space
        
        # Check each pattern category
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(search_space):
                    signals[category] = pattern.pattern[:50]  # Store matched pattern
                    is_malicious = True
                    break  # One match per category is enough
            if is_malicious and category in signals:
                break  # Found malicious pattern, can return early
        
        return is_malicious, signals
    
    def get_score(self, is_malicious: bool) -> float:
        """Convert boolean to score (0.0 or 1.0)."""
        return 1.0 if is_malicious else 0.0

