import os
import logging
from typing import List
from openai import AsyncOpenAI
from openai import APIConnectionError, RateLimitError, APIStatusError

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """
    Adaptador canónico para geração de embeddings.
    Aponta estritamente para o LocalAI provisionado no docker-compose.
    """

    def __init__(self):
        # Lê do .env as variáveis unificadas.
        # Fallbacks apontam para o LocalAI padrão (porta 8080) e modelo bge-large.
        self.base_url = os.getenv("EMBEDDING_API_BASE", "http://localhost:8080/v1")
        self.api_key = os.getenv("EMBEDDING_API_KEY", "sk-localai-dummy")
        self.model_name = os.getenv("EMBEDDING_MODEL", "bge-large")

        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            max_retries=1,
            timeout=15.0,  # Timeout estrito para evitar bloqueio do Worker
        )
        logger.info(
            "EmbeddingProvider inicializado. Endpoint: %s | Modelo: %s",
            self.base_url,
            self.model_name,
        )

    async def generate_embedding(self, text: str) -> List[float]:
        try:
            response = await self.client.embeddings.create(
                input=[text],
                model=self.model_name
            )
            return response.data[0].embedding
        except RateLimitError as e:
            logger.warning(f"Motor de embeddings sobrecarregado: {e}")
            raise
        except APIConnectionError as e:
            logger.error(f"Falha de conexão com LocalAI em {self.base_url}: {e}")
            raise
        except APIStatusError as e:
            logger.error(f"Erro no motor de embeddings. Status: {e.status_code}")
            raise

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=self.model_name
            )
            return [data.embedding for data in sorted(response.data, key=lambda x: x.index)]
        except Exception as e:
            logger.error(f"Falha ao gerar embeddings em lote ({len(texts)} chunks): {e}")
            raise
