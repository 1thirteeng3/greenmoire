"""
Tests para o MetaAgent (Fase 7).
Valida: chamadas ao modelo, quarentena, tratamento de falhas.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.agents.meta_agent import MetaAgent


@pytest.fixture
def mock_router():
    router = MagicMock()
    router.execute_tier = AsyncMock(
        return_value="def improved_function():\n    return 42\n"
    )
    return router


@pytest.fixture
def mock_sandbox():
    sandbox = MagicMock()
    proposal = MagicMock()
    proposal.id = "pr-test0001"
    sandbox.stage_proposal.return_value = proposal
    sandbox.run_security_tests.return_value = (True, "1 passed in 0.5s")
    return sandbox, proposal


@pytest.mark.asyncio
async def test_meta_agent_returns_proposal_id_on_success(
    tmp_path, mock_router, mock_sandbox
):
    """Sucesso completo: LLM retorna código, testes passam, proposta aguarda aprovação."""
    sandbox, proposal = mock_sandbox
    agent = MetaAgent(mock_router, sandbox)

    # Cria ficheiro alvo temporário
    target = tmp_path / "fake_module.py"
    target.write_text("def original(): pass\n", encoding="utf-8")

    result = await agent.self_improve(str(target), "Adicionar docstring")

    assert "pr-test0001" in result
    assert "SUCESSO" in result or "✅" in result
    sandbox.stage_proposal.assert_called_once()
    sandbox.run_security_tests.assert_called_once_with("pr-test0001")


@pytest.mark.asyncio
async def test_meta_agent_reports_failure_on_test_crash(
    tmp_path, mock_router, mock_sandbox
):
    """Se pytest falhar, MetaAgent deve reportar FALHA CRÍTICA sem tocar no sistema."""
    sandbox, proposal = mock_sandbox
    sandbox.run_security_tests.return_value = (
        False,
        "FAILED test_integrity.py:: assertion failed",
    )
    agent = MetaAgent(mock_router, sandbox)

    target = tmp_path / "failing_module.py"
    target.write_text("x = 1\n", encoding="utf-8")

    result = await agent.self_improve(str(target), "Quebrar tudo")

    assert "FALHA" in result or "💥" in result
    assert "pr-test0001" in result
    # Nenhum merge deve ter sido chamado
    sandbox.merge_proposal.assert_not_called()


@pytest.mark.asyncio
async def test_meta_agent_blocks_path_traversal(tmp_path, mock_router):
    """SandboxManager rejeita caminho fora de core/ — MetaAgent deve capturar e reportar."""
    from core.infrastructure.sandbox.manager import SandboxManager

    # SandboxManager real com root em tmp_path (sem core/ real equivalente)
    mgr = SandboxManager(root_dir=str(tmp_path))
    agent = MetaAgent(mock_router, mgr)

    # Ficheiro fora do core/ simulado
    outside = tmp_path / "secrets.txt"
    outside.write_text("token=abc123\n", encoding="utf-8")

    result = await agent.self_improve(str(outside), "Roubar segredos")

    assert "ACESSO NEGADO" in result or "🚫" in result


@pytest.mark.asyncio
async def test_meta_agent_handles_missing_file(mock_router, mock_sandbox):
    """Se o ficheiro alvo não existe, MetaAgent deve retornar mensagem de erro amigável."""
    sandbox, _ = mock_sandbox
    agent = MetaAgent(mock_router, sandbox)

    result = await agent.self_improve("/caminho/que/nao/existe.py", "Objetivo qualquer")

    assert "Falha" in result or "❌" in result
    sandbox.stage_proposal.assert_not_called()


@pytest.mark.asyncio
async def test_meta_agent_strips_markdown_fences(tmp_path, mock_sandbox):
    """Código com ```python deve ser limpo antes de ser enviado para sandbox."""
    sandbox, proposal = mock_sandbox
    router = MagicMock()
    router.execute_tier = AsyncMock(
        return_value="```python\ndef clean(): return True\n```"
    )
    agent = MetaAgent(router, sandbox)

    target = tmp_path / "strip_test.py"
    target.write_text("def original(): pass\n", encoding="utf-8")

    await agent.self_improve(str(target), "Deve limpar markdown")

    # O código enviado à sandbox NÃO deve conter backticks
    staged_code = sandbox.stage_proposal.call_args[0][1]  # positional arg 1
    assert "```" not in staged_code
    assert "def clean(): return True" in staged_code
