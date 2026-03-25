from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


def current_utc() -> datetime:
    return datetime.now(timezone.utc)


class IngestionTaskStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADED = "DOWNLOADED"
    CHUNKED = "CHUNKED"
    VECTORIZED = "VECTORIZED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IngestionSourceType(str, Enum):
    URL = "url"
    FILE = "file"
    RAW_TEXT = "raw_text"


class IngestionTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str
    source_type: IngestionSourceType
    source_uri: str = Field(description="URL, caminho local ou identificador lógico da origem.")
    status: IngestionTaskStatus = Field(default=IngestionTaskStatus.PENDING)
    retry_count: int = Field(default=0, ge=0)
    last_error: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=current_utc)
    updated_at: datetime = Field(default_factory=current_utc)

    model_config = ConfigDict(extra="forbid")


class IngestionRequest(BaseModel):
    task_id: str
    trace_id: str
    source_type: IngestionSourceType
    source_uri: str
    requested_by: str = Field(description="Serviço ou usuário que iniciou a ingestão.")

    model_config = ConfigDict(extra="forbid")


class RawContent(BaseModel):
    task_id: str
    trace_id: str
    extracted_text: str
    mime_type: Optional[str] = None
    language: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ContentChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    order_index: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class ChunkedContent(BaseModel):
    task_id: str
    trace_id: str
    chunks: list[ContentChunk]

    model_config = ConfigDict(extra="forbid")


class VectorizedChunk(BaseModel):
    chunk_id: str
    embedding_ref_id: str = Field(description="Referência para o vetor persistido no banco vetorial/pgvector.")
    dimension: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")


class VectorizedContent(BaseModel):
    task_id: str
    trace_id: str
    vectors: list[VectorizedChunk]

    model_config = ConfigDict(extra="forbid")


class IngestionRequestedEvent(BaseModel):
    task: IngestionTask
    request: IngestionRequest

    model_config = ConfigDict(extra="forbid")


class ContentExtractedEvent(BaseModel):
    task: IngestionTask
    content: RawContent

    model_config = ConfigDict(extra="forbid")


class ContentChunkedEvent(BaseModel):
    task: IngestionTask
    content: ChunkedContent

    model_config = ConfigDict(extra="forbid")


class ContentVectorizedEvent(BaseModel):
    task: IngestionTask
    content: VectorizedContent

    model_config = ConfigDict(extra="forbid")
