import json
import logging
from typing import Any, Dict, List, Optional

from core.agents.agent_models import AgentProfile
from core.agents.planner_agent import ExecutionPlan
from core.agents.tool_registry import ToolRegistry
from core.brain.model_router import ModelRouter

logger = logging.getLogger(__name__)


class ExecutorAgent:
    """
    Agente Operacional (O Musculo).
    Recebe um plano e executa tarefas utilizando o padrao ReAct e ferramentas fisicas.
    """

    def __init__(self, model_router: ModelRouter, tool_registry: ToolRegistry):
        self.router = model_router
        self.tool_registry = tool_registry

    async def execute_plan(
        self,
        user_prompt: str,
        plan: ExecutionPlan,
        agent_profile: AgentProfile,
        rag_context: Optional[str] = None,
        correction_directive: Optional[str] = None,
    ) -> str:
        """Executa o plano tatico com suporte a recovery mode."""
        logger.info("ExecutorAgent: Iniciando execucao com a persona '%s'", agent_profile.name)

        # 1. Montagem da "mente" do executor.
        system_content = [
            agent_profile.role_description,
            "Voce deve seguir ESTE PLANO ESTRUTURADO passo a passo:",
            *[f"{step.step_id}. {step.action_description}" for step in plan.steps],
        ]

        if rag_context:
            system_content.append(
                f"\n<CONHECIMENTO_RECUPERADO>\n{rag_context}\n</CONHECIMENTO_RECUPERADO>"
            )

        if correction_directive:
            logger.warning("ExecutorAgent: Operando sob diretiva de correcao (Recovery Mode).")
            system_content.append(
                "\n<ALERTA_DE_AUDITORIA>\n"
                f"Sua tentativa anterior falhou. O Auditor emitiu a seguinte critica: '{correction_directive}'. "
                "CORRIJA SEU COMPORTAMENTO IMEDIATAMENTE NESTA NOVA TENTATIVA.\n"
                "</ALERTA_DE_AUDITORIA>"
            )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": "\n".join(system_content)},
            {"role": "user", "content": user_prompt},
        ]

        # 2. Filtragem de ferramentas (RBAC).
        allowed_schemas = [
            schema
            for schema in self.tool_registry.get_all_schemas()
            if schema["function"]["name"] in agent_profile.allowed_tools
        ]

        # 3. Loop ReAct dedicado.
        iteration = 0
        max_iterations = agent_profile.max_loops

        while iteration < max_iterations:
            iteration += 1
            logger.debug("ExecutorAgent: ReAct iteracao %s/%s", iteration, max_iterations)

            response = await self.router.execute_tier_with_tools(
                tier="T3",
                messages=messages,
                tools=allowed_schemas,
            )

            if isinstance(response, str) or not response.get("tool_calls"):
                content = response if isinstance(response, str) else response.get("content")
                return content or "Execucao concluida sem output textual final."

            tool_calls = response["tool_calls"]
            messages.append(
                {
                    "role": "assistant",
                    "tool_calls": tool_calls,
                    "content": response.get("content", ""),
                }
            )

            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                raw_args = tool_call["function"].get("arguments", "{}")
                logger.info("ExecutorAgent: Chamando ferramenta fisica -> %s", tool_name)

                if isinstance(raw_args, dict):
                    tool_args = json.dumps(raw_args)
                elif isinstance(raw_args, str):
                    tool_args = raw_args
                else:
                    tool_args = "{}"

                tool_result = await self.tool_registry.execute_tool(tool_name, tool_args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result,
                    }
                )

        return "AVISO: O Executor excedeu o limite maximo de iteracoes sem concluir a tarefa."
