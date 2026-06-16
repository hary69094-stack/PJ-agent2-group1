"""ShortTermMemory — fixed-size sliding window using collections.deque."""

from collections import deque
from typing import Dict, List, Optional
from .base import MemoryStore


class ShortTermMemory(MemoryStore):
    """Fixed-size sliding window memory backed by a deque.

    Only the most recent `window_size` turns are retained. Older turns are
    silently evicted when the deque reaches capacity.
    """

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self._deque: deque[Dict[str, str]] = deque(maxlen=window_size)

    def add_turn(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        self._deque.append({"role": role, "content": content})

    def retrieve_context(self, query: str) -> str:
        # ShortTermMemory does not perform retrieval
        return ""

    def get_window(self) -> List[Dict[str, str]]:
        return list(self._deque)

    def reset(self) -> None:
        self._deque.clear()

    def snapshot(self) -> Dict:
        return {
            "type": "short_term",
            "window_size": self.window_size,
            "turns_stored": len(self._deque),
            "contents": list(self._deque),
        }
