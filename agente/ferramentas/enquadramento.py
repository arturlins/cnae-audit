"""Ferramenta `validar_enquadramento`: motor de regras determinístico sobre `data/regras_cnae.json`.

Toda decisão (compatibilidade, Fator R, anexo e status da afirmação) é tomada aqui, em código.
O modelo de linguagem apenas escolhe os parâmetros e explica o resultado.
"""

import json
from pathlib import Path

from agente import config
from agente.ferramentas.cnae import CnaeInvalido, formatar_cnae, normalizar_cnae

LIMIAR_FATOR_R_PERCENTUAL = 28  # LC 123/2006, art. 18, §§ 5º-J e 5º-M
ANEXOS_VALIDOS = ("I", "II", "III", "IV", "V")
_ANEXO_POR_NUMERO = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V"}


class ErroFonte(Exception):
    """A base de regras não pôde ser lida ou está malformada."""


def _caminho_relativo(caminho: Path) -> str:
    try:
        return caminho.resolve().relative_to(config.PROJECT_ROOT).as_posix()
    except ValueError:
        return caminho.as_posix()


def carregar_base() -> tuple[dict, str]:
    """Lê a base de regras do disco (sem cache) e devolve (base, caminho relativo)."""
    caminho = config.regras_path()
    try:
        base = json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ErroFonte(f"Base de regras não encontrada em {_caminho_relativo(caminho)}.") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ErroFonte(
            f"Base de regras ilegível em {_caminho_relativo(caminho)} ({type(exc).__name__})."
        ) from exc
    chaves = ("versao", "data_referencia", "fontes_legais", "modelos_negocio", "cnaes")
    if not isinstance(base, dict) or any(chave not in base for chave in chaves):
        raise ErroFonte("Base de regras com estrutura inválida (chaves obrigatórias ausentes).")
    return base, _caminho_relativo(caminho)


def _normalizar_anexo(anexo: str) -> str:
    bruto = str(anexo).strip().upper().removeprefix("ANEXO").strip()
    bruto = _ANEXO_POR_NUMERO.get(bruto, bruto)
    if bruto not in ANEXOS_VALIDOS:
        raise ValueError(f"Anexo '{anexo}' inválido. Use I, II, III, IV ou V.")
    return bruto


def _entrada_invalida(mensagem: str, **extra) -> dict:
    return {"status": "entrada_invalida", "mensagem": mensagem, **extra}


def _fundamentos(base: dict, ids: list[str]) -> list[dict]:
    fontes = base["fontes_legais"]
    return [{"id": i, **fontes[i]} for i in ids if i in fontes]


def _apurar_tributacao(
    tributacao: dict, folha_12m: float | None, receita_bruta_12m: float | None
) -> dict:
    sujeito = tributacao.get("sujeito_fator_r")
    resultado = {
        "confianca": tributacao.get("confianca"),
        "sujeito_fator_r": sujeito,
        "nota": tributacao.get("nota"),
    }
    if sujeito is None:
        resultado["anexo_resultante"] = None
        resultado["situacao"] = "indeterminado"
        resultado["mensagem"] = "A base não define o anexo deste CNAE (zona cinzenta)."
        return resultado
    if sujeito is False:
        resultado["anexo_resultante"] = tributacao["anexo"]
        resultado["situacao"] = "determinado"
        resultado["calculo_fator_r"] = {"aplicavel": False}
        return resultado

    if folha_12m is None or receita_bruta_12m is None:
        resultado["anexo_resultante"] = None
        resultado["situacao"] = "indeterminado"
        resultado["mensagem"] = (
            "Este CNAE depende do Fator R. Informe a folha de pagamento e a receita bruta "
            "dos últimos 12 meses para saber o anexo."
        )
        resultado["calculo_fator_r"] = {
            "aplicavel": True,
            "anexo_se_maior_ou_igual_28": tributacao["anexo_fator_r_alto"],
            "anexo_se_menor_28": tributacao["anexo_fator_r_baixo"],
        }
        return resultado

    # Comparação em inteiros/proporção para evitar erro de ponto flutuante no limiar.
    atinge = folha_12m * 100 >= LIMIAR_FATOR_R_PERCENTUAL * receita_bruta_12m
    anexo = tributacao["anexo_fator_r_alto"] if atinge else tributacao["anexo_fator_r_baixo"]
    razao = folha_12m / receita_bruta_12m
    resultado["anexo_resultante"] = anexo
    resultado["situacao"] = "determinado"
    resultado["calculo_fator_r"] = {
        "aplicavel": True,
        "folha_12m": folha_12m,
        "receita_bruta_12m": receita_bruta_12m,
        "razao": round(razao, 4),
        "razao_percentual": f"{razao * 100:.2f}%",
        "limiar": "28%",
        "regra": (
            f"folha / receita >= 28% -> Anexo {tributacao['anexo_fator_r_alto']}; "
            f"< 28% -> Anexo {tributacao['anexo_fator_r_baixo']}"
        ),
        "anexo_resultante": anexo,
    }
    return resultado


def _comparar(afirmado_ok: bool | None, apurado_definido: bool) -> str:
    if not apurado_definido:
        return "sem_evidencia"
    return "confere" if afirmado_ok else "diverge"


def _status_afirmacao(comparacao: list[dict]) -> str:
    if not comparacao:
        return "sem_evidencia_suficiente"
    resultados = {item["resultado"] for item in comparacao}
    if "diverge" in resultados:
        return "contradita"
    if resultados == {"confere"}:
        return "confirmada"
    return "sem_evidencia_suficiente"


def validar_enquadramento(
    codigo_cnae: str,
    modelo_negocio: str,
    folha_12m: float | None = None,
    receita_bruta_12m: float | None = None,
    afirmacao_compativel: bool | None = None,
    anexo_afirmado: str | None = None,
) -> dict:
    """Verifica, pela base de regras do projeto, se um CNAE combina com o modelo de negócio,
    calcula o Fator R / anexo do Simples Nacional e confronta o que o usuário ouviu.

    Use depois de `consultar_cnae_ibge`. O resultado (`compatibilidade`, `tributacao` e
    `status_afirmacao`) é decidido por esta ferramenta: explique-o, nunca o altere.

    Args:
        codigo_cnae: Código CNAE de 7 dígitos (ex.: "6201-5/01").
        modelo_negocio: Um destes valores exatos: saas_padronizado, desenvolvimento_sob_encomenda,
            licenciamento_customizavel, licenciamento_nao_customizavel, consultoria_ti,
            suporte_tecnico, hospedagem_infraestrutura, portal_conteudo, curso_online_gravado,
            mentoria_treinamento_ao_vivo, ebook_publicacao_digital, marketplace_intermediacao,
            revenda_hardware, promocao_vendas. Se o negócio do usuário não se encaixar claramente
            em um deles, NÃO chame a ferramenta: peça esclarecimento.
        folha_12m: Folha de pagamento dos últimos 12 meses em reais, incluindo pró-labore e
            encargos (opcional; informe junto com receita_bruta_12m).
        receita_bruta_12m: Receita bruta dos últimos 12 meses em reais (opcional, maior que zero).
        afirmacao_compativel: O que disseram ao usuário: True se disseram que o CNAE serve para o
            negócio, False se disseram que não serve, None se ele não afirmou nada sobre isso.
        anexo_afirmado: Anexo do Simples Nacional que disseram ao usuário ("I" a "V"), ou None.

    Returns:
        dict com `status` ("ok", "nao_encontrado", "entrada_invalida" ou "erro_fonte"). Em "ok":
        `compatibilidade` (compativel | incompativel | indeterminado), `regra_aplicada`, `motivo`,
        `cnaes_sugeridos`, `tributacao` (anexo e cálculo do Fator R), `status_afirmacao`
        (confirmada | contradita | sem_evidencia_suficiente), `comparacao`, `fundamento_legal`
        e `evidencia` (arquivo, chave e versão da base).
    """
    try:
        digitos = normalizar_cnae(codigo_cnae)
    except CnaeInvalido as exc:
        return _entrada_invalida(str(exc), campo="codigo_cnae")
    codigo = formatar_cnae(digitos)

    try:
        base, arquivo = carregar_base()
    except ErroFonte as exc:
        return {
            "status": "erro_fonte",
            "mensagem": f"{exc} Não é possível verificar sem a base de regras.",
        }

    modelos = base["modelos_negocio"]
    if modelo_negocio not in modelos:
        return _entrada_invalida(
            f"modelo_negocio '{modelo_negocio}' não existe na base.",
            campo="modelo_negocio",
            valores_validos={chave: item["rotulo"] for chave, item in modelos.items()},
        )

    numeros = {"folha_12m": folha_12m, "receita_bruta_12m": receita_bruta_12m}
    for nome, valor in numeros.items():
        if valor is not None and (isinstance(valor, bool) or not isinstance(valor, (int, float))):
            return _entrada_invalida(f"{nome} deve ser um número em reais.", campo=nome)
    if (folha_12m is None) != (receita_bruta_12m is None):
        return _entrada_invalida(
            "Para o Fator R, informe folha_12m e receita_bruta_12m juntos.", campo="folha_12m"
        )
    if folha_12m is not None and folha_12m < 0:
        return _entrada_invalida("folha_12m não pode ser negativa.", campo="folha_12m")
    if receita_bruta_12m is not None and receita_bruta_12m <= 0:
        return _entrada_invalida(
            "receita_bruta_12m deve ser maior que zero.", campo="receita_bruta_12m"
        )
    if afirmacao_compativel is not None and not isinstance(afirmacao_compativel, bool):
        return _entrada_invalida(
            "afirmacao_compativel deve ser true, false ou nulo.", campo="afirmacao_compativel"
        )
    anexo_norm = None
    if anexo_afirmado is not None and str(anexo_afirmado).strip():
        try:
            anexo_norm = _normalizar_anexo(anexo_afirmado)
        except ValueError as exc:
            return _entrada_invalida(str(exc), campo="anexo_afirmado")

    evidencia = {
        "arquivo": arquivo,
        "versao": base["versao"],
        "data_referencia": base["data_referencia"],
    }
    modelo_info = {"valor": modelo_negocio, "rotulo": modelos[modelo_negocio]["rotulo"]}

    cnae = base["cnaes"].get(codigo)
    if cnae is None:
        return {
            "status": "nao_encontrado",
            "codigo": codigo,
            "modelo_negocio": modelo_info,
            "compatibilidade": "indeterminado",
            "status_afirmacao": "sem_evidencia_suficiente",
            "mensagem": (
                f"O CNAE {codigo} não está na base de regras. Isso não significa que ele seja "
                "incompatível: a base simplesmente não cobre esse código."
            ),
            "cnaes_na_base": sorted(base["cnaes"]),
            "evidencia": {**evidencia, "chave": "cnaes"},
            "aviso": base.get("aviso"),
        }

    regra = next(
        (r for r in cnae.get("regras", []) if r.get("modelo_negocio") == modelo_negocio), None
    )
    if regra:
        compatibilidade = regra["resultado"]
        motivo = regra["motivo"]
        chave = f"cnaes.{codigo}.regras[id={regra['id']}]"
    else:
        compatibilidade = "indeterminado"
        motivo = (
            "A base não tem regra para este CNAE com este modelo de negócio. Ausência de regra "
            "não significa incompatibilidade."
        )
        chave = f"cnaes.{codigo}.regras"

    sugeridos = []
    if compatibilidade != "compativel":
        for outro_codigo, outro in base["cnaes"].items():
            if outro_codigo == codigo:
                continue
            for r in outro.get("regras", []):
                if r.get("modelo_negocio") == modelo_negocio and r.get("resultado") == "compativel":
                    sugeridos.append(
                        {
                            "codigo": outro_codigo,
                            "denominacao": outro["denominacao"],
                            "regra": r["id"],
                        }
                    )

    tributacao = _apurar_tributacao(cnae["tributacao"], folha_12m, receita_bruta_12m)

    comparacao = []
    if afirmacao_compativel is not None:
        definido = compatibilidade in ("compativel", "incompativel")
        comparacao.append(
            {
                "campo": "compatibilidade",
                "afirmado": "compativel" if afirmacao_compativel else "incompativel",
                "apurado": compatibilidade,
                "resultado": _comparar(
                    afirmacao_compativel == (compatibilidade == "compativel"), definido
                ),
            }
        )
    if anexo_norm is not None:
        apurado = tributacao["anexo_resultante"]
        comparacao.append(
            {
                "campo": "anexo",
                "afirmado": anexo_norm,
                "apurado": apurado,
                "resultado": _comparar(anexo_norm == apurado, apurado is not None),
            }
        )

    return {
        "status": "ok",
        "codigo": codigo,
        "denominacao": cnae["denominacao"],
        "modelo_negocio": modelo_info,
        "compatibilidade": compatibilidade,
        "regra_aplicada": regra["id"] if regra else None,
        "motivo": motivo,
        "cnaes_sugeridos": sugeridos,
        "tributacao": tributacao,
        "status_afirmacao": _status_afirmacao(comparacao),
        "comparacao": comparacao,
        "fundamento_legal": _fundamentos(base, cnae["tributacao"].get("fundamentos", [])),
        "evidencia": {
            **evidencia,
            "chave": chave,
            "chave_tributacao": f"cnaes.{codigo}.tributacao",
        },
        "aviso": base.get("aviso"),
    }
