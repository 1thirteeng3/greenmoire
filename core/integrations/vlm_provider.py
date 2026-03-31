import os
import base64
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class VLMProvider:
    """
    Adaptador híbrido para Modelos de Visão (VLM).
    Roteia as requisições para a OpenAI (Cloud) ou LocalAI (Offline) com base no ambiente,
    mantendo o contrato da aplicação estritamente idêntico.
    """

    def __init__(self):
        # A escolha do provedor dita a configuração do cliente
        self.provider_type = os.getenv("VLM_PROVIDER", "openai").lower()

        if self.provider_type == "localai":
            self.base_url = os.getenv("VLM_BASE_URL", "http://localhost:8080/v1")
            self.api_key = os.getenv("VLM_API_KEY", "sk-localai-dummy")
            self.model_name = os.getenv(
                "VLM_MODEL_NAME", "llava"
            )  # Modelo VLM padrão no LocalAI
            self.timeout = (
                120.0  # Timeout estendido: VLMs locais são pesados e demorados
            )
        else:
            self.base_url = os.getenv("VLM_BASE_URL", "https://api.openai.com/v1")
            self.api_key = os.getenv("VLM_API_KEY", "")
            self.model_name = os.getenv("VLM_MODEL_NAME", "gpt-4o-mini")
            self.timeout = 30.0  # Timeout padrão para APIs na nuvem

        if not self.api_key and self.provider_type == "openai":
            logger.warning(
                "VLM_PROVIDER está configurado para 'openai', mas a VLM_API_KEY não foi fornecida."
            )

        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            max_retries=1,
            timeout=self.timeout,
        )

        logger.info(
            f"VLMProvider inicializado. Roteamento: {self.provider_type.upper()} | Modelo: {self.model_name}"
        )

    def _encode_image(self, image_path: str) -> str:
        """Converte imagem local para Base64."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    async def describe_image(self, image_path: str) -> str:
        """
        Envia a imagem para o VLM configurado e retorna a descrição semântica.
        """
        try:
            base64_image = self._encode_image(image_path)

            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Você é um extrator de dados rigoroso. Descreva esta imagem em detalhes. "
                                    "Se for um gráfico ou diagrama, extraia os dados e explique as tendências. "
                                    "Se contiver texto legível, transcreva-o. Seja técnico e objetivo."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=500,
                temperature=0.1,  # Prioriza extração factual em vez de criatividade
            )
            description = response.choices[0].message.content.strip()
            return f"\n> [Descrição Semântica Extratada da Imagem: {description}]\n"

        except Exception as e:
            logger.error(
                f"Falha na inferência VLM ({self.provider_type}) para a imagem {image_path}: {e}"
            )
            # Em vez de quebrar a ingestão inteira por causa de uma imagem, deixamos um marcador de falha
            return "\n> [Erro de Extração Visual: Imagem não processada devido a falha no VLM]\n"
