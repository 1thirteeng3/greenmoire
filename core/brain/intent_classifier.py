import json
import logging
from typing import List

from pydantic import BaseModel, Field

from core.brain.model_router import ModelRouter

logger = logging.getLogger(__name__)


# ==========================================
# CONTRATO DE DADOS (SCHEMA ESTRITO)
# ==========================================
class ParsedIntent(BaseModel):
    tier: str = Field(description="O nivel de complexidade exigido: 'T1', 'T2' ou 'T3'")
    primary_intent: str = Field(
        description="A intencao principal resumida (ex: 'buscar_notas', 'gerar_codigo', 'conversa')"
    )
    requires_memory: bool = Field(
        description="True se o pedido exigir recuperacao de conhecimento do RAG ou historico."
    )
    extracted_entities: List[str] = Field(
        default_factory=list,
        description="Entidades chave identificadas no prompt.",
    )


# ==========================================
# MOTOR DE CLASSIFICACAO
# ==========================================
class IntentClassifier:
    """
    O Gatekeeper Cognitivo.
    Avalia a entrada do utilizador utilizando o modelo T1 (baixa latencia)
    para definir a rota de execucao no sistema orientado a eventos.
    """

    def __init__(self, model_router: ModelRouter):
        # Injetamos o roteador para que o classificador nao conheca chaves de API
        # ou provedores diretos.
        self.router = model_router

    async def classify_prompt(self, user_prompt: str) -> ParsedIntent:
        """Analisa o prompt e retorna uma estrutura de roteamento deterministica."""
        system_prompt = """
        Voce e o Classificador de Intencao de um Sistema Operacional Cognitivo.
        Sua unica funcao e analisar o prompt e classifica-lo em uma destas tres categorias:

        - T1 (Direct): Perguntas gerais de senso comum, saudacoes, traducoes diretas. Nao requer dados pessoais.
        - T2 (Analytical): Recuperacao de informacao pessoal. Ex: "O que eu anotei sobre X?", "Resuma o PDF Y". Requer busca na memoria.
        - T3 (Complex): Criacao, planejamento ou execucao multi-etapas. Ex: "Escreva um artigo com base nas notas", "Crie um script".

        Responda ESTRITAMENTE em formato JSON valido obedecendo ao seguinte schema:
        {"tier": "T1|T2|T3", "primary_intent": "texto", "requires_memory": true|false, "extracted_entities": ["entidade1"]}
        """
        response_text = ""
        try:
            # Acionamento estrito via T1 (baixa latencia + classificacao deterministica)
            response_text = await self.router.execute_tier(
                tier="T1",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Prompt: {user_prompt}"},
                ],
            )

            # Sanitizacao defensiva para markdown fences em modelos locais.
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            result_dict = json.loads(clean_text)
            parsed_intent = ParsedIntent(**result_dict)
            logger.info(
                "Classificacao [Tier: %s | RAG: %s]",
                parsed_intent.tier,
                parsed_intent.requires_memory,
            )
            return parsed_intent

        except json.JSONDecodeError as e:
            logger.error(
                "Falha no parse JSON do classificador: %s | Resposta crua: %s",
                e,
                response_text,
            )
            return self._get_fallback_intent()
        except Exception as e:
            logger.error("Falha de inferencia no Intent Classifier: %s", e)
            return self._get_fallback_intent()

    def _get_fallback_intent(self) -> ParsedIntent:
        """
        Fail-closed seguro: se T1 falhar em classificar adequadamente,
        assumimos o pior caso (T3 + memoria) para evitar resposta superficial.
        """
        return ParsedIntent(
            tier="T3",
            primary_intent="unclassified_fallback",
            requires_memory=True,
            extracted_entities=[],
        )
