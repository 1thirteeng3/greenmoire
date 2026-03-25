import logging
from typing import Any, Dict, List, Union

from core.brain.tier_engine import TierEngine
from core.integrations.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ModelRouter:
    """Roteador de execução que consome políticas do TierEngine."""

    def __init__(self, llm_provider: LLMProvider, tier_engine: TierEngine):
        self.provider = llm_provider
        self.engine = tier_engine

    async def execute_tier(
        self,
        tier: str,
        messages: List[Dict[str, Any]],
    ) -> str:
        """Execução padrão sem ferramentas (T1/T2)."""
        policy = self.engine.get_policy(tier)
        logger.debug(f"ModelRouter: Executando {tier} via {policy.provider} ({policy.model})")

        result = await self.provider.generate_completion(
            provider=policy.provider,
            model=policy.model,
            messages=messages,
            temperature=policy.temperature,
            max_tokens=policy.max_tokens,
        )
        return result if isinstance(result, str) else result.get("content", "")

    async def execute_tier_with_tools(
        self,
        tier: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> Union[str, Dict[str, Any]]:
        """Execução avançada para T3 com suporte a ferramentas."""
        policy = self.engine.get_policy(tier)

        if not policy.allows_tools:
            logger.warning(
                f"Tentativa de usar ferramentas na camada {tier}, que nao permite. "
                "As ferramentas serao ignoradas."
            )
            return await self.execute_tier(tier, messages)

        return await self.provider.generate_completion(
            provider=policy.provider,
            model=policy.model,
            messages=messages,
            temperature=policy.temperature,
            max_tokens=policy.max_tokens,
            tools=tools,
        )
