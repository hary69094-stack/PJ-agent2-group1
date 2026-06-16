"""ShortTermAgent — agent with only a short-term sliding window memory.

Keeps the most recent N conversation turns; older turns are lost forever.
"""

from typing import Dict, List
from .base import BaseAgent


class ShortTermAgent(BaseAgent):
    """Agent mode B: short-term sliding window only."""

    def _build_system_prompt(self) -> str:
        return (
            "You are a helpful assistant. You remember the last few messages "
            "in this conversation, but you have no long-term memory. If the "
            "user asks about something that was said more than a few turns ago, "
            "you should honestly admit that you don't remember it."
        )

    def _build_messages(self, user_input: str) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]
        # Append the sliding window of recent turns
        window = self.memory.get_window()
        messages.extend(window)
        # Append the current user input
        messages.append({"role": "user", "content": user_input})
        return messages
