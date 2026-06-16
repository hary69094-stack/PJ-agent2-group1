"""NoMemoryAgent — agent without any history or memory.

Each turn is independent; the agent cannot recall any prior interaction.
"""

from typing import Dict, List
from .base import BaseAgent


class NoMemoryAgent(BaseAgent):
    """Agent mode A: no memory at all.

    Every respond() call sends only [system_prompt, user_input] to the LLM.
    """

    def _build_system_prompt(self) -> str:
        return (
            "You are a helpful assistant. You have NO memory of any previous "
            "conversation. Answer each message as if it were the first time "
            "you are talking to this user. Do not pretend to remember things "
            "that were not said in the current message."
        )

    def _build_messages(self, user_input: str) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]
