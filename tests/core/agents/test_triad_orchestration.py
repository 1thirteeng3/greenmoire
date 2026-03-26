import json
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.agents.agent_models import AgentProfile
from core.agents.auditor_agent import AuditReport, AuditorAgent
from core.agents.executor_agent import ExecutorAgent
from core.agents.planner_agent import ExecutionPlan, PlannerAgent
from core.brain.tier_engine import TierEngine, TierPolicy
from core.services.orchestrator_worker import OrchestratorWorker


class MockTierEngine(TierEngine):
    """TierEngine deterministico para testes."""

    def get_policy(self, tier: str) -> TierPolicy:
        policies = {
            "T1": TierPolicy(
                tier_name="T1",
                provider="localai",
                model="llama-3",
                max_tokens=500,
                temperature=0.0,
                allows_tools=False,
                timeout_seconds=10,
            ),
            "T2": TierPolicy(
                tier_name="T2",
                provider="openai",
                model="gpt-4o-mini",
                max_tokens=1500,
                temperature=0.2,
                allows_tools=False,
                timeout_seconds=10,
            ),
            "T3": TierPolicy(
                tier_name="T3",
                provider="anthropic",
                model="claude-3-5",
                max_tokens=4000,
                temperature=0.3,
                allows_tools=True,
                timeout_seconds=10,
            ),
        }
        return policies.get(tier.upper(), policies["T2"])


class DegenerateTierEngine(TierEngine):
    """Mock onde todos os tiers usam o mesmo modelo."""

    def get_policy(self, tier: str) -> TierPolicy:
        return TierPolicy(
            tier_name=tier,
            provider="openai",
            model="gpt-4o",
            max_tokens=1000,
            temperature=0.0,
            allows_tools=True,
            timeout_seconds=10,
        )


class MockModelRouter:
    """Simula respostas do LLM para componentes isolados."""

    def __init__(self):
        self.execute_tier = AsyncMock(return_value="Mock response")
        self.execute_tier_with_tools = AsyncMock(return_value="Mock tool response")


class MockToolRegistry:
    def get_all_schemas(self):
        return [{"type": "function", "function": {"name": "dummy_tool", "parameters": {}}}]

    async def execute_tool(self, name, args):
        return json.dumps({"status": "success", "data": "dummy data"})


@pytest.mark.asyncio
async def test_planner_agent_generates_valid_plan():
    router = MockModelRouter()
    router.execute_tier.return_value = json.dumps(
        {
            "plan_rationale": "Dividir para conquistar.",
            "steps": [
                {
                    "step_id": 1,
                    "action_description": "Ler dados",
                    "required_tools": ["dummy_tool"],
                    "expected_outcome": "Dados carregados",
                    "dependencies": [],
                }
            ],
        }
    )

    planner = PlannerAgent(router)
    plan = await planner.generate_plan(
        "Faca X",
        context="",
        available_tools=["dummy_tool"],
        target_persona="Persona de teste",
    )

    assert isinstance(plan, ExecutionPlan)
    assert len(plan.steps) == 1
    assert plan.steps[0].action_description == "Ler dados"
    router.execute_tier.assert_called_once()


@pytest.mark.asyncio
async def test_auditor_agent_strict_routing():
    """Auditor nao deve usar o mesmo tier do executor quando houver alternativa."""
    router = MockModelRouter()
    engine = MockTierEngine()
    router.execute_tier.return_value = json.dumps({"approved": True, "critique": "OK"})

    auditor = AuditorAgent(router, engine)
    report = await auditor.audit_execution("Prompt", "Output", executor_tier="T3")

    assert report.approved is True
    called_tier = router.execute_tier.call_args.kwargs.get("tier")
    assert called_tier in ["T1", "T2"]
    assert called_tier != "T3"


@pytest.mark.asyncio
async def test_auditor_agent_degenerate_scenario_fallback(caplog):
    """
    Se todos os tiers tiverem a mesma assinatura, o Auditor aplica fallback
    e emite alerta critico de governanca.
    """
    router = MockModelRouter()
    degenerate_engine = DegenerateTierEngine()
    auditor = AuditorAgent(router, degenerate_engine)

    with caplog.at_level(logging.WARNING):
        fallback_tier = auditor._get_strict_auditor_tier(executor_tier="T3")

    assert fallback_tier == "T2"
    assert "ALERTA CRITICO DE GOVERNANCA" in caplog.text
    assert "assinatura de modelo" in caplog.text

    fallback_tier_alt = auditor._get_strict_auditor_tier(executor_tier="T2")
    assert fallback_tier_alt == "T3"


@pytest.mark.asyncio
async def test_orchestrator_recovery_protocol_and_dual_output():
    """
    Pior caso: Executor falha repetidamente, Auditor reprova e o sistema
    deve responder com Dual Output View sem loop infinito.
    """
    router = MockModelRouter()
    engine = MockTierEngine()
    tool_registry = MockToolRegistry()

    planner = PlannerAgent(router)
    executor = ExecutorAgent(router, tool_registry)
    auditor = AuditorAgent(router, engine)

    intent_classifier = AsyncMock()
    intent_classifier.classify_prompt.return_value = MagicMock(
        tier="T3",
        primary_intent="write",
        requires_memory=False,
    )

    agent_selector = AsyncMock()
    agent_selector.select_agent.return_value = AgentProfile(
        name="TestAgent",
        role_description="persona",
        allowed_tools=[],
        max_loops=1,
    )

    planner.generate_plan = AsyncMock(
        return_value=ExecutionPlan(
            plan_rationale="R",
            steps=[],
        )
    )
    executor.execute_plan = AsyncMock(return_value="Output ruim com alucinacao.")
    auditor.audit_execution = AsyncMock(
        return_value=AuditReport(approved=False, critique="Fato inventado sobre o projeto X.")
    )

    bus = AsyncMock()
    orchestrator = OrchestratorWorker(
        bus=bus,
        session_factory=MagicMock(),
        intent_classifier=intent_classifier,
        model_router=router,
        context_builder=MagicMock(),
        conflict_resolver=AsyncMock(),
        embedding_provider=AsyncMock(),
        agent_selector=agent_selector,
        planner_agent=planner,
        executor_agent=executor,
        auditor_agent=auditor,
    )

    mock_event = MagicMock()
    mock_event.payload = {"prompt": "Escreva sobre o projeto X."}
    mock_event.header.trace_id = "test-trace-001"
    mock_event.header.event_id = "event-001"
    mock_event.metadata = {}

    orchestrator._fetch_memories = AsyncMock(return_value=(None, None))
    await orchestrator._process_cognitive_cycle(mock_event, session=MagicMock())

    assert executor.execute_plan.call_count == 2
    assert auditor.audit_execution.call_count == 2

    assert bus.publish.called
    reply_event = bus.publish.call_args.args[1]
    response_text = reply_event.payload["response"]

    assert "**ALERTA DE AUDITORIA COGNITIVA**" in response_text
    assert "SAIDA GERADA (NAO CONFIAVEL)" in response_text
    assert "Fato inventado sobre o projeto X." in response_text
