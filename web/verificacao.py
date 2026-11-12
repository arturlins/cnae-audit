"""Pós-validação em código da resposta do agente (docs/solucao.md §9.3).

Antes de exibir, o app web confere:
1. pelo menos uma chamada de ferramenta bem-sucedida (exceto pedidos de esclarecimento/recusa);
2. as seções obrigatórias do template;
3. todo código CNAE citado no texto aparece nos argumentos ou retornos das ferramentas;
4. o selo vem do `status_afirmacao` da ferramenta, nunca do texto.
"""

import json
import re
from dataclasses import dataclass, field

from agente.instrucoes import SECAO_ESCLARECIMENTO, SECAO_FORA_DO_ESCOPO, SECOES

# Ex.: 6201-5/01, 6201501, 62.01-5-01, 6201-501
RE_CNAE = re.compile(r"(?<!\d)(\d{2})\.?(\d{2})-?(\d)[/-]?(\d{2})(?!\d)")

STATUS_OK = "ok"
SELOS = {
    "confirmada": "O que te disseram confere com a base",
    "contradita": "O que te disseram não confere com a base",
    "sem_evidencia_suficiente": "Não dá para concluir com os dados disponíveis",
}


@dataclass
class ChamadaFerramenta:
    nome: str
    argumentos: dict
    resultado: dict | None  # None quando o retorno não é JSON
    resultado_bruto: str
    erro: bool = False

    @property
    def status(self) -> str | None:
        return (self.resultado or {}).get("status")


@dataclass
class Verificacao:
    verificada: bool
    tipo: str  # "verificacao" | "esclarecimento" | "fora_do_escopo"
    falhas: list[str] = field(default_factory=list)
    status_afirmacao: str | None = None
    selo: str | None = None
    ferramentas: list[ChamadaFerramenta] = field(default_factory=list)
    sem_veredito: str | None = None  # motivo quando a base não deu veredito


def _carregar_json(bruto) -> dict | None:
    if isinstance(bruto, dict):
        return bruto
    try:
        valor = json.loads(bruto)
    except (TypeError, ValueError):
        return None
    return valor if isinstance(valor, dict) else None


def extrair_ferramentas(run: dict) -> list[ChamadaFerramenta]:
    """Lê as tool calls de `run["tools"]` (RunOutput.to_dict do AgentOS)."""
    chamadas = []
    for tool in run.get("tools") or []:
        if not isinstance(tool, dict) or not tool.get("tool_name"):
            continue
        bruto = tool.get("result")
        chamadas.append(
            ChamadaFerramenta(
                nome=tool["tool_name"],
                argumentos=tool.get("tool_args") or {},
                resultado=_carregar_json(bruto),
                resultado_bruto=bruto if isinstance(bruto, str) else json.dumps(bruto),
                erro=bool(tool.get("tool_call_error")),
            )
        )
    return chamadas


def cnaes_no_texto(texto: str) -> set[str]:
    """Códigos CNAE citados no texto, normalizados para 7 dígitos."""
    return {"".join(m.groups()) for m in RE_CNAE.finditer(texto or "")}


def _cnaes_nas_ferramentas(chamadas: list[ChamadaFerramenta]) -> set[str]:
    texto = " ".join(
        json.dumps(c.argumentos, ensure_ascii=False) + " " + c.resultado_bruto for c in chamadas
    )
    return cnaes_no_texto(texto)


def _tipo_resposta(conteudo: str) -> str:
    if SECAO_ESCLARECIMENTO in conteudo:
        return "esclarecimento"
    if SECAO_FORA_DO_ESCOPO in conteudo:
        return "fora_do_escopo"
    return "verificacao"


def _veredito(chamadas: list[ChamadaFerramenta]) -> tuple[str | None, str | None]:
    """(status_afirmacao, motivo_sem_veredito) da última chamada de validar_enquadramento."""
    validacoes = [c for c in chamadas if c.nome == "validar_enquadramento" and c.resultado]
    if not validacoes:
        return None, "A base de regras não foi consultada nesta resposta."
    ultima = validacoes[-1].resultado
    status = ultima.get("status")
    if status in ("ok", "nao_encontrado"):
        return ultima.get("status_afirmacao"), None
    if status == "erro_fonte":
        return None, "A base de regras está indisponível; nenhum veredito foi dado."
    return None, "A verificação na base de regras não foi concluída (entrada inválida)."


def verificar_resposta(run: dict) -> Verificacao:
    conteudo = run.get("content") or ""
    if not isinstance(conteudo, str):
        conteudo = json.dumps(conteudo, ensure_ascii=False)
    chamadas = extrair_ferramentas(run)
    tipo = _tipo_resposta(conteudo)
    falhas = []

    # 1. Pelo menos uma ferramenta bem-sucedida (pedidos de esclarecimento e recusas são isentos).
    if tipo == "verificacao" and not any(c.status == STATUS_OK for c in chamadas):
        falhas.append("Nenhuma ferramenta foi executada com sucesso nesta resposta.")

    # 2. Seções obrigatórias.
    if tipo == "verificacao":
        faltando = [s for s in SECOES if s not in conteudo]
        if faltando:
            falhas.append("Seções obrigatórias ausentes: " + ", ".join(faltando) + ".")

    # 3. Todo CNAE citado veio de uma ferramenta.
    inventados = cnaes_no_texto(conteudo) - _cnaes_nas_ferramentas(chamadas)
    if inventados:
        codigos = ", ".join(f"{c[:4]}-{c[4]}/{c[5:]}" for c in sorted(inventados))
        falhas.append(f"CNAE citado sem origem em ferramenta: {codigos}.")

    # 4. Selo vem da ferramenta.
    status_afirmacao, sem_veredito = _veredito(chamadas)

    return Verificacao(
        verificada=not falhas,
        tipo=tipo,
        falhas=falhas,
        status_afirmacao=status_afirmacao,
        selo=SELOS.get(status_afirmacao) if status_afirmacao else None,
        ferramentas=chamadas,
        sem_veredito=sem_veredito if tipo == "verificacao" else None,
    )
