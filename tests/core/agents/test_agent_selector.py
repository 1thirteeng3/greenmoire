import pytest

from core.agents.agent_selector import AgentSelector


class MockEmbeddingProvider:
    """Mock assíncrono para evitar chamadas de rede reais durante os testes."""

    async def generate_embedding(self, text: str) -> list[float]:
        # Retorna um vetor dummy estático para passar pela validação de tipo
        return [0.1] * 1024


@pytest.mark.asyncio
async def test_writer_agent_rbac_restrictions():
    """
    Garante que o WriterAgent NUNCA receba permissão para deletar notas.
    Esta restrição é vital para a Soberania de Dados.
    """
    mock_provider = MockEmbeddingProvider()
    selector = AgentSelector(embedding_provider=mock_provider)

    # Acesso direto ao perfil para testar as restrições baseadas na configuração
    writer_profile = selector.agents["writer"]["profile"]

    assert writer_profile.name == "WriterAgent"
    assert "write_obsidian_note" in writer_profile.allowed_tools
    assert "delete_obsidian_note" not in writer_profile.allowed_tools  # CRÍTICO


@pytest.mark.asyncio
async def test_governance_agent_rbac_allowance():
    """
    Garante que o GovernanceAgent possui a chave destrutiva necessária.
    """
    mock_provider = MockEmbeddingProvider()
    selector = AgentSelector(embedding_provider=mock_provider)

    gov_profile = selector.agents["governance"]["profile"]

    assert gov_profile.name == "GovernanceAgent"
    assert "delete_obsidian_note" in gov_profile.allowed_tools
