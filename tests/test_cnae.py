import pytest

from agente.ferramentas.cnae import CnaeInvalido, formatar_cnae, normalizar_cnae


@pytest.mark.parametrize(
    "entrada", ["6201-5/01", "6201501", "62.01-5-01", " 6201 5 01 ", "6201-5-01"]
)
def test_normaliza_formatos_usuais(entrada):
    assert normalizar_cnae(entrada) == "6201501"


@pytest.mark.parametrize("entrada", ["62015", "620150100", "", "   ", "6201-5/0A", "CNAE 6201501"])
def test_rejeita_formato_invalido(entrada):
    with pytest.raises(CnaeInvalido):
        normalizar_cnae(entrada)


def test_rejeita_nao_string():
    with pytest.raises(CnaeInvalido):
        normalizar_cnae(6201501)  # type: ignore[arg-type]


def test_formata_padrao_oficial():
    assert formatar_cnae("6201501") == "6201-5/01"
