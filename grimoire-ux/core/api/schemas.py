"""
Grimoire API – Contratos de Normalização (Pydantic v2)
Todos os dados que entram ou saem do Gateway são validados aqui.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ==========================================
# CONTRATOS DE ENTRADA
# ==========================================


class ChatRequest(BaseModel):
    """Payload normalizado para requisições de chat (REST e WS)."""

    prompt: str = Field(..., min_length=1, max_length=8000)
    context_hints: List[str] = Field(default_factory=list)
    session_id: Optional[str] = Field(
        default=None, description="ID de sessão para correlação WS."
    )

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, v: str) -> str:
        return v.strip()


# ==========================================
# CONTRATOS DE SAÍDA – REST
# ==========================================


class ChatResponse(BaseModel):
    """Resposta normalizada do endpoint síncrono."""

    trace_id: str
    response: str
    tier_used: str
    primary_intent: str
    tokens_used: Optional[int] = None
    audit_approved: Optional[bool] = None
    audit_critique: Optional[str] = None


# ==========================================
# CONTRATOS DE SAÍDA – WEBSOCKET (Frames)
# ==========================================


class WsFrameType(str, Enum):
    TRACE = "trace"
    PLAN = "plan"
    PLAN_STEP_UPDATE = "plan_step_update"
    RESPONSE = "response"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    CONNECTED = "connected"


class TraceFrame(BaseModel):
    """Frame de telemetria emitido em tempo real pelo Orchestrator."""

    type: Literal[WsFrameType.TRACE] = WsFrameType.TRACE
    trace_id: str
    agent: str = Field(
        description="Agente que gerou este log (ex: 'IntentClassifier')."
    )
    action: str = Field(description="Descrição legível da ação em curso.")
    tier: Optional[str] = None
    timestamp_ms: int


class PlanStep(BaseModel):
    """Um passo individual do plano de execução T3."""

    id: int
    description: str
    tools: List[str] = Field(default_factory=list)
    status: Literal["pending", "active", "completed", "failed"] = "pending"


class PlanFrame(BaseModel):
    """Frame enviado quando o PlannerAgent gera o DAG de execução."""

    type: Literal[WsFrameType.PLAN] = WsFrameType.PLAN
    trace_id: str
    plan_rationale: str
    steps: List[PlanStep]


class PlanStepUpdateFrame(BaseModel):
    """Frame de atualização de status de um passo do plano."""

    type: Literal[WsFrameType.PLAN_STEP_UPDATE] = WsFrameType.PLAN_STEP_UPDATE
    trace_id: str
    step_id: int
    status: Literal["pending", "active", "completed", "failed"]


class ResponseFrame(BaseModel):
    """Frame final contendo a resposta completa da sessão cognitiva."""

    type: Literal[WsFrameType.RESPONSE] = WsFrameType.RESPONSE
    trace_id: str
    content: str
    tier_used: str
    primary_intent: str
    audit_approved: bool = True
    audit_critique: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ErrorFrame(BaseModel):
    """Frame de erro estruturado para o frontend."""

    type: Literal[WsFrameType.ERROR] = WsFrameType.ERROR
    trace_id: str
    code: str
    message: str


class ConnectedFrame(BaseModel):
    """Handshake inicial após conexão WS bem-sucedida."""

    type: Literal[WsFrameType.CONNECTED] = WsFrameType.CONNECTED
    session_id: str
    message: str = "Grimoire Cognitive OS — Canal bidirecional estabelecido."
