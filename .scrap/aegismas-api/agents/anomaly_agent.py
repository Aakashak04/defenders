import time
from typing import Dict, Tuple
import redis


class AnomalyAgent:
	def __init__(self, redis_client: redis.Redis, window_seconds: int = 60, spike_threshold: int = 100):
		self.redis = redis_client
		self.window = window_seconds
		self.threshold = spike_threshold

	def evaluate(self, tenant: str, ip: str, path: str) -> Tuple[float, Dict[str, str]]:
		score = 0.0
		signals: Dict[str, str] = {}

		now = int(time.time())
		key = f"anomaly:{tenant}:{ip}:{now // self.window}"
		try:
			count = self.redis.incr(key)
			self.redis.expire(key, self.window * 2)
		except Exception:
			# Fail-open on Redis issues; do not penalize
			count = 1

		if count > self.threshold:
			score += 0.6
			signals["rate_spike"] = f"{count} in {self.window}s"
		elif count > self.threshold // 2:
			score += 0.3
			signals["rate_elevated"] = f"{count} in {self.window}s"

		# Path entropy proxy: very long paths are suspicious
		if len(path) > 200:
			score += 0.2
			signals["long_path"] = str(len(path))

		return min(score, 1.0), signals





