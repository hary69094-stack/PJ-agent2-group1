"""Abstract MemoryStore interface — the critical abstraction for all three agent modes."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class MemoryStore(ABC):
    """Abstract interface for all memory backends.

    Three concrete implementations provide the three evaluation modes:
    - NoMemory:         passthrough, stores nothing
    - ShortTermMemory:  fixed-size sliding window deque
    - LongTermMemory:   ShortTermMemory + FAISS vector store
    """

    @abstractmethod
    def add_turn(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Store one conversation turn (role = 'user' or 'assistant')."""
        ...

    @abstractmethod
    def retrieve_context(self, query: str) -> str:
        """Return a formatted string to inject into the LLM prompt as context.
        May be empty (for NoMemory/ShortTermMemory).
        """
        ...

    @abstractmethod
    def get_window(self) -> List[Dict[str, str]]:
        """Return only the raw short-term messages as [{'role':..., 'content':...}, ...]."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Clear all memory state (for fresh conversation start)."""
        ...

    @abstractmethod
    def snapshot(self) -> Dict:
        """Export memory state for logging/inspection."""
        ...
