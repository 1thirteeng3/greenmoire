import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.infrastructure.worker_base import BaseEventWorker
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.schemas.events import BaseEvent, EventHeader

from core.brain.intent_classifier import IntentClassifier
from core.brain.model_router import ModelRouter
from core.brain.context_builder import ContextBuilder
from core.brain.conflict_resolver import ConflictReport, ConflictResolver
from core.integrations.embedding_provider import EmbeddingProvider
from core.repositories.memory_repository import MemoryRepository

from core.agents.agent_selector import AgentSelector
from core.agents.planner_agent import PlannerAgent
from core.agents.executor_agent import ExecutorAgent
from core.agents.auditor_agent import AuditorAgent

logger = logging.getLogger(__name__)


class OrchestratorWorker(BaseEventWorker):
    """
    Maestro Central do Grimoire.
    Implementa a Triade de Agentes (Planejador -> Executor -> Auditor) e o Protocolo de Recuperacao.
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
        agent_selector: AgentSelector,
        planner_agent: PlannerAgent,
        executor_agent: ExecutorAgent,
        auditor_agent: AuditorAgent,
    ):
        super().__init__(bus, session_factory, "stream:user_input", "orchestrator_group", "orchestrator_1")
        self.classifier = intent_classifier
        self.router = model_router
        self.builder = context_builder
        self.conflict_resolver = conflict_resolver
        self.embedding_provider = embedding_provider
        self.selector = agent_selector
        self.planner = planner_agent
        self.executor = executor_agent
        self.auditor = auditor_agent

    async def start_service(self):
        logger.info("OrchestratorWorker (Maestro da Triade) Iniciado.")
        await self.start(self.handle_event)

    async def handle_event(self, event: BaseEvent, session: AsyncSession):
        if event.header.event_type == "user_prompt_received":
            await self._process_cognitive_cycle(event, session)

    async def _process_cognitive_cycle(self, event: BaseEvent, session: AsyncSession):
        user_prompt = event.payload.get("prompt")
        trace_id = event.header.trace_id
        reply_stream = event.metadata.get("reply_to_stream", "stream:frontend_output")

        if not user_prompt:
            raise ValueError("O payload do evento nao contem um 'prompt' valido.")

        # 1. Classificacao (Gatekeeper T1)
        intent = await self.classifier.classify_prompt(user_prompt)

        # 2. Recuperacao de memoria
        rag_context, conflict_report = await self._fetch_memories(
            user_prompt,
            intent.requires_memory,
            session,
        )

        response_text = ""

        # ==========================================
        # ROTA RAPIDA (T1 / T2)
        # ==========================================
        if intent.tier in ["T1", "T2"]:
            logger.info("[%s] Rota Direta (%s). Execucao single-shot.", trace_id, intent.tier)
            messages = self.builder.build_messages(user_prompt, rag_context, conflict_report)
            response_text = await self.router.execute_tier(intent.tier, messages)

        # ==========================================
        # ROTA COMPLEXA: A TRIADE (T3)
        # ==========================================
        else:
            logger.info("[%s] Rota Complexa (T3). Iniciando Triade de Agentes.", trace_id)

            # A) Seleção de persona
            agent_profile = await self.selector.select_agent(intent.primary_intent)

            # B) Planejamento
            plan = await self.planner.generate_plan(
                user_prompt,
                rag_context or "",
                agent_profile.allowed_tools,
            )

            # C) Execucao + Auditoria + Recuperacao (max 2 tentativas)
            max_retries = 2
            attempt = 0
            approved = False
            last_critique = None
            final_output = ""

            while attempt < max_retries and not approved:
                attempt += 1
                logger.info("[%s] T3 Execucao - Tentativa %s/%s", trace_id, attempt, max_retries)

                # O executor faz o trabalho
                final_output = await self.executor.execute_plan(
                    user_prompt=user_prompt,
                    plan=plan,
                    agent_profile=agent_profile,
                    rag_context=rag_context,
                    correction_directive=last_critique,
                )

                # O auditor (T2) valida o trabalho para evitar vies de confirmacao do T3
                audit_report = await self.auditor.audit_execution(user_prompt, final_output)

                if audit_report.approved:
                    logger.info("[%s] Saida APROVADA pelo Auditor.", trace_id)
                    approved = True
                else:
                    logger.warning("[%s] Saida REPROVADA. Motivo: %s", trace_id, audit_report.critique)
                    last_critique = audit_report.critique

            # D) Protocolo de alucinacao: Dual Output View
            if not approved:
                logger.error(
                    "[%s] Recuperacao falhou apos %s tentativas. Gerando Dual Output View.",
                    trace_id,
                    max_retries,
                )
                response_text = (
                    "**ALERTA DE AUDITORIA COGNITIVA**\n"
                    "O sistema detectou uma potencial alucinacao ou falha de conformidade que nao pode ser auto-corrigida.\n\n"
                    "--- **SAIDA GERADA (NAO CONFIAVEL)** ---\n"
                    f"{final_output}\n\n"
                    "--- **RELATORIO DO AUDITOR** ---\n"
                    f"{last_critique}\n"
                    "----------------------------------------\n"
                    "*Acao Recomendada: Refine o prompt ou execute as etapas manualmente.*"
                )
            else:
                response_text = final_output

        # 3. Entrega da resposta
        reply_event = BaseEvent(
            header=EventHeader(
                trace_id=trace_id,
                source_service="orchestrator",
                event_type="cognitive_response_delivered",
            ),
            payload={
                "response": response_text,
                "tier_used": intent.tier,
                "primary_intent": intent.primary_intent,
            },
        )
        await self.bus.publish(reply_stream, reply_event)

    async def _fetch_memories(
        self,
        prompt: str,
        requires_memory: bool,
        session: AsyncSession,
    ) -> tuple[Optional[str], Optional[ConflictReport]]:
        """Helper para extrair RAG e conflitos do banco de dados."""
        if not requires_memory:
            return None, None

        repository = MemoryRepository(session)
        embedding = await self.embedding_provider.generate_embedding(prompt)

        memories = await repository.search_semantic_memory(embedding, limit=5)
        rag_context = "\n".join([f"- {memory.content}" for memory, _ in memories]) if memories else None

        conflict = await self.conflict_resolver.evaluate_proposal(prompt, session)
        return rag_context, conflict
