import os
import logging
from typing import Any, Dict, List, Tuple

from core.integrations.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Roteador de Camadas (Tiers).
    Mapeia a complexidade cognitiva (T1, T2, T3) para o modelo e provedor definidos no ambiente.
    """

    def __init__(self, llm_provider: LLMProvider):
        self.provider = llm_provider

        # Mapeamento dinâmico baseado no .env
        self.routing_table = {
            "T1": {
                "provider": os.getenv("ROUTER_T1_PROVIDER", "localai"),
                "model": os.getenv("ROUTER_T1_MODEL", "llama-3-8b-instruct"),
            },
            "T2": {
                "provider": os.getenv("ROUTER_T2_PROVIDER", "openai"),
                "model": os.getenv("ROUTER_T2_MODEL", "gpt-4o-mini"),
            },
            "T3": {
                "provider": os.getenv("ROUTER_T3_PROVIDER", "anthropic"),
                "model": os.getenv("ROUTER_T3_MODEL", "claude-3-5-sonnet-latest"),
            },
        }

    def get_route_for_tier(self, tier: str) -> Tuple[str, str]:
        """Retorna o (provedor, modelo) configurado para a camada solicitada."""
        route = self.routing_table.get(tier.upper())
        if not route:
            logger.warning(f"Tier desconhecido: {tier}. Realizando fallback para T2.")
            route = self.routing_table["T2"]

        return route["provider"], route["model"]

    async def execute_tier(
        self,
        tier: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        """
        Executa uma inferência delegando a escolha do modelo à tabela de roteamento.
        """
        provider, model = self.get_route_for_tier(tier)
        logger.debug(f"Executando Tarefa {tier} via {provider.upper()} ({model})")

        # O adaptador LLMProvider lida com as nuances de cada API subjacente
        return await self.provider.generate_completion(
            provider=provider,
            model=model,
            messages=messages,
            temperature=temperature,
        )

    async def execute_tier_with_tools(
        self,
        tier: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: float = 0.2,
    ) -> Any:
        """
        Executa inferência com catálogo de ferramentas habilitado.
        Retorna texto final ou payload estruturado com tool_calls.
        """
        provider, model = self.get_route_for_tier(tier)
        logger.debug(f"Executando Tarefa {tier} com tools via {provider.upper()} ({model})")

        return await self.provider.generate_completion(
            provider=provider,
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
        )
