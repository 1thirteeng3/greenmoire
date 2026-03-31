"""add memory_entries table

Revision ID: 20260325_0002
Revises: 20260324_0001
Create Date: 2026-03-25 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260325_0002"
down_revision: Union[str, None] = "20260324_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    memory_type_enum = sa.Enum(
        "EPISODIC",
        "SEMANTIC",
        "ERROR",
        "PERSONAL",
        name="memorytype",
    )
    memory_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "memory_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("memory_type", memory_type_enum, nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column(
            "metadata_json",
            sa.JSON(),
            nullable=True,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_user_validated", sa.Boolean(), nullable=True),
        sa.Column("user_annotation", sa.String(), nullable=True),
        sa.Column("sync_hash", sa.String(), nullable=True),
        sa.Column("is_synced", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_memory_entries_memory_type", "memory_entries", ["memory_type"], unique=False
    )
    op.create_index(
        "ix_memory_entries_created_at", "memory_entries", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_memory_entries_created_at", table_name="memory_entries")
    op.drop_index("ix_memory_entries_memory_type", table_name="memory_entries")
    op.drop_table("memory_entries")

    memory_type_enum = sa.Enum(
        "EPISODIC",
        "SEMANTIC",
        "ERROR",
        "PERSONAL",
        name="memorytype",
    )
    memory_type_enum.drop(op.get_bind(), checkfirst=True)
