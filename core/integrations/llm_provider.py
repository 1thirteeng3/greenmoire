import os
import json
import logging
from typing import List, Dict, Any, Optional, Union

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


class LLMProvider:
    """
    Adaptador Universal para Modelos de Linguagem com Suporte a Function Calling.
    Garante que as diferencas de API entre provedores sejam invisiveis para o Orquestrador.
    """

    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("VLM_API_KEY", ""))
        self.localai_client = AsyncOpenAI(
            base_url=os.getenv("EMBEDDING_API_BASE", "http://localhost:8080/v1"),
            api_key=os.getenv("EMBEDDING_API_KEY", "sk-localai-dummy"),
        )

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
        """Roteia a inferencia e gerencia traducoes de schemas de ferramentas."""
        provider = provider.lower()

        try:
            if provider == "openai":
                return await self._call_openai(
                    self.openai_client,
                    model,
                    messages,
                    temperature,
                    max_tokens,
                    tools,
                )
            if provider == "localai":
                return await self._call_openai(
                    self.localai_client,
                    model,
                    messages,
                    temperature,
                    max_tokens,
                    tools,
                )
            if provider == "anthropic":
                if not self.anthropic_client:
                    raise ValueError("Anthropic API Key nao configurada.")
                return await self._call_anthropic(model, messages, temperature, max_tokens, tools)
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
        # A OpenAI e LocalAI aceitam o schema padrao nativamente
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        # Se houver chamada de ferramenta, normalizamos a saida
        if message.tool_calls:
            return {
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,  # String JSON
                        },
                    }
                    for tc in message.tool_calls
                ],
            }

        return message.content.strip() if message.content else ""

    async def _call_anthropic(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[str, Dict[str, Any]]:
        system_prompt = ""
        anthropic_messages: List[Dict[str, Any]] = []

        # 1. Tratamento de mensagens e system prompt
        for msg in messages:
            if msg["role"] == "system":
                system_prompt += msg["content"] + "\n"
            else:
                role = msg["role"] if msg["role"] in ["user", "assistant"] else "user"
                anthropic_messages.append({"role": role, "content": msg.get("content", "")})

        kwargs: Dict[str, Any] = {
            "model": model,
            "system": system_prompt.strip(),
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # 2. Traducao rigorosa do schema de ferramentas (OpenAI -> Anthropic)
        if tools:
            anthropic_tools = []
            for t in tools:
                if t.get("type") == "function":
                    func = t["function"]
                    anthropic_tools.append(
                        {
                            "name": func["name"],
                            "description": func["description"],
                            "input_schema": func["parameters"],
                        }
                    )
            kwargs["tools"] = anthropic_tools

        response = await self.anthropic_client.messages.create(**kwargs)

        # 3. Mapeamento reverso da resposta (Anthropic -> padrao OpenAI)
        tool_calls = []
        text_content = ""

        for block in response.content:
            if block.type == "text":
                text_content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "function": {
                            "name": block.name,
                            # Anthropic retorna dict; padronizamos para string JSON
                            "arguments": json.dumps(block.input),
                        },
                    }
                )

        if tool_calls:
            return {"content": text_content.strip(), "tool_calls": tool_calls}

        return text_content.strip()
