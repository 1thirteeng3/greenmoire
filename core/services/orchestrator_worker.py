import asyncio
import logging
from typing import Any, Dict, List

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

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Pesquisa na web por informacoes em tempo real.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Termo de busca"}},
                "required": ["query"],
            },
        },
    }
]


class OrchestratorWorker(BaseEventWorker):
    """
    Cerebro Central do Grimoire.
    Implementa Roteamento Simples (T1/T2) e padrao ReAct nativo para T3.
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
    ):
        super().__init__(bus, session_factory, "stream:user_input", "orchestrator_group", "orchestrator_1")
        self.classifier = intent_classifier
        self.router = model_router
        self.builder = context_builder
        self.conflict_resolver = conflict_resolver
        self.embedding_provider = embedding_provider

    async def start_service(self):
        logger.info("OrchestratorWorker Iniciado. Aguardando input do usuario...")
        await self.start(self.handle_event)

    async def handle_event(self, event: BaseEvent, session: AsyncSession):
        if event.header.event_type == "user_prompt_received":
            await self._process_cognitive_cycle(event, session)

    async def _process_cognitive_cycle(self, event: BaseEvent, session: AsyncSession):
        user_prompt = event.payload.get("prompt")
        trace_id = event.header.trace_id
        reply_to_stream = event.metadata.get("reply_to_stream", "stream:frontend_output")

        if not user_prompt:
            raise ValueError("O payload do evento nao contem um 'prompt' valido.")

        logger.info(f"[Trace: {trace_id}] Analisando prompt: '{user_prompt[:50]}...'")

        # 1. Classificacao (Gatekeeper T1)
        intent = await self.classifier.classify_prompt(user_prompt)

        rag_context_text = None
        conflict_report = None

        # 2. Recuperacao de memoria RAG e erros (ativo para T2 e T3)
        if intent.requires_memory:
            logger.debug(f"[{intent.tier}] Recuperando contexto semantico e historico de erros.")
            repository = MemoryRepository(session)

            prompt_emb = await self.embedding_provider.generate_embedding(user_prompt)
            memories = await repository.search_semantic_memory(prompt_emb, limit=5)
            if memories:
                rag_context_text = "\n".join([f"- {mem.content}" for mem, _ in memories])

            conflict_report = await self.conflict_resolver.evaluate_proposal(user_prompt, session)

        # 3. Construcao da mente (contexto blindado)
        final_messages = self.builder.build_messages(
            user_prompt=user_prompt,
            rag_context=rag_context_text,
            conflict_report=conflict_report,
        )

        # 4. Execucao bifurcada (ReAct vs Direct)
        if intent.tier == "T3":
            logger.info(f"[{intent.tier}] Tarefa complexa. Iniciando loop ReAct...")
            response_text = await self._execute_react_loop(final_messages, trace_id)
        else:
            logger.info(f"[{intent.tier}] Tarefa analitica/direta. Execucao single-shot.")
            response_text = await self.router.execute_tier(tier=intent.tier, messages=final_messages)

        # 5. Entrega da resposta
        reply_event = BaseEvent(
            header=EventHeader(
                trace_id=trace_id,
                correlation_id=event.header.event_id,
                source_service="orchestrator",
                event_type="cognitive_response_delivered",
            ),
            payload={
                "response": response_text,
                "tier_used": intent.tier,
                "primary_intent": intent.primary_intent,
            },
        )
        await self.bus.publish(reply_to_stream, reply_event)

        # Opcional: logar a conversa na memoria episodica
        self._dispatch_episodic_log(user_prompt, response_text, trace_id)

    async def _execute_react_loop(
        self,
        messages: List[Dict[str, str]],
        trace_id: str,
        max_iterations: int = 5,
    ) -> str:
        """
        Loop ReAct nativo. O LLM pode chamar ferramentas multiplas vezes antes de responder.
        """
        iteration = 0
        current_messages: List[Dict[str, Any]] = list(messages)

        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"[Trace: {trace_id}] ReAct iteracao {iteration}/{max_iterations}")

            response_message = await self.router.execute_tier_with_tools(
                tier="T3",
                messages=current_messages,
                tools=AVAILABLE_TOOLS,
            )

            if isinstance(response_message, str) or not response_message.get("tool_calls"):
                content = response_message if isinstance(response_message, str) else response_message.get("content")
                return content or "Tarefa concluida (sem output textual)."

            first_call = response_message["tool_calls"][0]
            logger.info(f"[Trace: {trace_id}] LLM solicitou ferramenta: {first_call['function']['name']}")

            current_messages.append(
                {
                    "role": "assistant",
                    "tool_calls": response_message["tool_calls"],
                    "content": response_message.get("content", ""),
                }
            )

            # Placeholder ate a fase de ferramentas nativas.
            tool_result = "{'status': 'sucesso', 'dado': 'Resultado simulado da pesquisa web'}"

            current_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": first_call["id"],
                    "content": tool_result,
                }
            )

        logger.warning(f"[Trace: {trace_id}] ReAct atingiu max_iterations ({max_iterations}).")
        return "Desculpe, a tarefa exigiu mais passos do que o meu limite de processamento permite."

    def _dispatch_episodic_log(self, user_prompt: str, system_response: str, trace_id: str):
        log_event = BaseEvent(
            header=EventHeader(
                trace_id=trace_id,
                source_service="orchestrator",
                event_type="episodic_memory_store",
            ),
            payload={
                "trace_id": trace_id,
                "content": f"User: {user_prompt}\nSystem: {system_response}",
                "participants": ["user", "grimoire"],
            },
        )
        asyncio.create_task(self.bus.publish("stream:memory", log_event))
