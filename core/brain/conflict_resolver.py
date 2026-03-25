import json
import logging
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from core.repositories.memory_repository import MemoryRepository
from core.integrations.embedding_provider import EmbeddingProvider
from core.models.memory_models import SemanticMemory, ErrorMemory

logger = logging.getLogger(__name__)


# ==========================================
# CONTRATOS DE DADOS DO RESOLVEDOR
# ==========================================

class ConflictReport(BaseModel):
    has_conflict: bool = Field(description="True se a proposta violar memórias de alta autoridade.")
    conflict_type: Optional[str] = Field(description="'PERSONAL_OVERRIDE' ou 'REPEATED_ERROR', None se não houver.")
    reason: str = Field(description="Justificação lógica da colisão gerada pelo LLM.")
    conflicting_memory_ids: List[str] = Field(default_factory=list)


# ==========================================
# NÚCLEO DO PROTOCOLO DE DETEÇÃO
# ==========================================

class ConflictResolver:
    """
    Guardião da Soberania Cognitiva. Avalia propostas de agentes contra a memória
    humana verificada e o registo histórico de erros (calibração).
    """

    def __init__(self, embedding_provider: EmbeddingProvider, llm_client: AsyncOpenAI):
        self.embedding_provider = embedding_provider
        self.llm_client = llm_client
        # Modelo ideal para julgamento rápido (T1 Tier). Pode apontar para o LocalAI.
        self.judge_model = "llama-3-8b-instruct"

    async def evaluate_proposal(self, proposed_content: str, session: AsyncSession) -> ConflictReport:
        """
        Executa o pipeline completo de deteção de conflitos.
        """
        repository = MemoryRepository(session)

        # 1. Vetorizar a proposta
        proposed_embedding = await self.embedding_provider.generate_embedding(proposed_content)

        # 2. Buscar Âncoras de Alta Autoridade (Personal > Error)
        verified_memories = await self._fetch_verified_personal_data(proposed_embedding, repository)
        known_errors = await self._fetch_unresolved_errors(proposed_embedding, session)

        if not verified_memories and not known_errors:
            # Sem âncoras semânticas próximas na zona de alta autoridade. Caminho livre (RAG ganha).
            return ConflictReport(has_conflict=False, reason="Nenhuma memória de alta autoridade relacionada encontrada.")

        # 3. Arbitragem Lógica via LLM (Deteção de Contradição)
        report = await self._judge_contradiction(proposed_content, verified_memories, known_errors)

        if report.has_conflict:
            logger.warning(f"Conflito Detetado: {report.conflict_type} - {report.reason}")

        return report

    async def _fetch_verified_personal_data(self, embedding: List[float], repository: MemoryRepository) -> List[Tuple[str, str]]:
        """Recupera APENAS memórias com human_verified=True que sejam semanticamente similares."""
        # Busca customizada no repositório filtrando pelo flag de autoridade
        stmt = select(SemanticMemory).where(
            and_(
                SemanticMemory.human_verified == True,
                SemanticMemory.embedding.cosine_distance(embedding) < 0.25,  # Threshold rigoroso (alta similaridade)
            )
        ).limit(3)

        result = await repository.session.execute(stmt)
        memories = result.scalars().all()
        return [(str(m.id), m.content) for m in memories]

    async def _fetch_unresolved_errors(self, embedding: List[float], session: AsyncSession) -> List[Tuple[str, str, str]]:
        """Recupera erros passados para evitar repetição (Calibração)."""
        # Nota: ErrorMemory não tem vetor por padrão no nosso schema para economizar VRAM,
        # mas faremos uma busca textual ou precisaremos adicionar vetor à tabela de erro no futuro.
        # Para manter a precisão atual, faremos uma query direta aos não resolvidos.
        stmt = select(ErrorMemory).where(ErrorMemory.resolved == False).order_by(ErrorMemory.created_at.desc()).limit(5)
        result = await session.execute(stmt)
        errors = result.scalars().all()
        return [(str(e.id), e.original_output, e.human_correction) for e in errors]

    async def _judge_contradiction(
        self,
        proposal: str,
        verified_memories: List[Tuple[str, str]],
        known_errors: List[Tuple[str, str, str]],
    ) -> ConflictReport:
        """Delega a avaliação de contradição ao motor inferencial."""

        personal_context = "\n".join([f"- ID: {m[0]} | Fato: {m[1]}" for m in verified_memories])
        error_context = "\n".join([f"- Erro a evitar: {e[1]} | Correção exigida: {e[2]}" for e in known_errors])

        system_prompt = f"""
        Você é o Guardião de Conflitos de um Sistema Operacional Cognitivo.
        Sua única função é comparar uma [Ação/Fato Proposto] com a [Memória Verificada] e os [Erros Passados].

        REGRAS DE AUTORIDADE:
        1. Se a proposta contradizer a Memória Verificada, a Memória Verificada VENCE (PERSONAL_OVERRIDE).
        2. Se a proposta repetir um Erro Passado ignorando a Correção, o Erro VENCE (REPEATED_ERROR).
        3. Se a proposta for apenas complementar e não contraditória, NÃO HÁ CONFLITO.

        [Memória Verificada (Verdade Absoluta)]:
        {personal_context or "Nenhuma."}

        [Erros Passados (Não repetir)]:
        {error_context or "Nenhum."}

        Responda ESTRITAMENTE em formato JSON com o schema:
        {{"has_conflict": boolean, "conflict_type": "PERSONAL_OVERRIDE" | "REPEATED_ERROR" | null, "reason": "explicação concisa", "conflicting_memory_ids": ["id1", "id2"]}}
        """

        try:
            response = await self.llm_client.chat.completions.create(
                model=self.judge_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"[Ação/Fato Proposto]:\n{proposal}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,  # Determinismo máximo
            )

            result_dict = json.loads(response.choices[0].message.content)
            return ConflictReport(**result_dict)

        except Exception as e:
            logger.error(f"Falha na inferência de conflito. Assumindo conflito preventivo. Erro: {e}")
            # Failsafe: Se o juiz falhar, bloqueamos por segurança (Fail Closed).
            return ConflictReport(
                has_conflict=True,
                conflict_type="SYSTEM_ERROR",
                reason="Falha no motor de validação. Ação bloqueada preventivamente.",
                conflicting_memory_ids=[],
            )
