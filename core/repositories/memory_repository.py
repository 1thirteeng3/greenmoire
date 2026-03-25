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

    async def save_episodic_event(self, trace_id: str, content: str, participants: List[str]) -> EpisodicMemory:
        memory = EpisodicMemory(
            trace_id=trace_id,
            content=content,
            participants=participants,
            metadata_json={"trace_id": trace_id},
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def log_hallucination_or_error(
        self,
        original_output: str,
        human_correction: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[dict] = None,
    ) -> ErrorMemory:
        error_mem = ErrorMemory(
            original_output=original_output,
            human_correction=human_correction,
            embedding=embedding,
            resolved=False,
            metadata_json=metadata or {},
        )
        self.session.add(error_mem)
        await self.session.flush()
        return error_mem

    async def search_relevant_errors(
        self,
        query_embedding: List[float],
        limit: int = 5,
        similarity_threshold: float = 0.6,
    ) -> List[Tuple[ErrorMemory, float]]:
        """Busca erros passados não resolvidos semanticamente similares."""
        distance_expr = ErrorMemory.embedding.cosine_distance(query_embedding)
        similarity_expr = (1.0 - distance_expr).label("similarity_score")

        stmt = select(ErrorMemory, similarity_expr).where(
            and_(
                ErrorMemory.resolved == False,  # noqa: E712
                ErrorMemory.embedding.is_not(None),
                similarity_expr >= similarity_threshold,
            )
        ).order_by(desc(similarity_expr)).limit(limit)

        result = await self.session.execute(stmt)
        return [(row.ErrorMemory, float(row.similarity_score)) for row in result]

    async def search_error_memory(
        self,
        query_embedding: List[float],
        limit: int = 3,
        similarity_threshold: float = 0.6,
    ) -> List[ErrorMemory]:
        """
        Busca regras de calibração semânticas para auditoria de conflito.
        Retorna apenas entidades ErrorMemory (sem score), para consumo do ConflictResolver.
        """
        results = await self.search_relevant_errors(
            query_embedding=query_embedding,
            limit=limit,
            similarity_threshold=similarity_threshold,
        )
        return [error for error, _score in results]
