from typing import Any, Dict, List

from integrations.base_memory_wrapper import BaseMemoryWrapper


class OriMnemosWrapper(BaseMemoryWrapper):
    """
    Wrapper para memória episódica (linha do tempo / rastreabilidade cognitiva).
    """

    def __init__(self):
        self._store: list[dict[str, Any]] = []

    def add(self, content: str, metadata: Dict[str, Any] | None = None) -> str:
        entry_id = str(len(self._store) + 1)
        self._store.append({"id": entry_id, "content": content, "metadata": metadata or {}})
        return entry_id

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        matches = [entry for entry in self._store if query_lower in entry["content"].lower()]
        return matches[:limit]
