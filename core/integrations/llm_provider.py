import os
import logging
from typing import List, Dict, Any, Optional, Union

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMProvider:
    """
    Adaptador Universal para Modelos de Linguagem.
    Padroniza chamadas para OpenAI, Anthropic e LocalAI usando a mesma interface de mensagens.
    """

    def __init__(self):
        # Cliente OpenAI (Cloud)
        self.openai_client = AsyncOpenAI(api_key=os.getenv("VLM_API_KEY", ""))

        # Cliente LocalAI (OpenAI-compatible)
        self.localai_client = AsyncOpenAI(
            base_url=os.getenv("EMBEDDING_API_BASE", "http://localhost:8080/v1"),
            api_key=os.getenv("EMBEDDING_API_KEY", "sk-localai-dummy"),
        )

        # Cliente Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_key) if anthropic_key else None

    async def generate_completion(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[str, Dict[str, Any]]:
        """Roteia a chamada para o SDK correto baseando-se no provedor solicitado."""
        provider = provider.lower()

        try:
            if provider == "openai":
                return await self._call_openai(
                    self.openai_client,
                    model,
                    messages,
                    temperature,
                    max_tokens,
                    tools=tools,
                )
            if provider == "localai":
                return await self._call_openai(
                    self.localai_client,
                    model,
                    messages,
                    temperature,
                    max_tokens,
                    tools=tools,
                )
            if provider == "anthropic":
                if not self.anthropic_client:
                    raise ValueError("Anthropic API Key nao configurada.")
                return await self._call_anthropic(model, messages, temperature, max_tokens)

            raise ValueError(f"Provedor LLM nao suportado: {provider}")
        except Exception as e:
            logger.error(f"Falha na inferencia LLM ({provider}/{model}): {e}")
            raise

    async def _call_openai(
        self,
        client: AsyncOpenAI,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[str, Dict[str, Any]]:
        """Chamada padrao compativel com OpenAI e LocalAI."""
        request_payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            request_payload["tools"] = tools

        response = await client.chat.completions.create(**request_payload)
        message = response.choices[0].message

        if getattr(message, "tool_calls", None):
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
            return {"content": message.content, "tool_calls": tool_calls}

        return (message.content or "").strip()

    async def _call_anthropic(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Traduz o formato de mensagens da OpenAI para o formato da Anthropic."""
        system_prompt = ""
        anthropic_messages: List[Dict[str, str]] = []

        for msg in messages:
            if msg["role"] == "system":
                system_prompt += msg["content"] + "\n"
            else:
                role = msg["role"] if msg["role"] in ["user", "assistant"] else "user"
                anthropic_messages.append({"role": role, "content": msg["content"]})

        response = await self.anthropic_client.messages.create(
            model=model,
            system=system_prompt.strip(),
            messages=anthropic_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        chunks = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                chunks.append(text)
        return "".join(chunks).strip()
