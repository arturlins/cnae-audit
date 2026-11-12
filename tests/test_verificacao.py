import json

from agente.instrucoes import AVISO, SECAO_ESCLARECIMENTO
from web.verificacao import cnaes_no_texto, extrair_ferramentas, verificar_resposta

TEXTO_OK = f"""{AVISO}

## Resultado
Compatibilidade: incompativel. Status da afirmação: contradita.

## Em linguagem simples
O CNAE 6201-5/01 é para software sob encomenda. Veja o 6319-4/00.

## Por que chegamos nisso
Regra R-6201-SAAS.

## Onde conferir
- https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/6201501
"""


def _tool(nome, args, resultado):
    return {"tool_name": nome, "tool_args": args, "result": json.dumps(resultado)}


def _run(content, tools):
    return {"run_id": "r1", "content": content, "tools": tools, "status": "COMPLETED"}


IBGE_OK = _tool(
    "consultar_cnae_ibge",
    {"codigo_cnae": "6201-5/01"},
    {"status": "ok", "codigo": "6201-5/01", "descricao": "..."},
)
VALIDAR_CONTRADITA = _tool(
    "validar_enquadramento",
    {"codigo_cnae": "6201-5/01", "modelo_negocio": "saas_padronizado"},
    {
        "status": "ok",
        "status_afirmacao": "contradita",
        "cnaes_sugeridos": [{"codigo": "6319-4/00"}],
    },
)


def test_cnaes_no_texto_formatos():
    texto = "6201-5/01, 6202300 e 62.03-1-00; data 2026-11-11 e 30000 não contam"
    assert cnaes_no_texto(texto) == {"6201501", "6202300", "6203100"}


def test_extrair_ferramentas_le_json_e_repr_invalido():
    run = _run("", [IBGE_OK, {"tool_name": "x", "tool_args": {}, "result": "{'a': None}"}])
    chamadas = extrair_ferramentas(run)
    assert chamadas[0].status == "ok"
    assert chamadas[1].resultado is None and chamadas[1].resultado_bruto == "{'a': None}"


def test_resposta_valida_usa_selo_da_ferramenta():
    v = verificar_resposta(_run(TEXTO_OK, [IBGE_OK, VALIDAR_CONTRADITA]))
    assert v.verificada, v.falhas
    assert v.status_afirmacao == "contradita"
    assert "não confere" in v.selo


def test_selo_ignora_o_texto_do_modelo():
    texto = TEXTO_OK.replace("contradita", "confirmada")
    v = verificar_resposta(_run(texto, [IBGE_OK, VALIDAR_CONTRADITA]))
    assert v.status_afirmacao == "contradita"


def test_cnae_inventado_reprova():
    texto = TEXTO_OK + "\nTalvez o 7490-1/04 também sirva."
    v = verificar_resposta(_run(texto, [IBGE_OK, VALIDAR_CONTRADITA]))
    assert not v.verificada
    assert any("7490-1/04" in f for f in v.falhas)


def test_secao_ausente_reprova():
    texto = TEXTO_OK.replace("## Onde conferir", "## Fontes")
    v = verificar_resposta(_run(texto, [IBGE_OK, VALIDAR_CONTRADITA]))
    assert not v.verificada
    assert any("Onde conferir" in f for f in v.falhas)


def test_sem_ferramenta_bem_sucedida_reprova():
    falha = _tool("consultar_cnae_ibge", {"codigo_cnae": "6201501"}, {"status": "indisponivel"})
    v = verificar_resposta(_run(TEXTO_OK.replace("6319-4/00", ""), [falha]))
    assert not v.verificada
    assert any("Nenhuma ferramenta" in f for f in v.falhas)


def test_esclarecimento_dispensa_ferramenta_e_secoes():
    texto = f"{AVISO}\n\n{SECAO_ESCLARECIMENTO}\nQual é o código CNAE?"
    v = verificar_resposta(_run(texto, []))
    assert v.verificada and v.tipo == "esclarecimento"
    assert v.selo is None and v.sem_veredito is None


def test_base_indisponivel_sem_veredito():
    erro = _tool(
        "validar_enquadramento",
        {"codigo_cnae": "6201-5/01", "modelo_negocio": "saas_padronizado"},
        {"status": "erro_fonte", "mensagem": "Base de regras não encontrada"},
    )
    v = verificar_resposta(_run(TEXTO_OK.replace("6319-4/00", ""), [IBGE_OK, erro]))
    assert v.status_afirmacao is None and v.selo is None
    assert "indisponível" in v.sem_veredito


def test_cnae_fora_da_base_sem_evidencia():
    fora = _tool(
        "validar_enquadramento",
        {"codigo_cnae": "4711-3/02", "modelo_negocio": "revenda_hardware"},
        {"status": "nao_encontrado", "status_afirmacao": "sem_evidencia_suficiente"},
    )
    texto = (
        TEXTO_OK.replace("6201-5/01", "4711-3/02")
        .replace("6201501", "4711302")
        .replace("6319-4/00", "")
    )
    ibge = _tool("consultar_cnae_ibge", {"codigo_cnae": "4711302"}, {"status": "ok"})
    v = verificar_resposta(_run(texto, [ibge, fora]))
    assert v.verificada, v.falhas
    assert v.status_afirmacao == "sem_evidencia_suficiente"
