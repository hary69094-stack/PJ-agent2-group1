"""NoMemory — pass-through implementation, stores nothing."""

from typing import Dict, List, Optional
from .base import MemoryStore


class NoMemory(MemoryStore):
    """A memory store that does nothing. Every call returns empty results."""

    def add_turn(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        pass  # intentional no-op

    def retrieve_context(self, query: str) -> str:
        return ""

    def get_window(self) -> List[Dict[str, str]]:
        return []

    def reset(self) -> None:
        pass

    def snapshot(self) -> Dict:
        return {"type": "no_memory", "turns_stored": 0}
