"""Monta a mensagem enviada ao agente a partir do formulário do app web."""

from dataclasses import dataclass

OUTRO = "outro"


class ValorInvalido(ValueError):
    pass


def ler_reais(texto: str | None, campo: str) -> float | None:
    """Converte "30.000,50", "30000.50" ou "30000" em float; vazio vira None."""
    bruto = (texto or "").strip().replace("R$", "").replace(" ", "")
    if not bruto:
        return None
    if "," in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    elif bruto.count(".") > 1 or (bruto.count(".") == 1 and len(bruto.split(".")[1]) == 3):
        bruto = bruto.replace(".", "")  # separador de milhar: "30.000" ou "1.000.000"
    try:
        valor = float(bruto)
    except ValueError as exc:
        raise ValorInvalido(f"{campo}: use apenas números (ex.: 30000 ou 30.000,00).") from exc
    if valor < 0:
        raise ValorInvalido(f"{campo}: o valor não pode ser negativo.")
    return valor


@dataclass
class Formulario:
    cnae: str
    modelo_negocio: str  # valor do enum, ou OUTRO
    descricao_livre: str = ""
    afirmacao_compativel: str = "nao_sei"  # sim | nao | nao_sei
    anexo_afirmado: str = ""  # I..V ou vazio
    folha_12m: str = ""
    receita_bruta_12m: str = ""


def _formatar_reais(valor: float) -> str:
    return f"{valor:.2f}"


def montar_mensagem(form: Formulario, rotulos: dict[str, str]) -> str:
    """Mensagem em linguagem natural, com os dados do formulário rotulados explicitamente."""
    folha = ler_reais(form.folha_12m, "Folha de pagamento")
    receita = ler_reais(form.receita_bruta_12m, "Receita bruta")

    linhas = ["Verifique se o CNAE da minha empresa combina com o que ela faz."]
    linhas.append(f"- CNAE: {form.cnae.strip() or '(não informado)'}")
    if form.modelo_negocio and form.modelo_negocio != OUTRO and form.modelo_negocio in rotulos:
        linhas.append(
            f"- O que minha empresa faz: {rotulos[form.modelo_negocio]} "
            f"(modelo_negocio: {form.modelo_negocio})"
        )
    else:
        descricao = form.descricao_livre.strip() or "(não informado)"
        linhas.append(
            f'- O que minha empresa faz (com minhas palavras, não sei qual opção é): "{descricao}"'
        )
    if form.afirmacao_compativel == "sim":
        linhas.append("- Me disseram que esse CNAE serve para o meu negócio.")
    elif form.afirmacao_compativel == "nao":
        linhas.append("- Me disseram que esse CNAE NÃO serve para o meu negócio.")
    if form.anexo_afirmado:
        linhas.append(
            f"- Me disseram que meu anexo do Simples Nacional é o Anexo {form.anexo_afirmado}."
        )
    if folha is not None:
        linhas.append(f"- Folha de pagamento dos últimos 12 meses: R$ {_formatar_reais(folha)}")
    if receita is not None:
        linhas.append(f"- Receita bruta dos últimos 12 meses: R$ {_formatar_reais(receita)}")
    return "\n".join(linhas)
