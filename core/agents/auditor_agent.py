import json
import logging

from pydantic import BaseModel, Field, ValidationError

from core.brain.model_router import ModelRouter
from core.brain.tier_engine import TierEngine

logger = logging.getLogger(__name__)


class AuditReport(BaseModel):
    approved: bool = Field(
        description="True se a resposta nao contiver alucinacoes e atender ao prompt original."
    )
    critique: str = Field(
        description=(
            "Se reprovado, aponte objetivamente o que o Executor fez "
            "de errado (alucinacao, desobediencia, omissao)."
        )
    )


class AuditorAgent:
    """
    Agente de Controle de Qualidade e Anti-Alucinacao (Red Teamer).
    Garante matematicamente que a auditoria seja feita por modelo diferente do executor.
    """

    def __init__(self, model_router: ModelRouter, tier_engine: TierEngine):
        self.router = model_router
        self.engine = tier_engine

    def _get_strict_auditor_tier(self, executor_tier: str) -> str:
        """
        Enforcement estrito: seleciona uma camada com modelo divergente do executor.
        """
        executor_policy = self.engine.get_policy(executor_tier)
        executor_sig = (executor_policy.provider, executor_policy.model)

        for candidate_tier in ["T1", "T2", "T3"]:
            if candidate_tier == executor_tier:
                continue

            candidate_policy = self.engine.get_policy(candidate_tier)
            candidate_sig = (candidate_policy.provider, candidate_policy.model)
            if candidate_sig != executor_sig:
                logger.debug(
                    "AuditorAgent: Assinatura divergente encontrada. Executor%s vs Auditor%s",
                    executor_sig,
                    candidate_sig,
                )
                return candidate_tier

        # Fallback de governanca caso todos os tiers tenham a mesma assinatura.
        logger.warning(
            "ALERTA CRITICO DE GOVERNANCA: Todos os Tiers do sistema possuem a mesma "
            "assinatura de modelo. O vies de confirmacao nao pode ser evitado."
        )
        return "T2" if executor_tier == "T3" else "T3"

    async def audit_execution(
        self,
        original_prompt: str,
        executor_output: str,
        executor_tier: str = "T3",
    ) -> AuditReport:
        # 1. Enforcement de roteamento cruzado.
        auditor_tier = self._get_strict_auditor_tier(executor_tier)
        logger.info(
            "AuditorAgent: Iniciando auditoria cruzada estrita na camada %s.",
            auditor_tier,
        )

        system_prompt = """
        Voce e o Agente Auditor de um Sistema Operacional Cognitivo.
        Sua funcao e atuar como um "Red Teamer" implacavel. Leia a solicitacao original do usuario e a resposta gerada pelo Agente Executor.

        CRITERIOS DE REPROVACAO:
        1. Alucinacao: O Executor inventou fatos, caminhos de arquivos ou dados que nao existem no contexto ou na solicitacao.
        2. Desobediencia: O Executor ignorou restricoes explicitas do usuario.
        3. Falsa Conclusao: O Executor afirma ter resolvido o problema, mas a saida demonstra o contrario.

        Seja justo, mas nao seja tolerante com mentiras logicas.
        Responda ESTRITAMENTE em formato JSON: {"approved": true/false, "critique": "motivo objetivo da reprovacao ou 'OK'"}
        """

        # 2. Execucao da auditoria.
        response = await self.router.execute_tier(
            tier=auditor_tier,
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
                "AuditorAgent: Concluido. Status: %s",
                "APROVADA" if report.approved else "REPROVADA",
            )
            return report
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error(
                "AuditorAgent: Falha técnica na validação do relatório (%s). Bloqueando por segurança (Fail-Closed).",
                type(exc).__name__,
            )
            return AuditReport(
                approved=False,
                critique=(
                    f"Falha de sistema: O Auditor não conseguiu processar os dados ({type(exc).__name__}). "
                    "Acesso negado por precaução de segurança (Fail-Closed)."
                ),
            )
