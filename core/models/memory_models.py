import os
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Index, String, Text, Enum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", 1536))


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)


# ==========================================
# DOMÍNIO DE MEMÓRIA
# ==========================================
class SemanticMemory(BaseModel):
    __tablename__ = "semantic_memories"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[Any]] = mapped_column(
        Vector(EMBEDDING_DIMENSION), nullable=True
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    human_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relacionamento 1:1 estrito
    sync_state: Mapped["ObsidianSyncState"] = relationship(
        "ObsidianSyncState",
        back_populates="semantic_memory",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        Index(
            "hnsw_idx_semantic",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class EpisodicMemory(BaseModel):
    __tablename__ = "episodic_memories"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    participants: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)


class ErrorMemory(BaseModel):
    """
    Memória de erro vetorizada para recuperação semântica de correções.
    """

    __tablename__ = "error_memories"

    original_output: Mapped[str] = mapped_column(Text, nullable=False)
    human_correction: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[Any]] = mapped_column(
        Vector(EMBEDDING_DIMENSION), nullable=True
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    __table_args__ = (
        Index(
            "hnsw_idx_error",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


# ==========================================
# DOMÍNIO DE INFRAESTRUTURA
# ==========================================
class ObsidianSyncState(BaseModel):
    __tablename__ = "obsidian_sync_states"

    semantic_memory_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("semantic_memories.id", ondelete="CASCADE"),
        unique=True,
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    last_sync_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)

    semantic_memory: Mapped["SemanticMemory"] = relationship(
        "SemanticMemory", back_populates="sync_state"
    )


# ==========================================
# DOMÍNIO DE INGESTÃO
# ==========================================
class IngestionStatus(PyEnum):
    PENDING = "PENDING"
    DOWNLOADED = "DOWNLOADED"
    CHUNKED = "CHUNKED"
    VECTORIZED = "VECTORIZED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IngestionTask(BaseModel):
    """Máquina de estados para rastrear pipelines assíncronos de ingestão."""

    __tablename__ = "ingestion_tasks"

    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus, name="ingestion_status_enum", create_type=False),
        default=IngestionStatus.PENDING,
        index=True,
    )
    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)
