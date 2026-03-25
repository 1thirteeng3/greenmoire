import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import String, Text, Boolean, DateTime, Index, ARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

EMBEDDING_DIMENSION = 1536


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)


class SemanticMemory(BaseModel):
    __tablename__ = "semantic_memories"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    human_verified: Mapped[bool] = mapped_column(Boolean, default=False)
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
    __tablename__ = "error_memories"
    original_output: Mapped[str] = mapped_column(Text, nullable=False)
    human_correction: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
