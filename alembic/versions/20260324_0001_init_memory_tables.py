"""init memory tables

Revision ID: 20260324_0001
Revises:
Create Date: 2026-03-24 00:00:00.000000
"""

from typing import Sequence, Union
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "20260324_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _embedding_dimension() -> int:
    raw_value = os.getenv("EMBEDDING_DIMENSION", "1536")
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            "EMBEDDING_DIMENSION deve ser inteiro para executar migrações."
        ) from exc
    if value <= 0:
        raise RuntimeError("EMBEDDING_DIMENSION deve ser maior que zero.")
    return value


def upgrade() -> None:
    dimension = _embedding_dimension()
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "semantic_memories",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("trace_id", sa.String(length=255), nullable=False),
        sa.Column("source_service", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("embedding", Vector(dimension), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_semantic_memories_trace_id", "semantic_memories", ["trace_id"], unique=False
    )
    op.create_index(
        "ix_semantic_memories_source_service",
        "semantic_memories",
        ["source_service"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX ix_semantic_memories_embedding_hnsw "
        "ON semantic_memories USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "episodic_memories",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("trace_id", sa.String(length=255), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column(
            "event_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("embedding", Vector(dimension), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_episodic_memories_trace_id", "episodic_memories", ["trace_id"], unique=False
    )
    op.create_index(
        "ix_episodic_memories_correlation_id",
        "episodic_memories",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        "ix_episodic_memories_event_type",
        "episodic_memories",
        ["event_type"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX ix_episodic_memories_embedding_hnsw "
        "ON episodic_memories USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "error_memories",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("trace_id", sa.String(length=255), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_error_memories_trace_id", "error_memories", ["trace_id"], unique=False
    )
    op.create_index(
        "ix_error_memories_error_code", "error_memories", ["error_code"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_error_memories_error_code", table_name="error_memories")
    op.drop_index("ix_error_memories_trace_id", table_name="error_memories")
    op.drop_table("error_memories")

    op.execute("DROP INDEX IF EXISTS ix_episodic_memories_embedding_hnsw")
    op.drop_index("ix_episodic_memories_event_type", table_name="episodic_memories")
    op.drop_index("ix_episodic_memories_correlation_id", table_name="episodic_memories")
    op.drop_index("ix_episodic_memories_trace_id", table_name="episodic_memories")
    op.drop_table("episodic_memories")

    op.execute("DROP INDEX IF EXISTS ix_semantic_memories_embedding_hnsw")
    op.drop_index("ix_semantic_memories_source_service", table_name="semantic_memories")
    op.drop_index("ix_semantic_memories_trace_id", table_name="semantic_memories")
    op.drop_table("semantic_memories")
