from typing import Any, Dict, Optional, Tuple
import redis

from .signature_agent import SignatureAgent
from .anomaly_agent import AnomalyAgent
from .reputation_agent import ReputationAgent


class Coordinator:
	def __init__(self, redis_client: redis.Redis, tenants: Dict[str, Dict[str, Any]], default_posture: str = "fail-open"):
		self.redis = redis_client
		self.tenants = tenants
		self.default_posture = default_posture
		self.signature_agent = SignatureAgent()
		self.anomaly_agent = AnomalyAgent(redis_client)
		self.reputation_agent = ReputationAgent(redis_client)

	def select_origin(self, tenant: Optional[str]) -> Tuple[Optional[str], Optional[str], str]:
		# Returns origin_url, cluster_name, posture
		if tenant and tenant in self.tenants:
			conf = self.tenants[tenant]
			return conf.get("origin"), conf.get("cluster"), conf.get("posture", self.default_posture)
		return None, None, self.default_posture

	def decide(
		self,
		tenant: Optional[str],
		ip: str,
		method: str,
		path: str,
		query: str,
		headers: Dict[str, str],
		body_sample: str,
	) -> Tuple[str, str, Optional[str], Optional[str]]:
		origin_url, cluster_name, posture = self.select_origin(tenant)

		# Evaluate agents
		sig_score, sig_signals = self.signature_agent.evaluate(method, path, query, headers, body_sample)
		an_score, an_signals = self.anomaly_agent.evaluate(tenant or "unknown", ip or "unknown", path or "/")
		rep_score, rep_signals = self.reputation_agent.evaluate(ip or "")

		# Combine scores (simple max with tie-breaker)
		max_score = max(sig_score, an_score, rep_score)
		signals = {}
		signals.update(sig_signals)
		signals.update(an_signals)
		signals.update(rep_signals)

		# Policy
		if max_score >= 0.9 or "blocklisted" in signals:
			return "block", f"high_risk:{signals}", origin_url, cluster_name
		if max_score >= 0.6:
			return "challenge", f"elevated_risk:{signals}", origin_url, cluster_name

		# Safe
		# Fail-safe handling when origin unknown: respect posture
		if not origin_url or not cluster_name:
			if posture == "fail-closed":
				return "block", "unknown_tenant_fail_closed", origin_url, cluster_name
			return "allow", "unknown_tenant_fail_open", origin_url or "", cluster_name or ""

		return "allow", f"low_risk:{signals}", origin_url, cluster_name





