import os
import logging
from typing import List
from openai import AsyncOpenAI
from openai import APIConnectionError, RateLimitError, APIStatusError

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """
    Adaptador enxuto para geração de embeddings.
    Aponta para o Infinity (local) por padrão, mas é compatível com a API da OpenAI.
    Não implementa backoff prolongado para não bloquear workers assíncronos.
    """

    def __init__(self):
        # Lê do .env. Se não existir, assume o container local do Infinity.
        self.base_url = os.getenv("EMBEDDING_API_BASE", "http://localhost:7997/v1")
        # A chave de API não é necessária para o Infinity local, mas o cliente OpenAI exige uma string não vazia.
        self.api_key = os.getenv("EMBEDDING_API_KEY", "sk-local-infinity")
        self.model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")

        # Cliente assíncrono oficial. max_retries=1 lida com falhas de TCP instáveis de curtíssima duração (milissegundos),
        # mas não faz backoff longo (segundos/minutos) para erros 503 ou Rate Limits.
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            max_retries=1,
            timeout=10.0,  # Timeout estrito: Se o motor travar, o worker se liberta em 10s.
        )

    async def generate_embedding(self, text: str) -> List[float]:
        """Gera um único vetor a partir de um texto."""
        try:
            response = await self.client.embeddings.create(
                input=[text],
                model=self.model_name,
            )
            return response.data[0].embedding

        except RateLimitError as e:
            logger.warning(f"Motor de embeddings sobrecarregado (Rate Limit/OOM transiente): {e}")
            raise  # Propaga para o Worker gerenciar a falha (PEL/DLQ)
        except APIConnectionError as e:
            logger.error(f"Falha de conexão com o motor de embeddings ({self.base_url}): {e}")
            raise
        except APIStatusError as e:
            logger.error(f"Erro no motor de embeddings. Status: {e.status_code}, Resposta: {e.response}")
            raise

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings em lote para otimizar o I/O do motor local.
        Crucial para o RAGService ao processar um documento chunked.
        """
        if not texts:
            return []

        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=self.model_name,
            )
            # Retorna a lista de vetores mantendo a ordem exata do array de entrada
            return [data.embedding for data in sorted(response.data, key=lambda x: x.index)]

        except Exception as e:
            logger.error(f"Falha ao gerar embeddings em lote ({len(texts)} chunks): {e}")
            raise
