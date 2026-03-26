import json
import logging
from typing import List

from pydantic import BaseModel, Field

from core.brain.model_router import ModelRouter

logger = logging.getLogger(__name__)


class ExecutionStep(BaseModel):
    step_id: int
    action_description: str = Field(
        description="A instrucao clara do que deve ser feito neste passo."
    )
    required_tools: List[str] = Field(
        description="Ferramentas sugeridas para este passo."
    )


class ExecutionPlan(BaseModel):
    plan_rationale: str = Field(description="A logica por tras desta decomposicao.")
    steps: List[ExecutionStep]


class PlannerAgent:
    """
    Agente de Decomposicao Logica.
    Pega numa tarefa T3 monolitica e quebra-a num plano de execucao estruturado.
    """

    def __init__(self, model_router: ModelRouter):
        self.router = model_router

    async def generate_plan(
        self,
        user_prompt: str,
        context: str,
        available_tools: List[str],
    ) -> ExecutionPlan:
        logger.info("PlannerAgent: Iniciando decomposicao da tarefa...")

        system_prompt = f"""
        Voce e o Arquiteto de Planejamento do Grimoire.
        Sua unica funcao e receber uma solicitacao complexa e quebra-la em passos logicos de execucao para um Agente Executor.

        FERRAMENTAS DISPONIVEIS NO SISTEMA:
        {available_tools}

        CONTEXTO RECUPERADO DA MEMORIA:
        {context}

        Responda ESTRITAMENTE em JSON obedecendo a este schema:
        {{"plan_rationale": "motivo", "steps": [{{"step_id": 1, "action_description": "fazer X", "required_tools": ["tool_name"]}}]}}
        """

        response = await self.router.execute_tier(
            tier="T3",  # Planejamento exige alto raciocinio
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Solicitacao: {user_prompt}"},
            ],
        )

        clean_json = response.replace("```json", "").replace("```", "").strip()

        try:
            plan_dict = json.loads(clean_json)
            plan = ExecutionPlan(**plan_dict)
            logger.info("PlannerAgent: Plano gerado com %s passos.", len(plan.steps))
            return plan
        except json.JSONDecodeError as exc:
            logger.error("PlannerAgent falhou ao gerar JSON valido: %s", exc)
            # Fallback de seguranca: Um unico passo contendo a intencao original.
            return ExecutionPlan(
                plan_rationale=(
                    "Falha na decomposicao estruturada. "
                    "Recorrendo a execucao monolitica direta."
                ),
                steps=[
                    ExecutionStep(
                        step_id=1,
                        action_description=user_prompt,
                        required_tools=[],
                    )
                ],
            )
