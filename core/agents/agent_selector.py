import logging
from typing import Dict

from core.agents.agent_models import AgentProfile

logger = logging.getLogger(__name__)


class AgentSelector:
    """
    Roteador de Especialistas (Multi-Agent System).
    Evita saturação de contexto limitando ferramentas e regras por tarefa T3.
    """

    def __init__(self):
        self.agents: Dict[str, AgentProfile] = {
            "researcher": AgentProfile(
                name="ResearchAgent",
                role_description=(
                    "Você é um Pesquisador Analítico. Sua função é buscar fatos na web "
                    "ou na memória e sintetizá-los. Nunca presuma fatos; use suas "
                    "ferramentas de busca exaustivamente."
                ),
                allowed_tools=["web_search", "get_current_time"],
                max_loops=6,
            ),
            "writer": AgentProfile(
                name="WriterAgent",
                role_description=(
                    "Você é um Escritor Técnico e Arquivista. Sua função é formatar "
                    "dados perfeitamente em Markdown e salvar documentos no cofre do "
                    "usuário. Foco em clareza, formatação e precisão estrutural."
                ),
                allowed_tools=["write_obsidian_note", "get_current_time"],
                max_loops=4,
            ),
            "planner": AgentProfile(
                name="PlannerAgent",
                role_description=(
                    "Você é um Arquiteto de Projetos. Sua função é desmembrar problemas "
                    "complexos em etapas acionáveis. Avalie a viabilidade e crie "
                    "planos estruturados."
                ),
                allowed_tools=["get_current_time"],
                max_loops=3,
            ),
            "general_executor": AgentProfile(
                name="GeneralAgent",
                role_description=(
                    "Você é um Agente de Execução Geral. Resolva a solicitação do "
                    "usuário utilizando as ferramentas disponíveis com máxima eficiência lógica."
                ),
                allowed_tools=["web_search", "get_current_time", "write_obsidian_note"],
                max_loops=5,
            ),
        }

    def select_agent(self, primary_intent: str) -> AgentProfile:
        """
        Mapeia intenção textual para perfil de agente especializado.
        """
        intent_lower = primary_intent.lower()

        if any(kw in intent_lower for kw in ["pesquisa", "buscar", "noticias", "informacao", "web"]):
            logger.info(f"Agent Selector: Roteando para {self.agents['researcher'].name}")
            return self.agents["researcher"]
        if any(kw in intent_lower for kw in ["escrever", "anotar", "salvar", "resumo", "documento"]):
            logger.info(f"Agent Selector: Roteando para {self.agents['writer'].name}")
            return self.agents["writer"]
        if any(kw in intent_lower for kw in ["plano", "projeto", "arquitetura", "etapas"]):
            logger.info(f"Agent Selector: Roteando para {self.agents['planner'].name}")
            return self.agents["planner"]

        logger.warning(
            f"Agent Selector: Intenção '{primary_intent}' não mapeada. Usando GeneralAgent."
        )
        return self.agents["general_executor"]
