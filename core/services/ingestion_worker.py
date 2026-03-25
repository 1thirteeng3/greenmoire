import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.brain.ingestion_utils import chunk_document, extract_and_enrich_pdf
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.infrastructure.worker_base import BaseEventWorker
from core.integrations.vlm_provider import VLMProvider
from core.schemas.events import BaseEvent

logger = logging.getLogger(__name__)


class IngestionWorker(BaseEventWorker):
    def __init__(
        self,
        bus: AsyncRedisEventBus,
        session_factory: async_sessionmaker[AsyncSession],
        vlm_provider: VLMProvider,
        stream_name: str = "stream:ingestion",
        group_name: str = "ingestion_group",
        consumer_name: str = "ingestion_worker_1",
    ):
        super().__init__(bus, session_factory, stream_name, group_name, consumer_name)
        self.vlm_provider = vlm_provider

    async def start_service(self) -> None:
        logger.info("Inicializando IngestionWorker...")
        await self.start(self.handle_event)

    async def handle_event(self, event: BaseEvent, session: AsyncSession) -> None:
        event_type = event.header.event_type
        if event_type != "ingestion_requested":
            logger.debug(f"IngestionWorker ignorou evento {event_type}.")
            return

        await self._process_ingestion(event.payload)

    async def _process_ingestion(self, payload: dict[str, Any]) -> None:
        file_path = payload.get("file_path")
        if not file_path:
            raise ValueError("Payload de ingestion_requested exige 'file_path'.")

        # 3. Extração Estrutural Enriquecida (Opendataloader + VLM)
        logger.info(f"Iniciando extração do ficheiro: {file_path}")
        raw_text = await extract_and_enrich_pdf(file_path, self.vlm_provider)

        max_tokens = int(payload.get("max_tokens", 400))
        chunks = await chunk_document(raw_text, max_tokens=max_tokens)
        logger.info(f"Ingestão processada: {len(chunks)} chunks gerados para {file_path}.")
