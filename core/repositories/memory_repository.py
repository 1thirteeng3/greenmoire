from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select

from core.models.memory_models import MemoryEntry, MemoryType


class MemoryRepository:
    def __init__(self, db_session):
        self.db = db_session

    def save_memory(self, memory: MemoryEntry) -> MemoryEntry:
        # Lógica de upsert e commit
        existing = self.db.get(MemoryEntry, memory.id)
        if existing:
            existing.memory_type = memory.memory_type
            existing.content = memory.content
            existing.metadata_json = memory.metadata_json
            existing.is_user_validated = memory.is_user_validated
            existing.user_annotation = memory.user_annotation
            existing.sync_hash = memory.sync_hash
            existing.is_synced = memory.is_synced
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def get_error_memories(self, trace_id: Optional[str] = None) -> List[MemoryEntry]:
        # Retorna memórias de erro, priorizando as não resolvidas/validadas
        query = self.db.query(MemoryEntry).filter(MemoryEntry.memory_type == MemoryType.ERROR)
        if trace_id:
            query = query.filter(MemoryEntry.metadata_json["trace_id"].astext == trace_id)
        query = query.order_by(MemoryEntry.is_user_validated.asc(), MemoryEntry.updated_at.desc())
        return query.all()

    def fetch_context(self, query_embedding: list, limit: int = 5) -> List[MemoryEntry]:
        # Busca vetorial no PGVector (se aplicável localmente) ou resgate por tags
        _ = query_embedding  # Placeholder até conexão com busca vetorial dedicada.
        return self.db.query(MemoryEntry).order_by(MemoryEntry.updated_at.desc()).limit(limit).all()
