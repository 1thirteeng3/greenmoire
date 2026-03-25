from typing import List, Optional, Tuple
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.models.memory_models import SemanticMemory, EpisodicMemory, ErrorMemory


class MemoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_semantic_memory(self, content: str, embedding: List[float], domain: str, metadata: dict = None, human_verified: bool = False) -> SemanticMemory:
        memory = SemanticMemory(content=content, embedding=embedding, domain=domain, metadata_json=metadata or {}, human_verified=human_verified)
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def search_semantic_memory(self, query_embedding: List[float], domain: Optional[str] = None, limit: int = 5, similarity_threshold: float = 0.75) -> List[Tuple[SemanticMemory, float]]:
        distance_expr = SemanticMemory.embedding.cosine_distance(query_embedding)
        similarity_expr = (1.0 - distance_expr).label("similarity_score")
        stmt = select(SemanticMemory, similarity_expr)
        if domain:
            stmt = stmt.where(SemanticMemory.domain == domain)
        stmt = stmt.where(similarity_expr >= similarity_threshold).order_by(desc(similarity_expr)).limit(limit)
        result = await self.session.execute(stmt)
        return [(row.SemanticMemory, float(row.similarity_score)) for row in result]
