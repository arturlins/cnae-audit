import json

import pytest

from agente.ferramentas.enquadramento import validar_enquadramento


def test_t02_licenciamento_6203_fator_r_alto_confirma_anexo_iii():
    r = validar_enquadramento(
        "6203-1/00",
        "licenciamento_nao_customizavel",
        folha_12m=30_000,
        receita_bruta_12m=100_000,
        anexo_afirmado="III",
    )
    assert r["status"] == "ok"
    assert r["compatibilidade"] == "compativel"
    assert r["regra_aplicada"] == "R-6203-LIC-NAO-CUSTOM"
    assert r["tributacao"]["anexo_resultante"] == "III"
    assert r["tributacao"]["calculo_fator_r"]["razao"] == 0.3
    assert r["status_afirmacao"] == "confirmada"
    assert r["evidencia"]["arquivo"] == "data/regras_cnae.json"
    assert r["evidencia"]["chave"] == "cnaes.6203-1/00.regras[id=R-6203-LIC-NAO-CUSTOM]"
    assert {f["id"] for f in r["fundamento_legal"]} >= {"LC123-18-5D-V", "LC123-18-5M"}


def test_t03_saas_no_6201_contradiz_afirmacao_e_sugere_alternativas():
    r = validar_enquadramento("6201501", "saas_padronizado", afirmacao_compativel=True)
    assert r["compatibilidade"] == "incompativel"
    assert r["regra_aplicada"] == "R-6201-SAAS"
    assert r["status_afirmacao"] == "contradita"
    assert r["comparacao"][0] == {
        "campo": "compatibilidade",
        "afirmado": "compativel",
        "apurado": "incompativel",
        "resultado": "diverge",
    }
    sugeridos = {s["codigo"] for s in r["cnaes_sugeridos"]}
    assert sugeridos == {"6311-9/00", "6319-4/00"}


def test_afirmacao_de_incompatibilidade_correta_e_confirmada():
    r = validar_enquadramento("6201-5/01", "saas_padronizado", afirmacao_compativel=False)
    assert r["status_afirmacao"] == "confirmada"


@pytest.mark.parametrize(
    ("folha", "receita", "anexo"),
    [(28_000, 100_000, "III"), (27_999.99, 100_000, "V"), (0, 100_000, "V")],
)
def test_limiar_do_fator_r_exatamente_28_porcento(folha, receita, anexo):
    r = validar_enquadramento("6201-5/01", "desenvolvimento_sob_encomenda", folha, receita)
    assert r["tributacao"]["anexo_resultante"] == anexo


def test_consultoria_segue_caminho_inverso_v_para_iii():
    baixo = validar_enquadramento("6204-0/00", "consultoria_ti", 10_000, 100_000)
    alto = validar_enquadramento("6204-0/00", "consultoria_ti", 40_000, 100_000)
    assert baixo["tributacao"]["anexo_resultante"] == "V"
    assert alto["tributacao"]["anexo_resultante"] == "III"


def test_fator_r_sem_folha_e_receita_fica_indeterminado():
    r = validar_enquadramento("6201-5/01", "desenvolvimento_sob_encomenda", anexo_afirmado="III")
    assert r["tributacao"]["anexo_resultante"] is None
    assert "Informe a folha" in r["tributacao"]["mensagem"]
    assert r["status_afirmacao"] == "sem_evidencia_suficiente"


def test_cnae_sem_fator_r_usa_anexo_fixo_e_contradiz_anexo_errado():
    r = validar_enquadramento("4751-2/01", "revenda_hardware", anexo_afirmado="Anexo III")
    assert r["tributacao"]["anexo_resultante"] == "I"
    assert r["tributacao"]["calculo_fator_r"] == {"aplicavel": False}
    assert r["status_afirmacao"] == "contradita"


def test_zona_cinzenta_de_tributacao_nao_define_anexo():
    r = validar_enquadramento("6319-4/00", "saas_padronizado", 30_000, 100_000, True, "III")
    assert r["compatibilidade"] == "compativel"
    assert r["tributacao"]["anexo_resultante"] is None
    assert r["tributacao"]["confianca"] == "indeterminada"
    # compatibilidade confere, anexo sem evidência -> conclusão conservadora
    assert r["status_afirmacao"] == "sem_evidencia_suficiente"


def test_regra_explicitamente_indeterminada_zona_cinzenta():
    r = validar_enquadramento("6203-1/00", "saas_padronizado", afirmacao_compativel=True)
    assert r["compatibilidade"] == "indeterminado"
    assert r["regra_aplicada"] == "R-6203-SAAS"
    assert r["status_afirmacao"] == "sem_evidencia_suficiente"


def test_ausencia_de_regra_nao_e_incompatibilidade():
    r = validar_enquadramento("6204-0/00", "ebook_publicacao_digital", afirmacao_compativel=True)
    assert r["compatibilidade"] == "indeterminado"
    assert r["regra_aplicada"] is None
    assert r["status_afirmacao"] == "sem_evidencia_suficiente"


def test_t04_cnae_fora_da_base_nao_e_falso():
    r = validar_enquadramento("4711-3/02", "saas_padronizado", afirmacao_compativel=True)
    assert r["status"] == "nao_encontrado"
    assert r["compatibilidade"] == "indeterminado"
    assert r["status_afirmacao"] == "sem_evidencia_suficiente"


def test_sem_afirmacao_status_sem_evidencia():
    r = validar_enquadramento("6201-5/01", "desenvolvimento_sob_encomenda")
    assert r["comparacao"] == []
    assert r["status_afirmacao"] == "sem_evidencia_suficiente"


@pytest.mark.parametrize(
    ("kwargs", "campo"),
    [
        ({"codigo_cnae": "62015", "modelo_negocio": "saas_padronizado"}, "codigo_cnae"),
        ({"codigo_cnae": "6201501", "modelo_negocio": "saas"}, "modelo_negocio"),
        (
            {"codigo_cnae": "6201501", "modelo_negocio": "consultoria_ti", "folha_12m": 1},
            "folha_12m",
        ),
        (
            {
                "codigo_cnae": "6201501",
                "modelo_negocio": "consultoria_ti",
                "folha_12m": -1,
                "receita_bruta_12m": 10,
            },
            "folha_12m",
        ),
        (
            {
                "codigo_cnae": "6201501",
                "modelo_negocio": "consultoria_ti",
                "folha_12m": 1,
                "receita_bruta_12m": 0,
            },
            "receita_bruta_12m",
        ),
        (
            {
                "codigo_cnae": "6201501",
                "modelo_negocio": "consultoria_ti",
                "folha_12m": "mil",
                "receita_bruta_12m": 10,
            },
            "folha_12m",
        ),
        (
            {"codigo_cnae": "6201501", "modelo_negocio": "consultoria_ti", "anexo_afirmado": "VI"},
            "anexo_afirmado",
        ),
        (
            {
                "codigo_cnae": "6201501",
                "modelo_negocio": "consultoria_ti",
                "afirmacao_compativel": "sim",
            },
            "afirmacao_compativel",
        ),
    ],
)
def test_t05_entradas_invalidas(kwargs, campo):
    r = validar_enquadramento(**kwargs)
    assert r["status"] == "entrada_invalida"
    assert r["campo"] == campo


def test_modelo_invalido_lista_valores_validos_com_rotulos():
    r = validar_enquadramento("6201501", "software")
    assert "saas_padronizado" in r["valores_validos"]
    assert r["valores_validos"]["saas_padronizado"].startswith("Vendo assinatura")


def test_t06b_base_ausente_e_erro_fonte_sem_veredito(monkeypatch, tmp_path):
    monkeypatch.setenv("REGRAS_PATH", str(tmp_path / "nao_existe.json"))
    r = validar_enquadramento("6201501", "saas_padronizado", afirmacao_compativel=True)
    assert r["status"] == "erro_fonte"
    assert "compatibilidade" not in r
    assert "status_afirmacao" not in r


def test_base_json_invalido_e_erro_fonte(monkeypatch, tmp_path):
    arquivo = tmp_path / "regras.json"
    arquivo.write_text("{ isto não é json", encoding="utf-8")
    monkeypatch.setenv("REGRAS_PATH", str(arquivo))
    assert validar_enquadramento("6201501", "saas_padronizado")["status"] == "erro_fonte"


def test_t07_base_relida_a_cada_chamada(monkeypatch, tmp_path):
    from agente.config import DEFAULT_REGRAS_PATH

    base = json.loads(DEFAULT_REGRAS_PATH.read_text(encoding="utf-8"))
    arquivo = tmp_path / "regras.json"
    arquivo.write_text(json.dumps(base), encoding="utf-8")
    monkeypatch.setenv("REGRAS_PATH", str(arquivo))

    antes = validar_enquadramento("6202-3/00", "saas_padronizado")
    assert antes["compatibilidade"] == "incompativel"

    regras = base["cnaes"]["6202-3/00"]["regras"]
    base["cnaes"]["6202-3/00"]["regras"] = [r for r in regras if r["id"] != "R-6202-SAAS"]
    arquivo.write_text(json.dumps(base), encoding="utf-8")

    depois = validar_enquadramento("6202-3/00", "saas_padronizado")
    assert depois["compatibilidade"] == "indeterminado"
