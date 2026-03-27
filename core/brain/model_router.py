import asyncio
import logging
from typing import Any, Dict, List, Union

from core.brain.tier_engine import TierEngine
from core.integrations.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Roteador de Modelos com Enforcement Estrito de Políticas (Timeouts e Custos).
    """

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
        logger.debug(
            f"Router: Executando {tier} ({policy.model}). Timeout: {policy.timeout_seconds}s"
        )

        try:
            result = await asyncio.wait_for(
                self.provider.generate_completion(
                    provider=policy.provider,
                    model=policy.model,
                    messages=messages,
                    temperature=policy.temperature,
                    max_tokens=policy.max_tokens,
                ),
                timeout=policy.timeout_seconds,
            )
            return result if isinstance(result, str) else result.get("content", "")
        except asyncio.TimeoutError:
            logger.error(
                f"Timeout Critico: Camada {tier} excedeu {policy.timeout_seconds} segundos."
            )
            return '{"error": "timeout", "message": "O modelo excedeu o tempo limite de resposta."}'

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
                f"Camada {tier} nao permite uso de tools. Fallback para texto plano."
            )
            return await self.execute_tier(tier, messages)

        try:
            return await asyncio.wait_for(
                self.provider.generate_completion(
                    provider=policy.provider,
                    model=policy.model,
                    messages=messages,
                    temperature=policy.temperature,
                    max_tokens=policy.max_tokens,
                    tools=tools,
                ),
                timeout=policy.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Timeout Critico (Tools): Camada {tier} excedeu {policy.timeout_seconds} segundos."
            )
            return {
                "content": "Ocorreu um timeout do sistema durante o raciocinio agentic. Acao abortada.",
                "tool_calls": [],
            }
