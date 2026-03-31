import json
import logging
from typing import List

from pydantic import BaseModel, Field, ValidationError

from core.brain.model_router import ModelRouter

logger = logging.getLogger(__name__)


# ==========================================
# CONTRATO DE DADOS DO PLANO DE EXECUCAO
# ==========================================
class ExecutionStep(BaseModel):
    step_id: int = Field(description="ID sequencial e unico da etapa.")
    action_description: str = Field(
        description="Instrucao atomica, clara e acionavel do que deve ser feito."
    )
    required_tools: List[str] = Field(
        description="Lista exata de ferramentas que o Executor deve usar neste passo."
    )
    expected_outcome: str = Field(
        description=(
            "O estado, dado ou confirmacao que define que este passo foi concluido com sucesso."
        )
    )
    dependencies: List[int] = Field(
        default_factory=list,
        description="IDs de etapas que devem ser concluidas estritamente antes desta.",
    )


class ExecutionPlan(BaseModel):
    plan_rationale: str = Field(
        description="A justificativa logica para a estrategia de decomposicao escolhida."
    )
    steps: List[ExecutionStep]


# ==========================================
# MOTOR DO PLANEJADOR
# ==========================================
class PlannerAgent:
    """
    Agente de Decomposicao Logica (O Arquiteto).
    Isolado de ferramentas fisicas, foca em transformar intencoes ambiguas
    em grafos de execucao para o ExecutorAgent.
    """

    def __init__(self, model_router: ModelRouter):
        self.router = model_router

    async def generate_plan(
        self,
        user_prompt: str,
        context: str,
        available_tools: List[str],
        target_persona: str,
    ) -> ExecutionPlan:
        logger.info(
            "PlannerAgent: Iniciando decomposicao estruturada para a persona '%s'...",
            target_persona,
        )

        system_prompt = f"""
        Voce e o Arquiteto de Planejamento do Grimoire.
        Sua unica funcao e receber uma solicitacao complexa e quebra-la em passos logicos e atomicos de execucao.

        RESTRICOES DE ARQUITETURA:
        1. O agente que executara este plano atuara sob a persona: {target_persona}.
        2. FERRAMENTAS DISPONIVEIS: {available_tools}. Nunca sugira ferramentas fora desta lista.
        3. Dependencias: Se o Passo 2 precisa dos dados do Passo 1, defina isso no campo 'dependencies'.
        4. Resultados: Defina o 'expected_outcome' de forma mensuravel (ex: 'Arquivo X salvo no disco', 'JSON de resposta obtido').

        CONTEXTO RECUPERADO DA MEMORIA:
        {context if context else "Nenhum contexto previo fornecido."}

        Responda ESTRITAMENTE em JSON valido, obedecendo a seguinte estrutura:
        {{
            "plan_rationale": "Explicacao da sua estrategia",
            "steps": [
                {{
                    "step_id": 1,
                    "action_description": "Fazer X",
                    "required_tools": ["tool_name"],
                    "expected_outcome": "Dado X extraido",
                    "dependencies": []
                }}
            ]
        }}
        """

        try:
            response_text = await self.router.execute_tier(
                tier="T3",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Solicitacao do Usuario: {user_prompt}",
                    },
                ],
            )

            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            plan_dict = json.loads(clean_json)
            plan = ExecutionPlan(**plan_dict)

            logger.info(
                "PlannerAgent: Plano estrategico gerado com sucesso. Passos: %s.",
                len(plan.steps),
            )
            return plan

        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error(
                "PlannerAgent: Falha critica no parsing estruturado do plano. Erro: %s",
                exc,
            )
            return self._generate_fallback_plan(user_prompt)
        except Exception as exc:
            logger.error("PlannerAgent: Falha de inferencia. Erro: %s", exc)
            return self._generate_fallback_plan(user_prompt)

    def _generate_fallback_plan(self, original_prompt: str) -> ExecutionPlan:
        """
        Fail-safe: se o planejamento falhar, degrada para execucao monolitica.
        """
        logger.warning("PlannerAgent: Acionando plano de contingencia (Fallback Plan).")
        return ExecutionPlan(
            plan_rationale=(
                "Falha na decomposicao estruturada via LLM. "
                "Recorrendo a execucao monolitica direta (Degradacao Graciosa)."
            ),
            steps=[
                ExecutionStep(
                    step_id=1,
                    action_description=(
                        "Resolva a seguinte solicitacao de forma integral: "
                        f"{original_prompt}"
                    ),
                    required_tools=[],
                    expected_outcome="Solicitacao do usuario integralmente atendida.",
                    dependencies=[],
                )
            ],
        )
