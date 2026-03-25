import os
import logging
from typing import List, Dict, Any
# Pressupõe a instalação da biblioteca: pip install mem0ai
from mem0 import Memory

logger = logging.getLogger(__name__)


class Mem0Wrapper:
    """
    Fachada para a biblioteca mem0.
    Configurada para utilizar o Postgres local como backend vetorial,
    garantindo que os dados não vazem para a cloud da mem0.
    """

    def __init__(self):
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://grimoire_admin:grimoire_secure_password@localhost:5432/grimoire_core",
        )

        config = {
            "vector_store": {
                "provider": "postgres",
                "config": {
                    "url": db_url,
                    "collection_name": "mem0_semantic_fallback",
                },
            }
        }
        try:
            self.memory_client = Memory.from_config(config)
            logger.info("Mem0 Wrapper inicializado com backend Postgres.")
        except Exception as e:
            logger.error(f"Falha ao inicializar mem0: {e}")
            self.memory_client = None

    def add_memory(self, text: str, user_id: str = "grimoire_user", metadata: Dict[str, Any] = None):
        """Encapsula a adição de memória garantindo tratamento de erros."""
        if not self.memory_client:
            raise RuntimeError("Cliente mem0 não está operacional.")
        return self.memory_client.add(text, user_id=user_id, metadata=metadata)

    def search_memory(self, query: str, user_id: str = "grimoire_user") -> List[Dict]:
        if not self.memory_client:
            raise RuntimeError("Cliente mem0 não está operacional.")
        return self.memory_client.search(query, user_id=user_id)
