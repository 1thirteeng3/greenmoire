import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.brain.ingestion_utils import chunk_document, extract_and_enrich_pdf
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.infrastructure.worker_base import BaseEventWorker
from core.integrations.firecrawl_provider import FirecrawlProvider
from core.integrations.opendataloader_provider import OpenDataLoaderProvider
from core.integrations.vlm_provider import VLMProvider
from core.models.memory_models import IngestionStatus, IngestionTask
from core.schemas.events import BaseEvent, EventHeader

logger = logging.getLogger(__name__)


class IngestionWorker(BaseEventWorker):
    def __init__(
        self,
        bus: AsyncRedisEventBus,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        super().__init__(
            bus,
            session_factory,
            "stream:ingestion",
            "ingestion_group",
            "ingestion_worker_1",
        )
        self.vlm_provider = VLMProvider()
        self.pdf_provider = OpenDataLoaderProvider()
        self.firecrawl_provider = FirecrawlProvider()

    async def start_service(self) -> None:
        logger.info("Inicializando IngestionWorker...")
        await self.start(self.handle_event)

    async def handle_event(self, event: BaseEvent, session: AsyncSession) -> None:
        if event.header.event_type == "ingestion_requested":
            await self._process_ingestion(event, session)

    async def _process_ingestion(self, event: BaseEvent, session: AsyncSession):
        task_id_str = event.payload.get("task_id")
        target_uri = event.payload.get("file_path") or event.payload.get(
            "url"
        )  # Aceita path ou URL
        domain = event.payload.get("domain", "general_knowledge")
        source_type = event.payload.get("source_type")  # 'pdf' ou 'web'
        mode = event.payload.get("mode", "scrape")  # 'scrape' ou 'crawl'
        if not target_uri or not isinstance(target_uri, str):
            raise ValueError(f"target_uri inválido: {target_uri}")

        stmt = select(IngestionTask).where(IngestionTask.id == task_id_str)
        task = (await session.execute(stmt)).scalar_one_or_none()
        if not task:
            raise ValueError(f"IngestionTask {task_id_str} não encontrada.")

        try:
            task.status = IngestionStatus.DOWNLOADED
            await session.commit()

            documents_to_chunk = []  # Lista de (texto_bruto, url_fonte)

            # --- ROTEAMENTO DE EXTRAÇÃO ---
            if source_type == "pdf":
                logger.info(f"Iniciando extração PDF: {target_uri}")
                raw_text = await extract_and_enrich_pdf(
                    target_uri, self.vlm_provider, self.pdf_provider
                )
                documents_to_chunk.append((raw_text, target_uri))

            elif source_type == "web":
                if mode == "crawl":
                    logger.info(f"Iniciando Web Crawl em lote: {target_uri}")
                    pages = await self.firecrawl_provider.crawl_website(target_uri)
                    for page in pages:
                        documents_to_chunk.append(
                            (page["markdown"], page["source_url"])
                        )
                else:
                    logger.info(f"Iniciando Web Scrape singular: {target_uri}")
                    page = await self.firecrawl_provider.scrape_url(target_uri)
                    documents_to_chunk.append((page["markdown"], page["source_url"]))
            else:
                raise ValueError(f"source_type desconhecido: {source_type}")

            task.status = IngestionStatus.CHUNKED
            await session.commit()

            # --- FRAGMENTAÇÃO E ENVIO PARA MEMÓRIA ---
            total_chunks_sent = 0
            for raw_text, source_url in documents_to_chunk:
                chunks = await chunk_document(raw_text)

                for idx, chunk_text in enumerate(chunks):
                    store_event = BaseEvent(
                        header=EventHeader(
                            trace_id=event.header.trace_id,
                            source_service="ingestion_worker",
                            event_type="semantic_memory_store",
                        ),
                        payload={
                            "content": chunk_text,
                            "domain": domain,
                            "metadata": {
                                "source_uri": source_url,
                                "chunk_index": idx,
                                "total_chunks": len(chunks),
                            },
                            "human_verified": False,
                        },
                    )
                    await self.bus.publish("stream:memory", store_event)
                    total_chunks_sent += 1

            task.status = IngestionStatus.COMPLETED
            logger.info(
                f"Ingestão concluída. {total_chunks_sent} chunks enviados para vetorização "
                f"a partir de {len(documents_to_chunk)} documento(s)."
            )

        except Exception as e:
            task.status = IngestionStatus.FAILED
            task.error_log = str(e)
            logger.error(f"Falha no pipeline de ingestão: {e}")
            raise
