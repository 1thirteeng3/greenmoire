import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.infrastructure.worker_base import BaseEventWorker
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.schemas.events import BaseEvent, EventHeader
from core.repositories.memory_repository import MemoryRepository
from core.integrations.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class MemoryServiceWorker(BaseEventWorker):
    def __init__(self, bus: AsyncRedisEventBus, session_factory: async_sessionmaker[AsyncSession], embedding_provider: EmbeddingProvider):
        super().__init__(bus, session_factory, stream_name="stream:memory", group_name="memory_service_group", consumer_name="memory_worker_1")
        self.embedding_provider = embedding_provider

    async def start_service(self):
        logger.info("MemoryService Daemon iniciado.")
        await self.start(self.handle_event)

    async def handle_event(self, event: BaseEvent, session: AsyncSession):
        repository = MemoryRepository(session)
        event_type = event.header.event_type
        payload = event.payload

        if event_type == "semantic_memory_store":
            embedding = await self.embedding_provider.generate_embedding(payload["content"])
            await repository.save_semantic_memory(
                content=payload["content"], embedding=embedding, domain=payload["domain"],
                metadata=payload.get("metadata", {}), human_verified=payload.get("human_verified", False)
            )
        elif event_type == "episodic_memory_store":
            await repository.save_episodic_event(
                trace_id=payload["trace_id"],
                content=payload["content"],
                participants=payload.get("participants", []),
                metadata=payload.get("metadata", {}),
            )
        elif event_type == "error_memory_log":
            error_embedding = await self.embedding_provider.generate_embedding(payload["original_output"])
            await repository.log_hallucination_or_error(
                original_output=payload["original_output"],
                human_correction=payload["human_correction"],
                embedding=error_embedding,
                metadata=payload.get("metadata", {}),
            )
        elif event_type == "semantic_memory_query":
            embedding = await self.embedding_provider.generate_embedding(payload["query"])
            results = await repository.search_semantic_memory(embedding, payload.get("domain"), payload.get("limit", 5))

            reply_event = BaseEvent(
                header=EventHeader(trace_id=event.header.trace_id, correlation_id=event.header.event_id, source_service="memory_service", event_type="semantic_memory_result"),
                payload={"results": [{"id": str(m.id), "content": m.content, "score": s} for m, s in results], "original_query": payload["query"]}
            )
            await self.bus.publish(event.metadata.get("reply_to_stream"), reply_event)
        else:
            raise ValueError(f"Evento não suportado: {event_type}")
