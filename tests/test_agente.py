import json

from agno.tools.function import Function

from agente import config
from agente.agente import como_json, criar_agente
from agente.ferramentas import validar_enquadramento


def test_como_json_preserva_contrato_e_devolve_json():
    envolvida = como_json(validar_enquadramento)
    fn = Function.from_callable(envolvida)
    assert fn.name == "validar_enquadramento"
    assert fn.parameters["required"] == ["codigo_cnae", "modelo_negocio"]
    assert "folha_12m" in fn.parameters["properties"]
    assert "base de regras" in fn.description
    # A anotação original não é alterada.
    assert validar_enquadramento.__annotations__["return"] is dict

    retorno = envolvida("6201-5/01", "saas_padronizado")
    assert isinstance(retorno, str)
    assert json.loads(retorno)["regra_aplicada"] == "R-6201-SAAS"


def test_agente_configurado(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_API_KEY", "teste")
    monkeypatch.setenv("AGENTOS_DB", str(tmp_path / "agentos.db"))
    agente = criar_agente()
    assert agente.id == config.AGENT_ID == "verificador-cnae"
    assert agente.tool_call_limit == 6
    assert agente.model.temperature == 0
    nomes = {getattr(t, "__name__", None) for t in agente.tools}
    assert nomes == {"consultar_cnae_ibge", "validar_enquadramento"}
