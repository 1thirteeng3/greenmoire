import logging
import os

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class TierPolicy(BaseModel):
    tier_name: str
    provider: str
    model: str
    max_tokens: int
    temperature: float
    allows_tools: bool
    timeout_seconds: int


class TierEngine:
    """
    Motor de Politicas de Camada (Tier Engine).
    Centraliza regras de negocio, limites de custo e restricoes operacionais por camada.
    """

    def __init__(self):
        self.t1_provider = os.getenv("ROUTER_T1_PROVIDER", "openai")
        self.t1_model = os.getenv("ROUTER_T1_MODEL", "deepseek-chat")

        self.t2_provider = os.getenv("ROUTER_T2_PROVIDER", "openai")
        self.t2_model = os.getenv("ROUTER_T2_MODEL", "deepseek-chat")

        self.t3_provider = os.getenv("ROUTER_T3_PROVIDER", "openai")
        self.t3_model = os.getenv("ROUTER_T3_MODEL", "deepseek-coder")

    def get_policy(self, tier: str) -> TierPolicy:
        """Retorna politica estrita de execucao para a camada solicitada."""
        tier = tier.upper()

        if tier == "T1":
            return TierPolicy(
                tier_name="T1",
                provider=self.t1_provider,
                model=self.t1_model,
                max_tokens=500,
                temperature=0.0,
                allows_tools=False,
                timeout_seconds=10,
            )
        if tier == "T2":
            return TierPolicy(
                tier_name="T2",
                provider=self.t2_provider,
                model=self.t2_model,
                max_tokens=1500,
                temperature=0.2,
                allows_tools=False,
                timeout_seconds=30,
            )
        if tier == "T3":
            return TierPolicy(
                tier_name="T3",
                provider=self.t3_provider,
                model=self.t3_model,
                max_tokens=4096,
                temperature=0.3,
                allows_tools=True,
                timeout_seconds=120,
            )

        logger.warning(
            "TierEngine: Camada desconhecida '%s'. Aplicando politica de seguranca (T2).",
            tier,
        )
        return self.get_policy("T2")
