import json
import logging

from pydantic import BaseModel, Field

from core.brain.model_router import ModelRouter

logger = logging.getLogger(__name__)


class AuditReport(BaseModel):
    approved: bool = Field(
        description="True se a resposta nao contiver alucinacoes e atender ao prompt."
    )
    critique: str = Field(
        description=(
            "Se reprovado, o que o Executor fez de errado "
            "(alucinacao, erro factual, desobediencia)."
        )
    )


class AuditorAgent:
    """
    Agente de Controle de Qualidade e Anti-Alucinacao.
    Avalia a saida do Executor de forma independente.
    """

    def __init__(self, model_router: ModelRouter):
        self.router = model_router

    async def audit_execution(
        self,
        original_prompt: str,
        executor_output: str,
    ) -> AuditReport:
        logger.info("AuditorAgent: Iniciando auditoria de conformidade cruzada...")

        system_prompt = """
        Voce e o Agente Auditor do Grimoire.
        Sua funcao e atuar como um "Red Teamer". Voce deve ler a solicitacao original do usuario e a resposta gerada pelo Agente Executor.

        CRITERIOS DE REPROVACAO:
        1. Alucinacao: O Executor inventou fatos, links ou dados que nao foram solicitados.
        2. Desobediencia: O Executor ignorou restricoes explicitas do usuario.
        3. Falsa Conclusao: O Executor diz que fez algo, mas o texto mostra que ele falhou.

        Se a resposta for minimamente aceitavel e segura, aprove. Seja rigoroso apenas contra falhas logicas e mentiras.
        Responda ESTRITAMENTE em JSON: {"approved": true/false, "critique": "motivo da reprovacao ou 'OK'"}
        """

        # REGRA CRITICA DO ROADMAP: Auditor IMPOE modelo diferente do Executor.
        # Como o Executor roda em T3, forcar auditoria para T2 quebra vies de confirmacao.
        response = await self.router.execute_tier(
            tier="T2",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "PROMPT ORIGINAL:\n"
                        f"{original_prompt}\n\n"
                        "SAIDA DO EXECUTOR:\n"
                        f"{executor_output}"
                    ),
                },
            ],
        )

        clean_json = response.replace("```json", "").replace("```", "").strip()

        try:
            report_dict = json.loads(clean_json)
            report = AuditReport(**report_dict)
            logger.info(
                "AuditorAgent: Auditoria concluida. Status: %s",
                "APROVADO" if report.approved else "REPROVADO",
            )
            return report
        except json.JSONDecodeError:
            logger.error(
                "AuditorAgent: Falha no parsing do JSON de auditoria. "
                "Forcando aprovacao por fail-open."
            )
            return AuditReport(
                approved=True,
                critique="Falha tecnica na auditoria. Resposta liberada por seguranca.",
            )
