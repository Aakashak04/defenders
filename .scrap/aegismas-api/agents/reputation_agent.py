from typing import Dict, Tuple
import redis


class ReputationAgent:
	def __init__(self, redis_client: redis.Redis):
		self.redis = redis_client
		self.blocklist_key = "reputation:blocklist"
		self.score_prefix = "reputation:ip:"

	def evaluate(self, ip: str) -> Tuple[float, Dict[str, str]]:
		score = 0.0
		signals: Dict[str, str] = {}

		try:
			if ip and self.redis.sismember(self.blocklist_key, ip):
				score = 1.0
				signals["blocklisted"] = "true"
				return score, signals
			if ip:
				val = self.redis.get(self.score_prefix + ip)
				if val is not None:
					try:
						numeric = float(val)
						score += min(max(numeric, 0.0), 1.0)
						signals["rep_score"] = str(numeric)
					except Exception:
						pass
		except Exception:
			# fail-open on Redis issues
			pass

		return min(score, 1.0), signals





