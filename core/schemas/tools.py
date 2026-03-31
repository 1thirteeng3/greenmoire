from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BaseToolInput(BaseModel):
    """
    Classe base estrita para contratos de ferramentas.
    Impede argumentos extras e coerções implícitas perigosas.
    """

    model_config = ConfigDict(extra="forbid", strict=True)


class ToolName(str, Enum):
    WEB_SEARCH = "web_search"
    FETCH_URL = "fetch_url"
    WRITE_NOTE = "write_note"
    UPSERT_MEMORY = "upsert_memory"


class WebSearchToolInput(BaseToolInput):
    query: str = Field(min_length=1, description="Consulta de busca na web.")
    top_k: int = Field(default=5, ge=1, le=25)


class FetchUrlToolInput(BaseToolInput):
    url: str = Field(description="URL absoluta a ser consultada.")
    timeout_seconds: int = Field(default=30, ge=1, le=120)


class WriteNoteToolInput(BaseToolInput):
    path: str = Field(min_length=1, description="Caminho relativo da nota no cofre.")
    content: str = Field(
        min_length=1, description="Conteúdo markdown a ser persistido."
    )
    overwrite: bool = Field(default=False)


class UpsertMemoryToolInput(BaseToolInput):
    memory_id: str | None = Field(
        default=None, description="ID existente para update; vazio para insert."
    )
    memory_type: Literal["semantic", "episodic", "error"]
    content: str = Field(min_length=1)
    trace_id: str | None = Field(default=None)
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0)


class ToolCallEnvelope(BaseModel):
    """
    Envelope de execução de ferramenta.
    O payload permanece tipado por ferramenta concreta e validado antes da execução.
    """

    tool_name: ToolName
    call_id: str = Field(description="ID único da chamada de ferramenta.")
    caller_agent: str = Field(description="Agente que solicitou a execução.")
    # Não usar Dict[str, Any] solto no executor.
    payload: (
        WebSearchToolInput
        | FetchUrlToolInput
        | WriteNoteToolInput
        | UpsertMemoryToolInput
    )
