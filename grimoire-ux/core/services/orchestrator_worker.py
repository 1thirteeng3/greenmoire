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
from core.api.trace_emitter import TraceEmitter

logger = logging.getLogger(__name__)


class OrchestratorWorker(BaseEventWorker):
    """
    Maestro Central do Grimoire.
    Implementa a Triade de Agentes (Planejador -> Executor -> Auditor),
    o Protocolo de Recuperacao e a emissão de telemetria em tempo real.
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

        # Instancia o emitter de telemetria para este trace específico
        tracer = TraceEmitter(bus=self.bus, trace_id=trace_id)

        # 1. Classificacao (Gatekeeper T1)
        await tracer.emit(
            agent="IntentClassifier",
            action="Analisando intenção e complexidade do prompt...",
            tier="T1",
        )
        intent = await self.classifier.classify_prompt(user_prompt)
        await tracer.emit(
            agent="IntentClassifier",
            action=f"Classificação concluída → Tier: {intent.tier} | Intent: {intent.primary_intent} | RAG: {intent.requires_memory}",
            tier="T1",
        )

        # 2. Recuperacao de memoria
        rag_context, conflict_report = None, None
        if intent.requires_memory:
            await tracer.emit(
                agent="ContextBuilder",
                action="Vetorizando prompt para busca semântica na memória...",
                tier="T2",
            )
            rag_context, conflict_report = await self._fetch_memories(
                user_prompt,
                intent.requires_memory,
                session,
            )
            if rag_context:
                await tracer.emit(
                    agent="ContextBuilder",
                    action=f"Memória recuperada: {len(rag_context.splitlines())} fragmentos relevantes encontrados.",
                    tier="T2",
                )
            if conflict_report and conflict_report.has_conflict:
                await tracer.emit(
                    agent="ConflictResolver",
                    action=f"⚠ Conflito de calibração detectado: {conflict_report.reason[:120]}...",
                    tier="T2",
                )

        response_text = ""
        audit_approved = True
        audit_critique = None

        # ==========================================
        # ROTA RAPIDA (T1 / T2)
        # ==========================================
        if intent.tier in ["T1", "T2"]:
            await tracer.emit(
                agent="ModelRouter",
                action=f"Rota Direta ({intent.tier}) — Execução single-shot sem agentes.",
                tier=intent.tier,
            )
            messages = self.builder.build_messages(user_prompt, rag_context, conflict_report)
            response_text = await self.router.execute_tier(intent.tier, messages)
            await tracer.emit(
                agent="ModelRouter",
                action="Resposta gerada. Entregando ao cliente.",
                tier=intent.tier,
            )

        # ==========================================
        # ROTA COMPLEXA: A TRIADE (T3)
        # ==========================================
        else:
            await tracer.emit(
                agent="OrchestratorWorker",
                action="Rota Complexa (T3) — Iniciando Tríade de Agentes.",
                tier="T3",
            )

            # A) Seleção de persona
            await tracer.emit(
                agent="AgentSelector",
                action=f"Selecionando perfil de agente para a intenção: '{intent.primary_intent}'...",
                tier="T3",
            )
            agent_profile = await self.selector.select_agent(intent.primary_intent)
            await tracer.emit(
                agent="AgentSelector",
                action=f"Agente selecionado: {agent_profile.name} | Ferramentas: {agent_profile.allowed_tools}",
                tier="T3",
            )

            # B) Planejamento
            await tracer.emit(
                agent="PlannerAgent",
                action="Decompondo solicitação em grafo de execução (DAG)...",
                tier="T3",
            )
            plan = await self.planner.generate_plan(
                user_prompt,
                rag_context or "",
                agent_profile.allowed_tools,
                agent_profile.role_description,
            )
            await tracer.emit_plan(
                plan_rationale=plan.plan_rationale,
                steps=plan.steps,
            )
            await tracer.emit(
                agent="PlannerAgent",
                action=f"Plano gerado com {len(plan.steps)} etapa(s). Fundamento: {plan.plan_rationale[:100]}",
                tier="T3",
            )

            # C) Execucao + Auditoria + Recuperacao (max 2 tentativas)
            max_retries = 2
            attempt = 0
            approved = False
            last_critique = None
            final_output = ""

            while attempt < max_retries and not approved:
                attempt += 1
                await tracer.emit(
                    agent="ExecutorAgent",
                    action=f"Iniciando execução das etapas do plano (Tentativa {attempt}/{max_retries})...",
                    tier="T3",
                )

                # Emitir atualizações de progresso por etapa
                for step in plan.steps:
                    await tracer.emit_step_update(step.step_id, "active")
                    await tracer.emit(
                        agent="ExecutorAgent",
                        action=f"Executando Etapa {step.step_id}: {step.action_description[:80]}",
                        tier="T3",
                    )

                final_output = await self.executor.execute_plan(
                    user_prompt=user_prompt,
                    plan=plan,
                    agent_profile=agent_profile,
                    rag_context=rag_context,
                    correction_directive=last_critique,
                )

                for step in plan.steps:
                    await tracer.emit_step_update(step.step_id, "completed")

                await tracer.emit(
                    agent="ExecutorAgent",
                    action="Execução concluída. Enviando para auditoria cruzada...",
                    tier="T3",
                )

                # D) Auditoria
                await tracer.emit(
                    agent="AuditorAgent",
                    action="Auditoria cruzada iniciada — verificando alucinações e conformidade...",
                    tier="T2",
                )
                audit_report = await self.auditor.audit_execution(
                    original_prompt=user_prompt,
                    executor_output=final_output,
                    executor_tier="T3",
                )

                if audit_report.approved:
                    await tracer.emit(
                        agent="AuditorAgent",
                        action="✓ Saída APROVADA — Sem alucinações detectadas.",
                        tier="T2",
                    )
                    approved = True
                    audit_approved = True
                    audit_critique = audit_report.critique
                else:
                    await tracer.emit(
                        agent="AuditorAgent",
                        action=f"✗ Saída REPROVADA — {audit_report.critique[:120]}. Iniciando recuperação...",
                        tier="T2",
                    )
                    last_critique = audit_report.critique
                    audit_approved = False
                    audit_critique = audit_report.critique

                    # Atualizar status dos steps para falha e reiniciar
                    for step in plan.steps:
                        await tracer.emit_step_update(step.step_id, "failed")

            # E) Protocolo de alucinacao: Dual Output View
            if not approved:
                await tracer.emit(
                    agent="OrchestratorWorker",
                    action=f"⚠ Protocolo DUAL OUTPUT ativado após {max_retries} tentativas falhadas.",
                    tier="T3",
                )
                response_text = (
                    "**ALERTA DE AUDITORIA COGNITIVA**\n"
                    "O sistema detectou uma potencial alucinação ou falha de conformidade que não pode ser auto-corrigida.\n\n"
                    "--- **SAIDA GERADA (NAO CONFIAVEL)** ---\n"
                    f"{final_output}\n\n"
                    "--- **RELATORIO DO AUDITOR** ---\n"
                    f"{last_critique}\n"
                    "----------------------------------------\n"
                    "*Ação Recomendada: Refine o prompt ou execute as etapas manualmente.*"
                )
            else:
                response_text = final_output

        # 3. Entrega da resposta
        await tracer.emit(
            agent="OrchestratorWorker",
            action="Ciclo cognitivo concluído. Entregando resposta ao cliente.",
        )

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
                "audit_approved": audit_approved,
                "audit_critique": audit_critique,
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
