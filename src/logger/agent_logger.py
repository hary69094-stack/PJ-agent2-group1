"""Structured logging for agent interactions.

Writes one JSON object per conversation turn to a JSONL file for later
analysis and verification.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Optional


class AgentLogger:
    """Structured JSON-lines logger for agent conversations."""

    def __init__(self, log_file: str):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    def log_turn(
        self,
        test_id: str,
        agent_mode: str,
        turn: int,
        user_input: str,
        llm_response: str,
        latency_ms: float,
        memory_snapshot: Dict,
        retrieved_context: Optional[str] = None,
        full_messages: Optional[list] = None,
    ) -> None:
        """Log one conversation turn as a JSON line.

        Args:
            test_id: Identifier for the test case.
            agent_mode: 'no_memory', 'short_term', or 'long_term'.
            turn: Turn number (1-indexed).
            user_input: The user's message.
            llm_response: The agent's generated response.
            latency_ms: Response time in milliseconds.
            memory_snapshot: Dict from memory_store.snapshot().
            retrieved_context: The retrieved long-term context string (if any).
            full_messages: The full list of messages sent to the LLM.
        """
        record = {
            "test_id": test_id,
            "agent_mode": agent_mode,
            "turn": turn,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_input": user_input,
            "llm_response": llm_response,
            "latency_ms": round(latency_ms, 2),
            "retrieved_context": retrieved_context or "",
        }

        # Include memory snapshot summary (avoid full FAISS debug in base log)
        if memory_snapshot:
            record["memory_summary"] = self._summarize_snapshot(memory_snapshot)

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_evaluation(
        self,
        test_id: str,
        turn: int,
        trigger_type: str,
        result: Dict,
    ) -> None:
        """Log an evaluation trigger result."""
        record = {
            "test_id": test_id,
            "turn": turn,
            "trigger_type": trigger_type,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    @staticmethod
    def _summarize_snapshot(snapshot: Dict) -> Dict:
        """Create a compact summary of the memory snapshot."""
        mem_type = snapshot.get("type", "unknown")
        summary = {"type": mem_type}

        if mem_type == "short_term":
            summary["turns_stored"] = snapshot.get("turns_stored", 0)
        elif mem_type == "long_term":
            st = snapshot.get("short_term", {})
            faiss_data = snapshot.get("faiss", {})
            summary["st_turns"] = st.get("turns_stored", 0)
            summary["faiss_vectors"] = faiss_data.get("total_vectors", 0)
        elif mem_type == "no_memory":
            summary["turns_stored"] = 0

        return summary
