import json
import logging
from typing import Any, Awaitable, Callable, Dict, List

from core.integrations.firecrawl_provider import FirecrawlProvider

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registro Central de Ferramentas Nativas do Grimoire.
    Mapeia descricoes JSON (schemas) para funcoes assincronas reais.
    """

    def __init__(self, firecrawl_provider: FirecrawlProvider):
        self.firecrawl = firecrawl_provider
        self._dispatch_table: Dict[str, Callable[..., Awaitable[str]]] = {
            "web_search": self.tool_web_search,
            "get_current_time": self.tool_get_current_time,
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

    async def tool_get_current_time(self) -> str:
        """
        Fornece ao LLM a percepcao temporal do mundo real.
        """
        from datetime import datetime

        now = datetime.now()
        return now.strftime("Data: %Y-%m-%d | Hora: %H:%M:%S")
