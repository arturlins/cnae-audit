"""Normalização e validação de códigos CNAE (subclasse, 7 dígitos)."""

import re

_SEPARADORES_PERMITIDOS = re.compile(r"^[\d\s./-]+$")


class CnaeInvalido(ValueError):
    """Código CNAE com formato inválido."""


def normalizar_cnae(codigo: str) -> str:
    """Converte um código CNAE em qualquer formato usual para 7 dígitos.

    Aceita `6201-5/01`, `6201501`, `62.01-5-01`, `6201 5 01`. Rejeita letras,
    outros símbolos e qualquer quantidade de dígitos diferente de 7.
    """
    if not isinstance(codigo, str) or not codigo.strip():
        raise CnaeInvalido("Informe o código CNAE (7 dígitos, ex.: 6201-5/01).")
    bruto = codigo.strip()
    if not _SEPARADORES_PERMITIDOS.match(bruto):
        raise CnaeInvalido(
            f"'{codigo}' contém caracteres inválidos. Use apenas dígitos e os separadores . - /"
        )
    digitos = re.sub(r"\D", "", bruto)
    if len(digitos) != 7:
        raise CnaeInvalido(
            f"'{codigo}' tem {len(digitos)} dígitos; um CNAE de subclasse tem 7 (ex.: 6201-5/01)."
        )
    return digitos


def formatar_cnae(digitos: str) -> str:
    """Formata 7 dígitos no padrão oficial `NNNN-N/NN`."""
    return f"{digitos[:4]}-{digitos[4]}/{digitos[5:]}"
