"""Checagens do scripts/run_casos.py que não dependem do modelo."""

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_casos.py"
_spec = importlib.util.spec_from_file_location("run_casos", _SCRIPT)
run_casos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_casos)

RESULTADO_T04 = (
    "## Resultado\n- Compatibilidade: indeterminado\n"
    "- Status da afirmação: sem_evidencia_suficiente\n\n## Em linguagem simples\n"
)


@pytest.mark.parametrize(
    "texto",
    [
        # Frase real do T04 (execução de 12/11/2026), que a checagem antiga reprovava.
        (
            "Como o CNAE 4711-3/02 não está cadastrado na base de regras, a ferramenta classifica "
            "a compatibilidade como indeterminada, pois a ausência na base não significa "
            "necessariamente que o CNAE seja incompatível perante a legislação."
        ),
        "Isso não significa que ele seja incompatível.",
        "O CNAE não está na base.",
    ],
)
def test_t04_aceita_explicacao_sem_afirmar_incompatibilidade(texto):
    assert not run_casos._afirma_incompatibilidade(RESULTADO_T04 + texto)


@pytest.mark.parametrize(
    "texto",
    [
        RESULTADO_T04 + "O CNAE 4711-3/02 é incompatível com revenda de computadores.",
        RESULTADO_T04 + "Não está na base. Mesmo assim, ele é incompatível com o seu negócio.",
        "## Resultado\nCompatibilidade: incompativel (não confirmado)\n\n## Em linguagem simples\n",
    ],
)
def test_t04_reprova_resposta_que_chama_o_cnae_de_incompativel(texto):
    assert run_casos._afirma_incompatibilidade(texto)
