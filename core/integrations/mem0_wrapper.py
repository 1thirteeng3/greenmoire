import os
import asyncio
import logging
from typing import List, Dict, Any

from mem0 import Memory

logger = logging.getLogger(__name__)


class Mem0Wrapper:
    """
    Fachada para a biblioteca mem0.
    Configurada para utilizar o Postgres local como backend vetorial,
    garantindo que os dados não vazem para a cloud da mem0.
    """

    def __init__(self):
        db_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://grimoire_admin:grimoire_secure_password@localhost:5432/grimoire_core")
        config = {
            "vector_store": {"provider": "postgres", "config": {"url": db_url, "collection_name": "mem0_fallback"}}
        }
        try:
            self.client = Memory.from_config(config)
        except Exception as e:
            logger.error(f"Falha de inicialização mem0: {e}")
            self.client = None

    async def store_async(self, text: str, trace_id: str, metadata: Dict[str, Any] = None) -> bool:
        """Envelopa a chamada síncrona numa thread para proteger o event loop."""
        if not self.client:
            return False

        meta = metadata or {}
        meta["trace_id"] = trace_id

        def _add():
            self.client.add(text, user_id="grimoire", metadata=meta)

        await asyncio.to_thread(_add)
        return True

    async def retrieve_async(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.client:
            return []

        def _search():
            return self.client.search(query, user_id="grimoire", limit=limit)

        return await asyncio.to_thread(_search)
