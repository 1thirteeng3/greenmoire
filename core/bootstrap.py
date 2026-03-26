import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Infraestrutura e Integrações
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.integrations.embedding_provider import EmbeddingProvider
from core.integrations.llm_provider import LLMProvider
from core.integrations.firecrawl_provider import FirecrawlProvider

# Brain (Core Cognitivo)
from core.brain.tier_engine import TierEngine
from core.brain.model_router import ModelRouter
from core.brain.intent_classifier import IntentClassifier
from core.brain.context_builder import ContextBuilder
from core.brain.conflict_resolver import ConflictResolver

# Agentes e Ferramentas
from core.agents.tool_registry import ToolRegistry
from core.agents.agent_selector import AgentSelector
from core.agents.planner_agent import PlannerAgent
from core.agents.executor_agent import ExecutorAgent
from core.agents.auditor_agent import AuditorAgent

# Workers
from core.services.orchestrator_worker import OrchestratorWorker

logger = logging.getLogger(__name__)


class ApplicationContainer:
    """
    Conteiner de Injecao de Dependencias (DI).
    Instancia o grafo de objetos na ordem estrita de dependencia.
    """

    def __init__(self, bus: AsyncRedisEventBus, session_factory: async_sessionmaker[AsyncSession]):
        logger.info("Iniciando Bootstrap da Aplicacao (Dependency Wiring)...")

        # Nivel 0: Provedores Externos
        self.embedding_provider = EmbeddingProvider()
        self.llm_provider = LLMProvider()
        self.firecrawl_provider = FirecrawlProvider()

        # Nivel 1: Motores Base
        self.tier_engine = TierEngine()
        self.model_router = ModelRouter(self.llm_provider, self.tier_engine)
        self.context_builder = ContextBuilder()
        # ConflictResolver agora é agnóstico e usa o ModelRouter.
        self.conflict_resolver = ConflictResolver(self.embedding_provider, self.model_router)

        # Nivel 2: Ferramentas e Agentes
        self.tool_registry = ToolRegistry(self.firecrawl_provider)
        self.agent_selector = AgentSelector(self.embedding_provider)
        self.intent_classifier = IntentClassifier(self.model_router)
        self.planner_agent = PlannerAgent(self.model_router)
        self.executor_agent = ExecutorAgent(self.model_router, self.tool_registry)
        self.auditor_agent = AuditorAgent(self.model_router, self.tier_engine)

        # Nivel 3: Orquestracao (O Maestro)
        self.orchestrator_worker = OrchestratorWorker(
            bus=bus,
            session_factory=session_factory,
            intent_classifier=self.intent_classifier,
            model_router=self.model_router,
            context_builder=self.context_builder,
            conflict_resolver=self.conflict_resolver,
            embedding_provider=self.embedding_provider,
            agent_selector=self.agent_selector,
            planner_agent=self.planner_agent,
            executor_agent=self.executor_agent,
            auditor_agent=self.auditor_agent,
        )
        logger.info("Grafo de dependencias resolvido e instanciado com sucesso.")

    async def start_all_workers(self):
        """Inicializa as rotinas assincronas dos workers registrados."""
        logger.info("Dando boot nos daemons do sistema...")
        await self.orchestrator_worker.start_service()
