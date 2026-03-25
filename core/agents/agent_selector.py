import math
import logging
from typing import Dict, List

from core.agents.agent_models import AgentProfile
from core.integrations.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculo ultrarrapido de similaridade sem dependencia de numpy."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude = math.sqrt(sum(a * a for a in vec1)) * math.sqrt(sum(b * b for b in vec2))
    return dot_product / magnitude if magnitude != 0 else 0.0


class AgentSelector:
    """
    Roteador semantico de agentes.
    Compara o vetor da intencao do usuario com os vetores de capacidade dos agentes.
    """

    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedding_provider = embedding_provider
        self.agents: Dict[str, dict] = {
            "researcher": {
                "profile": AgentProfile(
                    name="ResearchAgent",
                    role_description=(
                        "Voce e um Pesquisador Analitico. Sua funcao e buscar fatos na web "
                        "ou na memoria e sintetiza-los. Nunca presuma fatos; use suas "
                        "ferramentas de busca exaustivamente."
                    ),
                    allowed_tools=["web_search", "get_current_time"],
                    max_loops=6,
                ),
                "semantic_anchor": (
                    "pesquisar na internet, buscar informacoes externas, ler noticias, descobrir "
                    "fatos novos, coleta de dados, scraping web, busca profunda em motores de pesquisa."
                ),
            },
            "writer": {
                "profile": AgentProfile(
                    name="WriterAgent",
                    role_description=(
                        "Voce e um Escritor Tecnico e Arquivista. Sua funcao e formatar dados "
                        "em Markdown e salvar documentos. REGRA DE SEGURANCA MAXIMA: Ao usar a "
                        "ferramenta 'write_obsidian_note', voce DEVE SEMPRE usar mode='inbox' "
                        "como padrao absoluto, a menos que o usuario use verbos explicitos de "
                        "modificacao (como 'adicione a', 'atualize' ou 'sobrescreva'). "
                        "Na duvida, escolha sempre 'inbox'."
                    ),
                    allowed_tools=["write_obsidian_note", "get_current_time"],
                    max_loops=4,
                ),
                "semantic_anchor": (
                    "escrever texto, criar arquivo markdown, salvar anotacao, arquivar documento "
                    "no obsidian, registrar ideias no cofre, documentar resumo, editar nota fisica."
                ),
            },
            "planner": {
                "profile": AgentProfile(
                    name="PlannerAgent",
                    role_description=(
                        "Voce e um Arquiteto de Projetos. Sua funcao e desmembrar problemas "
                        "complexos em etapas acionaveis. Avalie a viabilidade e crie planos estruturados."
                    ),
                    allowed_tools=[],
                    max_loops=3,
                ),
                "semantic_anchor": (
                    "criar planejamento, estruturar projeto, dividir em tarefas, criar roadmap, "
                    "organizar etapas, estrategia de execucao, arquitetar solucao."
                ),
            },
            "governance": {
                "profile": AgentProfile(
                    name="GovernanceAgent",
                    role_description=(
                        "Voce e o Zelador do Cofre (Zettelkasten). Sua funcao e podar o jardim "
                        "cognitivo, apagando notas duplicadas, obsoletas ou reestruturando informacoes antigas."
                    ),
                    allowed_tools=["delete_obsidian_note", "write_obsidian_note", "get_current_time"],
                    max_loops=4,
                ),
                "semantic_anchor": (
                    "apagar arquivo antigo, deletar nota obsoleta, limpar cofre, remover anotacao "
                    "duplicada, podar jardim digital, excluir arquivo markdown inutil."
                ),
            },
        }
        self._anchor_embeddings: Dict[str, List[float]] = {}

    async def _ensure_embeddings_loaded(self) -> None:
        """Lazy loading: vetoriza as ancoras apenas na primeira execucao."""
        if not self._anchor_embeddings:
            logger.info("Agent Selector: Vetorizando ancoras semanticas de agentes...")
            for key, data in self.agents.items():
                emb = await self.embedding_provider.generate_embedding(data["semantic_anchor"])
                self._anchor_embeddings[key] = emb

    async def select_agent(self, primary_intent: str) -> AgentProfile:
        """
        Calcula embedding da intencao e devolve o agente com maior similaridade de cosseno.
        """
        await self._ensure_embeddings_loaded()
        intent_embedding = await self.embedding_provider.generate_embedding(primary_intent)

        best_score = -1.0
        selected_agent_key = "writer"  # Fallback conservador

        for key, anchor_emb in self._anchor_embeddings.items():
            score = _cosine_similarity(intent_embedding, anchor_emb)
            logger.debug(f"Semantic Score [{key}]: {score:.4f}")
            if score > best_score:
                best_score = score
                selected_agent_key = key

        if best_score < 0.45:
            logger.warning(
                f"Baixa confianca semantica ({best_score:.2f}). Fallback para ResearchAgent."
            )
            return self.agents["researcher"]["profile"]

        logger.info(
            "Agent Selector: Roteado para %s (Score: %.4f)",
            self.agents[selected_agent_key]["profile"].name,
            best_score,
        )
        return self.agents[selected_agent_key]["profile"]
