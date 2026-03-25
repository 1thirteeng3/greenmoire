import logging
from typing import Dict, List, Optional

from core.brain.conflict_resolver import ConflictReport

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Fábrica de prompts do Grimoire.
    Garante a injeção robusta de regras, contexto RAG e diretivas de calibração.
    """

    def __init__(self):
        self.base_system_prompt = (
            "Você é o Grimoire, um Sistema Operacional Cognitivo e assistente pessoal de elite. "
            "Suas respostas devem ser imparciais, diretas, lógicas e baseadas ESTRITAMENTE em fatos. "
            "Siga estas restrições rigorosamente:\n"
            "1. Não utilize linguagem subserviente, excessivamente cordial ou eufemismos (evite 'sugarcoating').\n"
            "2. Não invente informações. Se o contexto fornecido for insuficiente, declare a limitação imediatamente.\n"
            "3. Estruture suas respostas logicamente, utilizando Markdown limpo."
        )

    def build_messages(
        self,
        user_prompt: str,
        rag_context: Optional[str] = None,
        conflict_report: Optional[ConflictReport] = None,
        agent_role: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Constrói mensagens [system, user] prontas para inferência.
        """
        system_content = [self.base_system_prompt]

        if conflict_report and conflict_report.has_conflict:
            logger.debug("Injetando diretivas de calibração no system prompt.")
            system_content.append(
                "\n<DIRETIVAS_DE_CALIBRACAO>\n"
                "ATENÇÃO MÁXIMA: O usuário já corrigiu seu comportamento no passado referente a este tema. "
                "Você DEVE obedecer à seguinte restrição para não repetir o erro:\n"
                f"{conflict_report.reason}\n"
                "</DIRETIVAS_DE_CALIBRACAO>"
            )

        if rag_context:
            logger.debug("Injetando conhecimento recuperado no system prompt.")
            system_content.append(
                "\n<CONHECIMENTO_RECUPERADO>\n"
                "Utilize EXCLUSIVAMENTE os fatos abaixo para responder à solicitação do usuário. "
                "Não misture com conhecimento prévio de treinamento se houver contradição.\n"
                f"{rag_context}\n"
                "</CONHECIMENTO_RECUPERADO>"
            )

        if agent_role:
            logger.debug("Injetando persona do agente especializado no system prompt.")
            system_content.append(
                "\n<PERFIL_DE_EXECUCAO>\n"
                f"{agent_role}\n"
                "</PERFIL_DE_EXECUCAO>"
            )

        final_system_message = "\n".join(system_content)
        return [
            {"role": "system", "content": final_system_message},
            {"role": "user", "content": user_prompt},
        ]
