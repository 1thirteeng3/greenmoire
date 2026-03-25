from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class IntentTier(str, Enum):
    T1_DIRECT = "T1"
    T2_ANALYTICAL = "T2"
    T3_COMPLEX = "T3"


class ParsedIntent(BaseModel):
    """Representa a compreensão do sistema sobre o que o usuário deseja."""

    original_query: str = Field(...)
    classified_tier: IntentTier = Field(...)
    required_domains: List[str] = Field(
        description="Domínios de memória semântica necessários para esta query."
    )
    requires_tools: bool = Field(default=False)
    ambiguity_level: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Se > 0.5, o sistema deve devolver uma pergunta esclarecedora "
            "em vez de executar."
        ),
    )


class ExecutionPlan(BaseModel):
    """Plano gerado pelo Planner Agent para intenções T3."""

    plan_id: str = Field(..., description="Identificador único deste plano.")
    intent_reference: str = Field(..., description="A query/intenção que originou este plano.")
    steps: List[str] = Field(..., description="Lista sequencial de ações atômicas a serem tomadas.")
    estimated_complexity: str = Field(description="Ex: 'High', 'Medium', 'Low'")
    requires_auditor: bool = Field(
        default=True,
        description="Operações críticas sempre exigem auditoria do resultado final.",
    )
