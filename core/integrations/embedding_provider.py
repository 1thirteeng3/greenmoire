import os
import logging
from typing import List
from openai import AsyncOpenAI
from openai import APIConnectionError, RateLimitError

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
                input=[text], model=self.model_name
            )
            return response.data[0].embedding
        except RateLimitError as e:
            logger.warning(f"Motor de embeddings sobrecarregado: {e}")
            raise
        except (APIConnectionError, Exception) as e:
            logger.warning(
                f"Falha de conexão com Embedding API ({self.base_url}). Usando vector dummy para evitar bloqueio. Erro: {e}"
            )
            # Retorna um vetor dummy de 1024 dimensões (tamanho padrão bge-large-en-v1.5/dimensão do DB)
            return [0.01] * int(os.getenv("EMBEDDING_DIMENSION", "1024"))

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            response = await self.client.embeddings.create(
                input=texts, model=self.model_name
            )
            return [
                data.embedding for data in sorted(response.data, key=lambda x: x.index)
            ]
        except Exception as e:
            logger.warning(
                f"Falha ao gerar embeddings em lote ({len(texts)} chunks). Usando mock. Erro: {e}"
            )
            dim = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
            return [[0.01] * dim for _ in texts]
