import logging
from pathlib import Path

from core.brain.model_router import ModelRouter
from core.infrastructure.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)


class MetaAgent:
    """
    O Agente capaz de refletir e reescrever a própria arquitetura do Grimoire.

    Pipeline de segurança:
      1. Lê o código-fonte do ficheiro alvo (read-only)
      2. Submete ao LLM T3 com prompt estrito (retornar APENAS Python puro)
      3. Limpa a resposta de wrappers markdown
      4. Envia para quarentena via SandboxManager.stage_proposal()
      5. Executa pytest automaticamente
      6. Retorna status legível pelo humano (aprovação ainda é manual)
    """

    # Instrução de segurança injetada em TODOS os prompts do MetaAgent
    _SAFETY_SYSTEM_PROMPT = """
Você é o Meta-Agente do Grimoire OS. Sua missão é evoluir o sistema modificando o código-fonte.

REGRAS ABSOLUTAS – VIOLÁ-LAS CAUSA REJEIÇÃO IMEDIATA:
1. Devolva APENAS O CÓDIGO FONTE PYTHON MODIFICADO, COMPLETO E FUNCIONAL.
2. Absolutamente NENHUM texto fora do código. Sem explicações, sem blocos markdown (```python).
3. Mantenha todas as importações necessárias e a tipagem estrita (type hints).
4. Não remova funcionalidade existente sem instrução explícita.
5. Não adicione dependências externas não listadas nos imports originais.

ARQUIVO ALVO: {target_file}
OBJETIVO DA MELHORIA: {objective}

CÓDIGO ATUAL:
{current_code}
""".strip()

    def __init__(self, model_router: ModelRouter, sandbox_manager: SandboxManager):
        self.router = model_router
        self.sandbox = sandbox_manager

    async def self_improve(self, target_file: str, objective: str) -> str:
        """
        Orquestra o ciclo completo de auto-melhoria para um único ficheiro.
        Retorna uma string de status legível destinada à interface do utilizador.
        """
        logger.warning(
            "⚡ Meta-Cognição Ativada: tentativa de modificação em '%s' | objetivo: %s",
            target_file,
            objective[:120],
        )

        # ── 1. Ler o código atual ─────────────────────────────────────────
        try:
            current_code = Path(target_file).read_text(encoding="utf-8")
        except OSError as e:
            return f"❌ Falha ao ler o ficheiro alvo: {e}"

        # ── 2. Construir prompt & chamar LLM T3 ───────────────────────────
        system_content = self._SAFETY_SYSTEM_PROMPT.format(
            target_file=target_file,
            objective=objective,
            current_code=current_code,
        )

        try:
            response = await self.router.execute_tier(
                tier="T3",
                messages=[{"role": "system", "content": system_content}],
            )
        except Exception as e:
            logger.error("MetaAgent: falha na chamada ao LLM T3: %s", e)
            return f"❌ Falha na chamada ao LLM T3: {e}"

        # ── 3. Limpar wrappers markdown ───────────────────────────────────
        clean_code = response.replace("```python", "").replace("```", "").strip()

        if not clean_code:
            return "❌ O LLM devolveu uma resposta vazia. Proposta abortada."

        # ── 4. Quarentena ─────────────────────────────────────────────────
        try:
            proposal = self.sandbox.stage_proposal(target_file, clean_code, objective)
        except PermissionError as e:
            logger.critical("MetaAgent: violação de segurança bloqueada: %s", e)
            return f"🚫 ACESSO NEGADO: {e}"
        except Exception as e:
            return f"❌ Falha ao criar a proposta na sandbox: {e}"

        # ── 5. Pipeline de testes automáticos ────────────────────────────
        success, logs = self.sandbox.run_security_tests(proposal.id)

        if success:
            return (
                f"✅ PROPOSTA {proposal.id} CRIADA COM SUCESSO.\n"
                f"O código passou na bateria de testes locais (pytest).\n"
                f"Aguarda Veto Humano via endpoint: "
                f"POST /api/v1/governance/proposals/{proposal.id}/merge\n\n"
                f"Para inspecionar o diff:\n"
                f"GET /api/v1/governance/proposals/{proposal.id}/diff"
            )
        else:
            return (
                f"💥 FALHA CRÍTICA – Proposta {proposal.id} CHUMBADA.\n"
                f"O código gerado quebrou a suíte de testes. Nenhuma alteração foi feita ao sistema.\n\n"
                f"--- LOGS DE FALHA (últimos 300 chars) ---\n"
                f"{logs[-300:]}"
            )
