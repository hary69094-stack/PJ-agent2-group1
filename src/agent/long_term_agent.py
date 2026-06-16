"""LongTermAgent — agent with short-term window + long-term vector memory retrieval.

On every turn:
  1. The user input is embedded and used to search FAISS for relevant history.
  2. Retrieved chunks are injected as additional system-level context.
  3. The short-term window provides recent conversational flow.
  4. The LLM sees: [system] + [retrieved] + [window] + [current_user]
"""

from typing import Dict, List
from .base import BaseAgent


class LongTermAgent(BaseAgent):
    """Agent mode C: short-term window + long-term vector memory."""

    def _build_system_prompt(self) -> str:
        return (
            "You are a helpful assistant with access to your conversation history. "
            "Below the system message, you will receive:\n"
            "  1. 'Retrieved from memory:' — relevant facts from earlier in this "
            "conversation, retrieved by semantic search.\n"
            "  2. The recent conversation history (last several turns).\n"
            "  3. The user's current message.\n\n"
            "Guidelines:\n"
            "- Use retrieved information to give consistent, personalized answers.\n"
            "- If retrieved information contradicts what the user just said, trust "
            "the user's latest statement.\n"
            "- If you don't know something, say so honestly — don't fabricate."
        )

    def _build_messages(self, user_input: str) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]

        # Retrieve relevant long-term memory
        context = self.memory.retrieve_context(user_input)
        if context:
            messages.append({"role": "system", "content": context})

        # Append the short-term sliding window
        window = self.memory.get_window()
        messages.extend(window)

        # Append current user input
        messages.append({"role": "user", "content": user_input})

        return messages
