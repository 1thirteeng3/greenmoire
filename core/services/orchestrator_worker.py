import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.infrastructure.worker_base import BaseEventWorker
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.schemas.events import BaseEvent, EventHeader

from core.brain.intent_classifier import IntentClassifier
from core.brain.model_router import ModelRouter
from core.brain.context_builder import ContextBuilder
from core.brain.conflict_resolver import ConflictResolver
from core.repositories.memory_repository import MemoryRepository
from core.integrations.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class OrchestratorWorker(BaseEventWorker):
    """
    O Cerebro Central do Grimoire.
    Coordena o ciclo cognitivo E2E: Escuta -> Classifica -> Recupera Contexto
    (RAG/Erros) -> Pensa (LLM) -> Responde.
    """

    def __init__(
        self,
        bus: AsyncRedisEventBus,
        session_factory: async_sessionmaker[AsyncSession],
        intent_classifier: IntentClassifier,
        model_router: ModelRouter,
        context_builder: ContextBuilder,
        conflict_resolver: ConflictResolver,
        embedding_provider: EmbeddingProvider,
        stream_name: str = "stream:user_input",
        group_name: str = "orchestrator_group",
        consumer_name: str = "orchestrator_1",
    ):
        super().__init__(bus, session_factory, stream_name, group_name, consumer_name)
        self.classifier = intent_classifier
        self.router = model_router
        self.builder = context_builder
        self.conflict_resolver = conflict_resolver
        self.embedding_provider = embedding_provider

    async def start_service(self):
        logger.info("OrchestratorWorker (Maestro) Inicializado. Aguardando interacoes do usuario...")
        await self.start(self.handle_event)

    async def handle_event(self, event: BaseEvent, session: AsyncSession):
        """Ponto de entrada unico para todas as requisicoes cognitivas."""
        if event.header.event_type == "user_prompt_received":
            await self._process_cognitive_cycle(event, session)
        else:
            logger.warning(f"Evento nao reconhecido no Orquestrador: {event.header.event_type}")

    async def _process_cognitive_cycle(self, event: BaseEvent, session: AsyncSession):
        user_prompt = event.payload.get("prompt")
        trace_id = event.header.trace_id
        reply_to_stream = event.metadata.get("reply_to_stream", "stream:frontend_output")

        if not user_prompt:
            raise ValueError("O payload do evento nao contem um 'prompt' valido.")

        logger.info(f"[Trace: {trace_id}] Iniciando Ciclo Cognitivo para: '{user_prompt[:50]}...'")

        # ---------------------------------------------------------
        # PASSO 1: CLASSIFICACAO DE INTENCAO (O Gatekeeper)
        # ---------------------------------------------------------
        intent = await self.classifier.classify_prompt(user_prompt)

        rag_context_text = None
        conflict_report = None

        # ---------------------------------------------------------
        # PASSO 2: RECUPERACAO DE CONTEXTO E CALIBRACAO (Se necessario)
        # ---------------------------------------------------------
        if intent.requires_memory:
            logger.debug(f"[{intent.tier}] Intencao requer memoria. Acionando MemoryRepository e ConflictResolver.")
            repository = MemoryRepository(session)

            # 2.1 Vetorizacao em tempo real do prompt do usuario
            prompt_embedding = await self.embedding_provider.generate_embedding(user_prompt)

            # 2.2 Busca na Memoria Semantica (RAG)
            memories = await repository.search_semantic_memory(prompt_embedding, limit=5)
            if memories:
                formatted_memories = [f"- {mem.content}" for mem, _score in memories]
                rag_context_text = "\n".join(formatted_memories)

            # 2.3 Avaliacao de Conflitos e Recuperacao de Erros de Calibracao
            conflict_report = await self.conflict_resolver.evaluate_proposal(user_prompt, session)

        # ---------------------------------------------------------
        # PASSO 3: MONTAGEM DA MENTE (Context Builder)
        # ---------------------------------------------------------
        final_messages = self.builder.build_messages(
            user_prompt=user_prompt,
            rag_context=rag_context_text,
            conflict_report=conflict_report,
        )

        # ---------------------------------------------------------
        # PASSO 4: EXECUCAO AGNOSTICA (Model Router)
        # ---------------------------------------------------------
        response_text = await self.router.execute_tier(
            tier=intent.tier,
            messages=final_messages,
        )

        logger.info(f"[Trace: {trace_id}] Ciclo Cognitivo concluido via {intent.tier}. Enviando resposta.")

        # ---------------------------------------------------------
        # PASSO 5: ENTREGA DO RESULTADO
        # ---------------------------------------------------------
        reply_event = BaseEvent(
            header=EventHeader(
                trace_id=trace_id,
                correlation_id=event.header.event_id,
                source_service="orchestrator_worker",
                event_type="cognitive_response_delivered",
            ),
            payload={
                "response": response_text,
                "tier_used": intent.tier,
                "primary_intent": intent.primary_intent,
            },
        )
        await self.bus.publish(reply_to_stream, reply_event)

        # Opcional: despacha um evento para o MemoryService gravar EpisodicMemory.
        self._dispatch_episodic_log(user_prompt, response_text, trace_id)

    def _dispatch_episodic_log(self, user_prompt: str, system_response: str, trace_id: str):
        """Dispara log assincrono (fire-and-forget) para nao bloquear o worker."""
        log_event = BaseEvent(
            header=EventHeader(
                trace_id=trace_id,
                source_service="orchestrator",
                event_type="episodic_memory_store",
            ),
            payload={
                "trace_id": trace_id,
                "content": f"User: {user_prompt}\nSystem: {system_response}",
                "participants": ["user", "grimoire_system"],
            },
        )

        # Cria a task assincrona no event loop atual
        import asyncio

        asyncio.create_task(self.bus.publish("stream:memory", log_event))
