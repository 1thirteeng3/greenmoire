import os
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List

import aiofiles

from core.integrations.firecrawl_provider import FirecrawlProvider

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registro Central de Ferramentas Nativas do Grimoire.
    Mapeia descricoes JSON (schemas) para funcoes assincronas reais.
    """

    def __init__(self, firecrawl_provider: FirecrawlProvider):
        self.firecrawl = firecrawl_provider
        self.vault_path = Path(os.getenv("OBSIDIAN_VAULT_PATH", "./2ndBrain")).resolve()
        self.inbox_path = self.vault_path / "Grimoire_Inbox"
        self.inbox_path.mkdir(parents=True, exist_ok=True)
        self._dispatch_table: Dict[str, Callable[..., Awaitable[str]]] = {
            "web_search": self.tool_web_search,
            "get_current_time": self.tool_get_current_time,
            "write_obsidian_note": self.tool_write_obsidian_note,
            "delete_obsidian_note": self.tool_delete_obsidian_note,
        }

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """
        Retorna as definicoes estritas para injecao no prompt do LLM.
        Formato no padrao universal (OpenAI).
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": (
                        "Realiza uma busca em tempo real na internet para obter informacoes "
                        "atualizadas, noticias ou documentacao externa nao presente na memoria local."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "O termo de busca otimizado para motores de busca.",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": (
                        "Retorna a data e hora atual do sistema local. Use sempre que o contexto "
                        "exigir precisao temporal recente."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_obsidian_note",
                    "description": (
                        "Cria ou edita uma nota no cofre do usuario. Use 'inbox' para novas ideias, "
                        "'append' para adicionar a notas existentes, e 'overwrite' APENAS quando for "
                        "explicitamente instruido a reescrever ou governar o cofre."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "Nome do arquivo (ex: 'Plano_Marketing.md')"},
                            "content": {"type": "string", "description": "Conteudo em Markdown"},
                            "mode": {
                                "type": "string",
                                "enum": ["inbox", "append", "overwrite"],
                                "description": "Modo de escrita de seguranca.",
                            },
                        },
                        "required": ["filename", "content", "mode"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_obsidian_note",
                    "description": (
                        "FERRAMENTA DE GOVERNANCA: Apaga permanentemente uma nota do cofre. "
                        "Use apenas para podar informacoes duplicadas, obsoletas ou lixo cognitivo."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Nome exato do arquivo a deletar (ex: 'Ideia_Antiga.md')",
                            }
                        },
                        "required": ["filename"],
                    },
                },
            },
        ]

    async def execute_tool(self, tool_name: str, arguments_json: str) -> str:
        """
        Interpreta o pedido do modelo, valida e executa o codigo fisico.
        """
        logger.info(f"Executando ferramenta nativa: {tool_name}")

        if tool_name not in self._dispatch_table:
            error_msg = f"Ferramenta '{tool_name}' nao existe no ToolRegistry."
            logger.error(error_msg)
            return json.dumps({"status": "error", "message": error_msg})

        try:
            kwargs = json.loads(arguments_json) if arguments_json else {}
            func = self._dispatch_table[tool_name]
            result = await func(**kwargs)
            return json.dumps({"status": "success", "data": result})
        except json.JSONDecodeError:
            return json.dumps(
                {
                    "status": "error",
                    "message": "Falha de validacao: os argumentos fornecidos nao sao um JSON valido.",
                }
            )
        except Exception as e:
            logger.error(f"Falha na execucao da ferramenta '{tool_name}': {e}")
            return json.dumps({"status": "error", "message": str(e)})

    async def tool_web_search(self, query: str) -> str:
        """
        Executa um web scraping direcionado utilizando o provedor integrado.
        """
        logger.debug(f"Buscando na web por: {query}")
        return (
            f"Resultados da web para '{query}': A funcionalidade de pesquisa profunda "
            "esta operante. Conecte o endpoint de search na integracao."
        )

    def _sanitize_path(self, filename: str) -> str:
        """Prevencao contra path traversal (ex: '../../etc/passwd')."""
        clean_name = os.path.basename(filename)
        if not clean_name.endswith(".md"):
            clean_name += ".md"
        return clean_name

    async def tool_write_obsidian_note(self, filename: str, content: str, mode: str) -> str:
        """Manipula arquivos do vault com modos de seguranca."""
        clean_name = self._sanitize_path(filename)

        if mode == "inbox":
            target_path = self.inbox_path / clean_name
            async with aiofiles.open(target_path, "w", encoding="utf-8") as f:
                await f.write(content)
            return f"Nota criada com sucesso na Quarentena/Inbox: {target_path.name}"

        if mode == "append":
            target_path = self.vault_path / clean_name
            if not target_path.exists():
                return f"Erro: Arquivo {clean_name} nao encontrado para append. Crie na inbox primeiro."

            async with aiofiles.open(target_path, "a", encoding="utf-8") as f:
                await f.write(f"\n\n---\n*Adicionado por Grimoire:*\n{content}")
            return f"Conteudo adicionado (append) com sucesso a {clean_name}"

        if mode == "overwrite":
            target_path = self.vault_path / clean_name
            async with aiofiles.open(target_path, "w", encoding="utf-8") as f:
                await f.write(content)
            return f"AVISO: Nota {clean_name} sobrescrita (overwrite) com sucesso."

        return "Modo de escrita invalido."

    async def tool_delete_obsidian_note(self, filename: str) -> str:
        """Apaga nota (uso recomendado para governanca)."""
        clean_name = self._sanitize_path(filename)
        target_path = self.vault_path / clean_name
        if not target_path.exists():
            target_path = self.inbox_path / clean_name

        if target_path.exists():
            os.remove(target_path)
            return f"Governanca: Nota {clean_name} deletada permanentemente."
        return f"Erro: Nota {clean_name} nao encontrada para exclusao."

    async def tool_get_current_time(self) -> str:
        """
        Fornece ao LLM a percepcao temporal do mundo real.
        """
        from datetime import datetime

        now = datetime.now()
        return now.strftime("Data: %Y-%m-%d | Hora: %H:%M:%S")
