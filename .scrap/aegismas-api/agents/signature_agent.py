import re
from typing import Dict, Tuple


SQLI_REGEXES = [
	re.compile(r"(?i)(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b).*", re.S),
	re.compile(r"(?i)(\bor\b|\band\b)\s+1\s*=\s*1"),
	re.compile(r"(?i)('|\")\s*(or|and)\s*('|\")?\d+\s*=\s*\d+('|\")?"),
	re.compile(r"(?i)(--|#|/\*)"),
]

PATH_TRAVERSAL = re.compile(r"(\.\./|\.\.\\)")

RCE_PATTERNS = [
	re.compile(r"(?i)(;|\|\||&&)\s*(cat|ls|whoami|bash|sh|powershell)"),
	re.compile(r"(?i)\$\{.*\}"),  # simple SSTI-like
]


class SignatureAgent:
	def evaluate(self, method: str, path: str, query: str, headers: Dict[str, str], body_sample: str) -> Tuple[float, Dict[str, str]]:
		score = 0.0
		signals: Dict[str, str] = {}

		payload_space = " ".join([path or "", query or "", body_sample or ""])[:2000]

		# SQLi
		for rx in SQLI_REGEXES:
			if rx.search(payload_space):
				score += 0.6
				signals["sqli"] = "pattern_detected"
				break

		# Path traversal
		if PATH_TRAVERSAL.search(payload_space):
			score += 0.5
			signals["path_traversal"] = "dotdot_detected"

		# RCE-like
		for rx in RCE_PATTERNS:
			if rx.search(payload_space):
				score += 0.7
				signals["rce"] = "shell_injection_like"
				break

		# Basic method check
		if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
			score += 0.2
			signals["unknown_method"] = method

		return min(score, 1.0), signals





