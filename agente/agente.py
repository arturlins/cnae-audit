"""Definição do agente Agno "verificador-cnae" (modelo, instruções, limites e ferramentas)."""

import functools
import json
from collections.abc import Callable

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.google import Gemini

from agente import config
from agente.ferramentas import consultar_cnae_ibge, validar_enquadramento
from agente.instrucoes import DESCRICAO, INSTRUCOES


def como_json(ferramenta: Callable[..., dict]) -> Callable[..., str]:
    """Expõe uma ferramenta que devolve dict como texto JSON.

    O Agno converte retornos que não são str com `str()`, o que gera repr de Python
    (aspas simples, None, True). Em JSON, o modelo e o pós-validador do app web leem o
    retorno sem ambiguidade. Nome, docstring e parâmetros da ferramenta são preservados.
    """

    @functools.wraps(ferramenta)
    def envolvida(*args, **kwargs) -> str:
        return json.dumps(ferramenta(*args, **kwargs), ensure_ascii=False)

    envolvida.__annotations__ = {**ferramenta.__annotations__, "return": str}
    return envolvida


def criar_agente() -> Agent:
    config.agentos_db_path().parent.mkdir(parents=True, exist_ok=True)
    return Agent(
        id=config.AGENT_ID,
        name="Verificador de CNAE",
        description=DESCRICAO,
        model=Gemini(id=config.gemini_model_id(), temperature=0),
        instructions=INSTRUCOES,
        tools=[como_json(consultar_cnae_ibge), como_json(validar_enquadramento)],
        tool_call_limit=config.TOOL_CALL_LIMIT,
        # Só sessões do AgentOS; não é fonte de dados do domínio.
        db=SqliteDb(db_file=str(config.agentos_db_path())),
        add_history_to_context=True,
        num_history_runs=3,
        markdown=True,
        telemetry=False,
    )
