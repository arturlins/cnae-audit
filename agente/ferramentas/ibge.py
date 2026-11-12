"""Ferramenta `consultar_cnae_ibge`: descrição oficial de um CNAE na API pública do IBGE."""

from datetime import UTC, datetime

import httpx

from agente import config
from agente.ferramentas.cnae import CnaeInvalido, formatar_cnae, normalizar_cnae

FONTE = "API CNAE do IBGE (servicodados.ibge.gov.br)"
_MAX_OBSERVACOES = 3
_MAX_CHARS_OBSERVACAO = 700


def _agora_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _hierarquia(dados: dict) -> dict:
    classe = dados.get("classe") or {}
    grupo = classe.get("grupo") or {}
    divisao = grupo.get("divisao") or {}
    secao = divisao.get("secao") or {}
    return {
        "secao": f"{secao.get('id', '?')} - {secao.get('descricao', '?')}",
        "divisao": f"{divisao.get('id', '?')} - {divisao.get('descricao', '?')}",
        "grupo": f"{grupo.get('id', '?')} - {grupo.get('descricao', '?')}",
        "classe": f"{classe.get('id', '?')} - {classe.get('descricao', '?')}",
    }


def _resumir_observacoes(observacoes: list) -> list[str]:
    resumo = []
    for obs in observacoes[:_MAX_OBSERVACOES]:
        texto = " ".join(str(obs).split())
        if len(texto) > _MAX_CHARS_OBSERVACAO:
            texto = texto[:_MAX_CHARS_OBSERVACAO].rstrip() + " (...)"
        resumo.append(texto)
    return resumo


def consultar_cnae_ibge(codigo_cnae: str) -> dict:
    """Consulta a descrição OFICIAL de um código CNAE (subclasse) na API pública do IBGE.

    Use sempre que um CNAE for citado pelo usuário ou sugerido por outra ferramenta,
    para mostrar a descrição oficial e o que a subclasse compreende / não compreende.

    Args:
        codigo_cnae: Código CNAE de 7 dígitos, em qualquer formato usual
            (ex.: "6201-5/01", "6201501", "62.01-5-01").

    Returns:
        dict com `status`:
        - "ok": `codigo`, `descricao`, `hierarquia`, `observacoes` e `evidencia`
          (fonte, url consultada e data/hora UTC da consulta).
        - "entrada_invalida": código malformado; nada foi consultado.
        - "nao_encontrado": o IBGE não tem essa subclasse (não invente descrição).
        - "indisponivel": falha de rede, tempo esgotado ou resposta inesperada;
          NÃO há dados — declare a limitação ao usuário.
    """
    try:
        digitos = normalizar_cnae(codigo_cnae)
    except CnaeInvalido as exc:
        return {"status": "entrada_invalida", "codigo_informado": codigo_cnae, "mensagem": str(exc)}

    codigo = formatar_cnae(digitos)
    url = f"{config.ibge_base_url()}/subclasses/{digitos}"
    consultado_em = _agora_utc()
    evidencia = {"fonte": FONTE, "url": url, "consultado_em": consultado_em}

    try:
        resposta = httpx.get(url, timeout=config.ibge_timeout_s())
    except httpx.TimeoutException:
        return {
            "status": "indisponivel",
            "codigo": codigo,
            "mensagem": f"O IBGE não respondeu em {config.ibge_timeout_s():g} s.",
            "evidencia": evidencia,
        }
    except httpx.HTTPError as exc:
        return {
            "status": "indisponivel",
            "codigo": codigo,
            "mensagem": f"Falha de conexão com o IBGE ({type(exc).__name__}).",
            "evidencia": evidencia,
        }

    if resposta.status_code != 200:
        return {
            "status": "indisponivel",
            "codigo": codigo,
            "mensagem": f"O IBGE respondeu com HTTP {resposta.status_code}.",
            "evidencia": evidencia,
        }

    try:
        dados = resposta.json()
    except ValueError:
        return {
            "status": "indisponivel",
            "codigo": codigo,
            "mensagem": "O IBGE devolveu uma resposta que não é JSON.",
            "evidencia": evidencia,
        }

    # Verificado em 2026-11-11: código inexistente devolve HTTP 200 com lista vazia.
    if dados == []:
        return {
            "status": "nao_encontrado",
            "codigo": codigo,
            "mensagem": f"O IBGE não possui a subclasse CNAE {codigo}.",
            "evidencia": evidencia,
        }

    if not isinstance(dados, dict) or dados.get("id") != digitos or not dados.get("descricao"):
        return {
            "status": "indisponivel",
            "codigo": codigo,
            "mensagem": "O IBGE devolveu um formato de resposta inesperado.",
            "evidencia": evidencia,
        }

    return {
        "status": "ok",
        "codigo": codigo,
        "descricao": dados["descricao"],
        "hierarquia": _hierarquia(dados),
        "observacoes": _resumir_observacoes(dados.get("observacoes") or []),
        "evidencia": evidencia,
    }
