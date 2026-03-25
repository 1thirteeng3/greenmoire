from typing import Any, Dict, List
import uuid

from integrations.base_memory_wrapper import BaseMemoryWrapper


class Mem0Wrapper(BaseMemoryWrapper):
    """
    Wrapper semântico para integração com mem0.
    Nesta fase, mantém uma implementação mínima e estável do contrato.
    """

    def __init__(self):
        self._store: list[dict[str, Any]] = []

    def add(self, content: str, metadata: Dict[str, Any] = None) -> str:
        memory_id = str(uuid.uuid4())
        self._store.append(
            {
                "id": memory_id,
                "content": content,
                "metadata": metadata or {},
            }
        )
        return memory_id

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        matches = [m for m in self._store if query_lower in m["content"].lower()]
        return matches[:limit]
