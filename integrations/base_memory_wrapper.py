from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseMemoryWrapper(ABC):
    @abstractmethod
    def add(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Adiciona uma nova memória e retorna o ID."""
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca memórias relevantes."""
        raise NotImplementedError
