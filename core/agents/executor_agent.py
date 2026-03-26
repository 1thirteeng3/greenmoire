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

    @staticmethod
    def _normalize_tool_arguments(raw_args: Any) -> str:
        """Normaliza argumentos de tool-call para string JSON."""
        if isinstance(raw_args, dict):
            import json

            return json.dumps(raw_args)
        if isinstance(raw_args, str):
            return raw_args
        return "{}"

    async def execute_plan(
        self,
        user_prompt: str,
        plan: ExecutionPlan,
        agent_profile: AgentProfile,
        rag_context: Optional[str] = None,
        correction_directive: Optional[str] = None,
    ) -> str:
        """Executa o plano como fluxo semantico por etapa."""
        logger.info(
            "ExecutorAgent: Iniciando processamento semantico do DAG (%s etapas).",
            len(plan.steps),
        )

        # Filtragem RBAC das ferramentas.
        allowed_schemas = [
            schema
            for schema in self.tool_registry.get_all_schemas()
            if schema["function"]["name"] in agent_profile.allowed_tools
        ]

        workflow_memory: Dict[int, str] = {}
        final_aggregated_output: List[str] = []

        # Execucao explicita etapa por etapa.
        for step in plan.steps:
            unmet_dependencies = [dep for dep in step.dependencies if dep not in workflow_memory]
            if unmet_dependencies:
                step_output = (
                    f"Aviso: Etapa {step.step_id} bloqueada por dependencias nao resolvidas: "
                    f"{unmet_dependencies}."
                )
                logger.warning("ExecutorAgent: %s", step_output)
                workflow_memory[step.step_id] = step_output
                final_aggregated_output.append(f"\n### Etapa {step.step_id}\n{step_output}\n")
                continue

            logger.info(
                "ExecutorAgent: Executando etapa %s - %s",
                step.step_id,
                step.action_description[:80],
            )

            step_system_content = [
                agent_profile.role_description,
                (
                    f"OBJETIVO ATUAL (Etapa {step.step_id} de {len(plan.steps)}): "
                    f"{step.action_description}"
                ),
                f"RESULTADO ESPERADO: {step.expected_outcome}",
                "Conclua APENAS esta etapa antes de seguir.",
            ]

            if workflow_memory:
                history = "\n".join(
                    [f"Etapa {step_id}: {result}" for step_id, result in sorted(workflow_memory.items())]
                )
                step_system_content.append(
                    f"\n<HISTORICO_DAS_ETAPAS_ANTERIORES>\n{history}\n</HISTORICO_DAS_ETAPAS_ANTERIORES>"
                )

            if rag_context and step.step_id == 1:
                step_system_content.append(
                    f"\n<CONHECIMENTO_RECUPERADO>\n{rag_context}\n</CONHECIMENTO_RECUPERADO>"
                )

            if correction_directive:
                logger.warning(
                    "ExecutorAgent: Operando sob diretiva de correcao (Recovery Mode)."
                )
                step_system_content.append(
                    "\n<ALERTA_DE_AUDITORIA>\n"
                    f"Corrija a falha anterior: '{correction_directive}'\n"
                    "</ALERTA_DE_AUDITORIA>"
                )

            messages: List[Dict[str, Any]] = [
                {"role": "system", "content": "\n".join(step_system_content)},
                {
                    "role": "user",
                    "content": (
                        f"Meta principal do usuario: {user_prompt}\n"
                        "Inicie a etapa atual."
                    ),
                },
            ]

            iteration = 0
            step_completed = False
            step_output = ""

            while iteration < agent_profile.max_loops and not step_completed:
                iteration += 1
                logger.debug(
                    "ExecutorAgent: ReAct etapa %s iteracao %s/%s",
                    step.step_id,
                    iteration,
                    agent_profile.max_loops,
                )

                response = await self.router.execute_tier_with_tools(
                    tier="T3",
                    messages=messages,
                    tools=allowed_schemas,
                )

                if isinstance(response, str) or not response.get("tool_calls"):
                    step_output = response if isinstance(response, str) else response.get("content", "")
                    step_completed = True
                    break

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
                    logger.debug("ExecutorAgent: Acionando ferramenta %s", tool_name)

                    tool_result = await self.tool_registry.execute_tool(
                        tool_name,
                        self._normalize_tool_arguments(raw_args),
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": tool_result,
                        }
                    )

            if not step_completed:
                step_output = (
                    f"Aviso: Etapa {step.step_id} abortada por exceder o limite "
                    "de iteracoes ReAct."
                )

            workflow_memory[step.step_id] = step_output
            final_aggregated_output.append(f"\n### Etapa {step.step_id}\n{step_output}\n")

        logger.info("ExecutorAgent: DAG processado integralmente.")
        return "".join(final_aggregated_output).strip()
