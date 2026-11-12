import httpx
import pytest

from agente.ferramentas import ibge
from agente.ferramentas.ibge import consultar_cnae_ibge

RESPOSTA_6201501 = {
    "id": "6201501",
    "descricao": "DESENVOLVIMENTO DE PROGRAMAS DE COMPUTADOR SOB ENCOMENDA",
    "classe": {
        "id": "62015",
        "descricao": "DESENVOLVIMENTO DE PROGRAMAS DE COMPUTADOR SOB ENCOMENDA",
        "grupo": {
            "id": "620",
            "descricao": "ATIVIDADES DOS SERVIÇOS DE TECNOLOGIA DA INFORMAÇÃO",
            "divisao": {
                "id": "62",
                "descricao": "ATIVIDADES DOS SERVIÇOS DE TECNOLOGIA DA INFORMAÇÃO",
                "secao": {"id": "J", "descricao": "INFORMAÇÃO E COMUNICAÇÃO"},
            },
        },
    },
    "observacoes": ["Esta subclasse compreende\r\n- o desenvolvimento " + "x" * 2000],
}


def _mock_get(monkeypatch, *, json_data=None, status=200, exc=None, text=None):
    chamadas = []

    def fake_get(url, timeout):
        chamadas.append({"url": url, "timeout": timeout})
        if exc is not None:
            raise exc
        request = httpx.Request("GET", url)
        if text is not None:
            return httpx.Response(status, text=text, request=request)
        return httpx.Response(status, json=json_data, request=request)

    monkeypatch.setattr(ibge.httpx, "get", fake_get)
    return chamadas


def test_ok_retorna_descricao_hierarquia_e_evidencia(monkeypatch):
    chamadas = _mock_get(monkeypatch, json_data=RESPOSTA_6201501)
    r = consultar_cnae_ibge("6201-5/01")
    assert r["status"] == "ok"
    assert r["codigo"] == "6201-5/01"
    assert r["descricao"] == RESPOSTA_6201501["descricao"]
    assert r["hierarquia"]["secao"] == "J - INFORMAÇÃO E COMUNICAÇÃO"
    assert r["evidencia"]["url"].endswith("/subclasses/6201501")
    assert r["evidencia"]["consultado_em"].endswith("+00:00")
    assert len(r["observacoes"][0]) < 800  # observações longas são resumidas
    assert chamadas[0]["timeout"] == 5.0


def test_lista_vazia_e_nao_encontrado(monkeypatch):
    _mock_get(monkeypatch, json_data=[])
    r = consultar_cnae_ibge("9999999")
    assert r["status"] == "nao_encontrado"
    assert "descricao" not in r


def test_entrada_invalida_nao_chama_api(monkeypatch):
    chamadas = _mock_get(monkeypatch, json_data=RESPOSTA_6201501)
    r = consultar_cnae_ibge("62015")
    assert r["status"] == "entrada_invalida"
    assert chamadas == []


@pytest.mark.parametrize(
    "exc",
    [httpx.ConnectTimeout("timeout"), httpx.ConnectError("dns"), httpx.ReadTimeout("lento")],
)
def test_falha_de_rede_e_indisponivel_sem_dados(monkeypatch, exc):
    _mock_get(monkeypatch, exc=exc)
    r = consultar_cnae_ibge("6201501")
    assert r["status"] == "indisponivel"
    assert "descricao" not in r


@pytest.mark.parametrize("status", [404, 500, 503])
def test_http_diferente_de_200_e_indisponivel(monkeypatch, status):
    _mock_get(monkeypatch, json_data={"erro": "x"}, status=status)
    assert consultar_cnae_ibge("6201501")["status"] == "indisponivel"


def test_resposta_nao_json_e_indisponivel(monkeypatch):
    _mock_get(monkeypatch, text="<html>manutenção</html>")
    assert consultar_cnae_ibge("6201501")["status"] == "indisponivel"


def test_resposta_com_id_divergente_e_indisponivel(monkeypatch):
    _mock_get(monkeypatch, json_data={**RESPOSTA_6201501, "id": "6202300"})
    assert consultar_cnae_ibge("6201501")["status"] == "indisponivel"


def test_base_url_e_timeout_configuraveis(monkeypatch):
    monkeypatch.setenv("IBGE_BASE_URL", "http://ibge-fora-do-ar.invalid/api/")
    monkeypatch.setenv("IBGE_TIMEOUT_S", "1.5")
    chamadas = _mock_get(monkeypatch, exc=httpx.ConnectError("dns"))
    r = consultar_cnae_ibge("6201501")
    assert r["status"] == "indisponivel"
    assert chamadas[0]["url"] == "http://ibge-fora-do-ar.invalid/api/subclasses/6201501"
    assert chamadas[0]["timeout"] == 1.5
