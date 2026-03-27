from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class EventHeader(BaseModel):
    event_id: str = Field(default_factory=generate_uuid)
    trace_id: str = Field(
        description="Identificador único para rastrear o fluxo cognitivo completo."
    )
    correlation_id: Optional[str] = Field(
        default=None, description="ID do evento que originou este evento."
    )
    timestamp: datetime = Field(default_factory=current_utc_time)
    source_service: str = Field(
        description="Nome do microsserviço que emitiu o evento."
    )
    event_type: str = Field(
        description="Classificação do evento (ex: 'intent_detected', 'memory_retrieved')."
    )


class BaseEvent(BaseModel):
    header: EventHeader
    payload: Dict[str, Any] = Field(description="Carga útil estruturada do evento.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("payload")
    def validate_payload_not_empty(cls, v):
        if not v:
            raise ValueError("O payload do evento não pode estar vazio.")
        return v
