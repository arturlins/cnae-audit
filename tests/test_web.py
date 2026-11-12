import json

import httpx
import pytest
from fastapi.testclient import TestClient

from agente.instrucoes import AVISO
from web import agentos_client, main

CONTEUDO = f"""{AVISO}

## Resultado
Compatibilidade: incompativel. Status da afirmação: contradita.

## Em linguagem simples
O 6201-5/01 não serve para SaaS.

## Por que chegamos nisso
Regra R-6201-SAAS.

## Onde conferir
- base
"""

RUN = {
    "run_id": "run-1",
    "status": "COMPLETED",
    "content": CONTEUDO,
    "tools": [
        {
            "tool_name": "validar_enquadramento",
            "tool_args": {"codigo_cnae": "6201-5/01", "modelo_negocio": "saas_padronizado"},
            "result": json.dumps({"status": "ok", "status_afirmacao": "contradita"}),
        }
    ],
}

FORM = {"cnae": "6201-5/01", "modelo_negocio": "saas_padronizado", "afirmacao_compativel": "sim"}


@pytest.fixture
def client():
    return TestClient(main.app)


def test_index_lista_modelos_da_base(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'value="saas_padronizado"' in r.text
    assert "Material de referência" in r.text


def test_verificar_mostra_selo_e_ferramentas(client, monkeypatch):
    enviado = {}

    def falso(mensagem, session_id=None):
        enviado["mensagem"] = mensagem
        return RUN

    monkeypatch.setattr(main, "run_agent", falso)
    r = client.post("/verificar", data=FORM)
    assert r.status_code == 200
    assert "não confere com a base" in r.text
    assert "validar_enquadramento" in r.text
    assert "R-6201-SAAS" in r.text
    assert "CNAE: 6201-5/01" in enviado["mensagem"]


def test_verificar_resposta_nao_verificada(client, monkeypatch):
    run = {**RUN, "content": CONTEUDO + "\nUse o 7490-1/04."}
    monkeypatch.setattr(main, "run_agent", lambda m, session_id=None: run)
    r = client.post("/verificar", data=FORM)
    assert "Resposta não verificada" in r.text
    assert "7490-1/04" in r.text  # aparece na lista de falhas, não como resposta


def test_verificar_valor_invalido(client):
    r = client.post("/verificar", data={**FORM, "folha_12m": "abc"})
    assert "Confira os valores" in r.text


def test_agentos_fora_do_ar_mostra_erro_amigavel(client, monkeypatch):
    def recusa(*args, **kwargs):
        raise httpx.ConnectError("recusado")

    monkeypatch.setattr(agentos_client.httpx, "post", recusa)
    r = client.post("/verificar", data=FORM)
    assert r.status_code == 200
    assert "Não foi possível verificar agora" in r.text
    assert "Tentar novamente" in r.text


def test_agentos_tempo_esgotado(monkeypatch):
    def lento(*args, **kwargs):
        raise httpx.ReadTimeout("lento")

    monkeypatch.setattr(agentos_client.httpx, "post", lento)
    with pytest.raises(agentos_client.AgentOSError) as exc:
        agentos_client.run_agent("oi")
    assert exc.value.kind == "tempo_esgotado"


def test_cliente_envia_form_e_chave(monkeypatch):
    capturado = {}

    def post(url, data, headers, timeout):
        capturado.update(url=url, data=data, headers=headers, timeout=timeout)
        return httpx.Response(200, json=RUN)

    monkeypatch.setenv("OS_SECURITY_KEY", "segredo")
    monkeypatch.setenv("AGENTOS_TIMEOUT_S", "12")
    monkeypatch.setattr(agentos_client.httpx, "post", post)
    run = agentos_client.run_agent("oi", session_id="s1")
    assert run["run_id"] == "run-1"
    assert capturado["url"].endswith("/agents/verificador-cnae/runs")
    assert capturado["data"] == {"message": "oi", "stream": "false", "session_id": "s1"}
    assert capturado["headers"]["Authorization"] == "Bearer segredo"
    assert capturado["timeout"] == 12.0


def test_cliente_http_500_vira_erro(monkeypatch):
    monkeypatch.setattr(
        agentos_client.httpx, "post", lambda *a, **k: httpx.Response(500, text="boom")
    )
    with pytest.raises(agentos_client.AgentOSError) as exc:
        agentos_client.run_agent("oi")
    assert exc.value.kind == "erro_api"
