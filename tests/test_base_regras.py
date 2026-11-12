"""Integridade da base de regras: protege contra edições manuais inconsistentes."""

import json
import re

import pytest

from agente.config import DEFAULT_REGRAS_PATH

BASE = json.loads(DEFAULT_REGRAS_PATH.read_text(encoding="utf-8"))
CNAES = BASE["cnaes"]
REGRAS = [(codigo, regra) for codigo, cnae in CNAES.items() for regra in cnae["regras"]]


def test_metadados_obrigatorios():
    for chave in ("versao", "data_referencia", "aviso", "fontes_legais", "modelos_negocio"):
        assert BASE[chave]
    assert "não substitui" in BASE["aviso"]


@pytest.mark.parametrize("codigo", list(CNAES))
def test_codigo_no_formato_oficial(codigo):
    assert re.fullmatch(r"\d{4}-\d/\d{2}", codigo)


def test_ids_de_regra_unicos():
    ids = [regra["id"] for _, regra in REGRAS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(("codigo", "regra"), REGRAS, ids=[r["id"] for _, r in REGRAS])
def test_regra_valida(codigo, regra):
    assert regra["modelo_negocio"] in BASE["modelos_negocio"]
    assert regra["resultado"] in {"compativel", "incompativel", "indeterminado"}
    assert regra["motivo"].strip()


def test_no_maximo_uma_regra_por_cnae_e_modelo():
    pares = [(codigo, regra["modelo_negocio"]) for codigo, regra in REGRAS]
    assert len(pares) == len(set(pares))


@pytest.mark.parametrize("codigo", list(CNAES))
def test_tributacao_coerente(codigo):
    trib = CNAES[codigo]["tributacao"]
    assert trib["fundamentos"]
    assert all(f in BASE["fontes_legais"] for f in trib["fundamentos"])
    if trib["sujeito_fator_r"] is True:
        assert trib["anexo_fator_r_alto"] == "III"
        assert trib["anexo_fator_r_baixo"] == "V"
        assert trib["confianca"] == "alta"
    elif trib["sujeito_fator_r"] is False:
        assert trib["anexo"] in {"I", "II", "III", "IV", "V"}
    else:
        assert trib["confianca"] == "indeterminada"
        assert "anexo" not in trib


def test_fontes_legais_tem_url_oficial():
    for fonte in BASE["fontes_legais"].values():
        assert fonte["url"].startswith("https://www.planalto.gov.br/")
        assert fonte["dispositivo"] and fonte["trecho"]


def test_todo_modelo_tem_ao_menos_um_cnae_compativel_ou_zona_cinzenta():
    cobertos = {regra["modelo_negocio"] for _, regra in REGRAS}
    assert cobertos == set(BASE["modelos_negocio"])
