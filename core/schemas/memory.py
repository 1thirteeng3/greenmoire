from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, SkipValidation


def current_utc() -> datetime:
    return datetime.now(timezone.utc)


class MemoryMetadata(BaseModel):
    source: str = Field(
        description="Origem da memória (ex: 'user_input', 'rag_ingestion', 'auditor_agent')"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Nível de confiança da informação. Menor que 0.8 exige auditoria.",
    )
    tags: list[str] = Field(default_factory=list)
    # Permite metadados extras sem quebrar o schema, mas tipando o core.
    model_config = ConfigDict(extra="allow")


class BaseMemoryEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str = Field(..., description="O conteúdo textual bruto da memória.")
    # Evita validação elemento-a-elemento de vetores grandes em cada hop de evento.
    embedding: SkipValidation[list[float]] | None = Field(
        default=None,
        description="Vetor denso opcional. Preferir tráfego por referência em eventos.",
    )
    # Referência para armazenar vetores fora do payload quando possível.
    embedding_ref_id: str | None = Field(
        default=None,
        description="ID de referência para vetor persistido (preferencial para tráfego leve).",
    )
    created_at: datetime = Field(default_factory=current_utc)
    updated_at: datetime = Field(default_factory=current_utc)
    metadata: MemoryMetadata


class SemanticMemory(BaseMemoryEntity):
    """Fatos consolidados, conhecimento geral e preferências do usuário."""

    memory_type: str = Field(default="semantic", frozen=True)
    domain: str = Field(
        ...,
        description="Categoria do conhecimento (ex: 'preferences', 'tech_stack', 'project_x').",
    )
    human_verified: bool = Field(
        default=False,
        description="True se o usuário confirmou este fato explicitamente.",
    )


class EpisodicMemory(BaseMemoryEntity):
    """Histórico de interações, pensamentos do sistema e eventos."""

    memory_type: str = Field(default="episodic", frozen=True)
    trace_id: str = Field(
        ...,
        description="Vínculo obrigatório com o fluxo cognitivo que gerou esta memória.",
    )
    participants: list[str] = Field(
        description="Ex: ['user', 'executor_agent', 'auditor_agent']"
    )


class ErrorMemory(BaseMemoryEntity):
    """Registro de alucinações, falhas de lógica e correções do usuário."""

    memory_type: str = Field(default="error", frozen=True)
    original_output: str = Field(
        ..., description="A saída do sistema que foi classificada como erro."
    )
    human_correction: str = Field(
        ..., description="A correção fornecida pelo usuário ou o log de conflito."
    )
    resolved: bool = Field(
        default=False, description="Define se a política de recuperação foi concluída."
    )


class MemoryEnvelope(BaseModel):
    """
    Envelope discriminado para consumo uniforme em filas/eventos.
    """

    memory: SemanticMemory | EpisodicMemory | ErrorMemory
    extra: dict[str, Any] = Field(default_factory=dict)
