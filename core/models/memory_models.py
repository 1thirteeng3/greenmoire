from sqlalchemy import Column, String, JSON, DateTime, Enum, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class MemoryType(enum.Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    ERROR = "error"
    PERSONAL = "personal"


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id = Column(String, primary_key=True)  # UUID ou Hash
    memory_type = Column(Enum(MemoryType), nullable=False)
    content = Column(String, nullable=False)
    metadata_json = Column(JSON, default=dict)  # Tags, source, trace_id
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Específico para Error Memory (Governança humana)
    is_user_validated = Column(Boolean, default=False)
    user_annotation = Column(String, nullable=True)

    # Específico para Sync (Obsidian)
    sync_hash = Column(String, nullable=True)
    is_synced = Column(Boolean, default=False)
