"""
Coordinator - Merges agent scores and makes final decision
"""
from typing import Dict, Tuple, Optional
from datetime import datetime

from .config import config
from .agents.signature_agent import SignatureAgent
from .agents.stats_agent import StatsAgent
from .agents.lstm_agent import LSTMAgent


class Coordinator:
    """Coordinates multiple agents and makes final decision."""
    
    def __init__(self, redis_client=None):
        self.signature_agent = SignatureAgent()
        self.stats_agent = StatsAgent()
        self.lstm_agent = LSTMAgent(redis_client=redis_client)
    
    def decide(
        self,
        tenant: Optional[str],
        ip: str,
        method: str,
        path: str,
        query: str = "",
        headers: Dict[str, str] = None,
        body_sample: str = "",
        hour_of_day: Optional[int] = None,
        recent_rps: float = 0.0,
    ) -> Tuple[str, str, Dict[str, any]]:
        """
        Make final decision based on all agents.
        
        Returns:
            (action, reason, signals_dict)
            action: "allow" | "block" | "challenge"
        """
        signals = {}
        
        # 1. Signature Agent (fast, hard rules first)
        is_malicious, sig_signals = self.signature_agent.evaluate(
            method, path, query, headers, body_sample
        )
        signature_score = self.signature_agent.get_score(is_malicious)
        signals["signature"] = {
            "matched": is_malicious,
            "patterns": sig_signals,
        }
        
        # If signature matches, can return early (hard block)
        if is_malicious:
            return "block", f"signature:{list(sig_signals.keys())[0] if sig_signals else 'unknown'}", signals
        
        # 2. Statistical Agent
        stats_score, stats_signals = self.stats_agent.evaluate(
            method, path, body_sample, query, hour_of_day, recent_rps
        )
        signals["stats"] = stats_signals
        
        # 3. LSTM Agent
        lstm_score, lstm_signals = self.lstm_agent.evaluate(
            ip, method, path, body_sample, query, hour_of_day, recent_rps
        )
        signals["lstm"] = lstm_signals
        
        # 4. Combine scores (weighted)
        combined_score = (
            config.SIGNATURE_WEIGHT * signature_score +
            config.STATS_WEIGHT * stats_score +
            config.LSTM_WEIGHT * lstm_score
        )
        
        signals["combined_score"] = combined_score
        signals["scores"] = {
            "signature": signature_score,
            "stats": stats_score,
            "lstm": lstm_score,
        }
        
        # 5. Decision logic
        if combined_score >= config.BLOCK_THRESHOLD:
            action = "block"
            reason = f"high_risk:combined={combined_score:.3f}"
        elif combined_score >= config.CHALLENGE_THRESHOLD:
            action = "challenge"
            reason = f"elevated_risk:combined={combined_score:.3f}"
        else:
            action = "allow"
            reason = f"low_risk:combined={combined_score:.3f}"
        
        return action, reason, signals

