"""Add ObsidianSyncState and error embeddings

Revision ID: 20260325_0003
Revises: 20260325_0002
Create Date: 2026-03-25 00:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "20260325_0003"
down_revision: Union[str, None] = "20260325_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "error_memories", sa.Column("original_output", sa.Text(), nullable=True)
    )
    op.add_column(
        "error_memories", sa.Column("human_correction", sa.Text(), nullable=True)
    )
    op.add_column(
        "error_memories",
        sa.Column(
            "resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column("error_memories", sa.Column("embedding", Vector(1536), nullable=True))

    op.execute(
        "UPDATE error_memories SET original_output = message WHERE original_output IS NULL"
    )
    op.execute(
        "UPDATE error_memories SET human_correction = COALESCE(metadata->>'human_correction', '') WHERE human_correction IS NULL"
    )
    op.execute("UPDATE error_memories SET resolved = false WHERE resolved IS NULL")

    op.alter_column("error_memories", "original_output", nullable=False)
    op.alter_column("error_memories", "human_correction", nullable=False)
    op.create_index(
        "ix_error_memories_resolved", "error_memories", ["resolved"], unique=False
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS hnsw_idx_error "
        "ON error_memories USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "obsidian_sync_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("semantic_memory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("last_sync_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.ForeignKeyConstraint(
            ["semantic_memory_id"], ["semantic_memories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("semantic_memory_id"),
        sa.UniqueConstraint("file_path"),
    )


def downgrade() -> None:
    op.drop_table("obsidian_sync_states")

    op.execute("DROP INDEX IF EXISTS hnsw_idx_error")
    op.drop_index("ix_error_memories_resolved", table_name="error_memories")
    op.drop_column("error_memories", "embedding")
    op.drop_column("error_memories", "resolved")
    op.drop_column("error_memories", "human_correction")
    op.drop_column("error_memories", "original_output")
