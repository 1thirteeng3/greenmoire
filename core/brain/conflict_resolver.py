import json
import logging
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.brain.model_router import ModelRouter
from core.integrations.embedding_provider import EmbeddingProvider
from core.repositories.memory_repository import MemoryRepository

logger = logging.getLogger(__name__)


# ==========================================
# CONTRATOS DE DADOS DO RESOLVEDOR
# ==========================================


class ConflictReport(BaseModel):
    has_conflict: bool = Field(
        description="True se a solicitacao violar uma regra de calibracao passada."
    )
    reason: str = Field(description="Explicacao da violacao e diretiva de correcao.")


# ==========================================
# NÚCLEO DO PROTOCOLO DE DETEÇÃO
# ==========================================


class ConflictResolver:
    """
    Guardiao de calibracao.
    Avalia se o prompt atual entra em conflito com regras de comportamento
    corrigidas no passado (ErrorMemory), utilizando o roteador agnostico.
    """

    def __init__(
        self, embedding_provider: EmbeddingProvider, model_router: ModelRouter
    ):
        self.embedding_provider = embedding_provider
        self.router = model_router

    async def evaluate_proposal(
        self, user_prompt: str, session: AsyncSession
    ) -> Optional[ConflictReport]:
        """
        1) Vetoriza o prompt.
        2) Busca regras de calibracao semanticamente similares no banco.
        3) Usa LLM via ModelRouter (T2) para avaliar conflito logico.
        """
        try:
            prompt_emb = await self.embedding_provider.generate_embedding(user_prompt)
            repo = MemoryRepository(session)

            active_rules = await repo.search_error_memory(prompt_emb, limit=3)
            if not active_rules:
                return None

            rules_text = "\n".join(
                [
                    f"- Erro: {rule.original_output} | Correcao: {rule.human_correction}"
                    for rule in active_rules
                ]
            )

            system_prompt = f"""
            Voce e um Auditor de Conformidade.
            O usuario fez a seguinte solicitacao: "{user_prompt}"

            No passado, o usuario estabeleceu as seguintes regras estritas de comportamento:
            {rules_text}

            Avalie se a solicitacao atual exige a aplicacao destas regras.
            Responda ESTRITAMENTE em JSON:
            {{"has_conflict": true/false, "reason": "motivo e como o sistema deve agir"}}
            """

            response_text = await self.router.execute_tier(
                tier="T2",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Avalie o conflito."},
                ],
            )

            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            result_dict = json.loads(clean_text)
            report = ConflictReport(**result_dict)

            if report.has_conflict:
                logger.info(
                    f"ConflictResolver: Conflito detectado! Motivo: {report.reason}"
                )
            return report

        except Exception as e:
            logger.error(f"Falha ao avaliar conflitos de calibracao: {e}")
            # Fail-open: se o auditor falhar, nao trava o sistema.
            return None
