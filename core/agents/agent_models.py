from typing import List

from pydantic import BaseModel, Field


class AgentProfile(BaseModel):
    name: str
    role_description: str = Field(
        description="O prompt de sistema especifico que define a especialidade deste agente."
    )
    allowed_tools: List[str] = Field(
        description="Lista restrita dos nomes das ferramentas que este agente tem permissao para usar."
    )
    max_loops: int = Field(
        default=5,
        description="Numero maximo de iteracoes ReAct que este agente pode executar antes de abortar.",
    )
