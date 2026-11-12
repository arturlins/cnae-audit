import pytest

from web.mensagem import Formulario, ValorInvalido, ler_reais, montar_mensagem

ROTULOS = {"saas_padronizado": "Vendo assinatura de um sistema na internet (SaaS)"}


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("", None),
        ("30000", 30000.0),
        ("30.000", 30000.0),
        ("30.000,50", 30000.5),
        ("R$ 1.000.000,00", 1000000.0),
        ("30000.5", 30000.5),
    ],
)
def test_ler_reais(texto, esperado):
    assert ler_reais(texto, "x") == esperado


@pytest.mark.parametrize("texto", ["abc", "-10"])
def test_ler_reais_invalido(texto):
    with pytest.raises(ValorInvalido):
        ler_reais(texto, "Folha")


def test_mensagem_com_enum_afirmacao_e_fator_r():
    form = Formulario(
        cnae="6201-5/01",
        modelo_negocio="saas_padronizado",
        afirmacao_compativel="sim",
        anexo_afirmado="III",
        folha_12m="30.000",
        receita_bruta_12m="100.000",
    )
    msg = montar_mensagem(form, ROTULOS)
    assert "CNAE: 6201-5/01" in msg
    assert "(modelo_negocio: saas_padronizado)" in msg
    assert "serve para o meu negócio" in msg and "NÃO" not in msg
    assert "Anexo III" in msg
    assert "R$ 30000.00" in msg and "R$ 100000.00" in msg


def test_mensagem_texto_livre_sem_afirmacao():
    form = Formulario(cnae="", modelo_negocio="outro", descricao_livre="vendo planilhas")
    msg = montar_mensagem(form, ROTULOS)
    assert "(não informado)" in msg
    assert '"vendo planilhas"' in msg
    assert "modelo_negocio:" not in msg
    assert "Me disseram" not in msg
