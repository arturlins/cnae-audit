"""Executa os casos T01–T07 pela API HTTP do AgentOS e grava as evidências em `evidencias/`.

Uso:
    uv run python scripts/run_casos.py              # todos os casos
    uv run python scripts/run_casos.py T03 T07      # só alguns

O script sobe o próprio AgentOS (`python -m agente.servidor`) em um subprocesso, porque o T06
precisa reiniciar o serviço com variáveis de ambiente alteradas. A porta 7777 (ou AGENTOS_PORT)
precisa estar livre. O resultado esperado de cada caso foi definido pela inspeção de
`data/regras_cnae.json` e da API do IBGE, não pela resposta do modelo (docs/testes.md).
"""

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agente import config
from agente.instrucoes import SECAO_ESCLARECIMENTO
from web.mensagem import Formulario, montar_mensagem
from web.verificacao import ChamadaFerramenta, verificar_resposta

EVIDENCIAS = ROOT / "evidencias"
REGRAS = ROOT / "data" / "regras_cnae.json"
REGRAS_BAK = ROOT / "data" / "regras_cnae.json.bak"
IBGE_INVALIDO = "http://ibge-indisponivel.invalid/api/v2/cnae"
REGRAS_AUSENTE = "data/regras_cnae_AUSENTE.json"
REGRA_T07 = "R-6201-SAAS"


def _rotulos() -> dict[str, str]:
    base = json.loads(REGRAS.read_text(encoding="utf-8"))
    return {k: v["rotulo"] for k, v in base["modelos_negocio"].items()}


def _msg_form(**campos) -> str:
    """Mesma mensagem que o app web monta a partir do formulário."""
    return montar_mensagem(Formulario(**campos), _rotulos())


# ---------------------------------------------------------------- checagens


@dataclass
class Execucao:
    run: dict
    chamadas: list[ChamadaFerramenta]
    conteudo: str

    def de(self, nome: str) -> list[ChamadaFerramenta]:
        return [c for c in self.chamadas if c.nome == nome]

    def ultima(self, nome: str) -> dict:
        lista = [c for c in self.de(nome) if c.resultado]
        return lista[-1].resultado if lista else {}


Checagem = tuple[str, bool]


def _ibge_codigos(e: Execucao, status: str = "ok") -> set[str]:
    return {
        c.resultado.get("codigo")
        for c in e.de("consultar_cnae_ibge")
        if c.resultado and c.resultado.get("status") == status
    }


def checar_t01(e: Execucao) -> list[Checagem]:
    r = next((c.resultado for c in e.de("consultar_cnae_ibge") if c.resultado), {})
    return [
        ("consultar_cnae_ibge foi chamada", bool(e.de("consultar_cnae_ibge"))),
        ("IBGE devolveu status ok para 6203-1/00", r.get("codigo") == "6203-1/00"),
        (
            "descrição oficial contém 'NÃO CUSTOMIZÁVEIS'",
            "NÃO CUSTOMIZÁVEIS" in (r.get("descricao") or "").upper(),
        ),
        ("evidência com URL e data/hora", bool((r.get("evidencia") or {}).get("consultado_em"))),
        ("resposta diz que a afirmação confere", "confirm" in e.conteudo.lower()),
    ]


def checar_t02(e: Execucao) -> list[Checagem]:
    r = e.ultima("validar_enquadramento")
    trib = r.get("tributacao") or {}
    args = (e.de("validar_enquadramento") or [ChamadaFerramenta("", {}, None, "")])[-1].argumentos
    return [
        ("validar_enquadramento foi chamada", bool(e.de("validar_enquadramento"))),
        (
            "modelo_negocio = licenciamento_nao_customizavel",
            args.get("modelo_negocio") == "licenciamento_nao_customizavel",
        ),
        (
            "folha e receita repassadas",
            args.get("folha_12m") == 30000 and args.get("receita_bruta_12m") == 100000,
        ),
        (
            "compatível pela regra R-6203-LIC-NAO-CUSTOM",
            r.get("compatibilidade") == "compativel"
            and r.get("regra_aplicada") == "R-6203-LIC-NAO-CUSTOM",
        ),
        ("Fator R 30% -> Anexo III", trib.get("anexo_resultante") == "III"),
        ("status_afirmacao = confirmada", r.get("status_afirmacao") == "confirmada"),
    ]


def checar_t03(e: Execucao) -> list[Checagem]:
    r = e.ultima("validar_enquadramento")
    sugeridos = {s["codigo"] for s in r.get("cnaes_sugeridos") or []}
    return [
        (
            "validar_enquadramento com saas_padronizado e afirmação 'serve'",
            any(
                c.argumentos.get("modelo_negocio") == "saas_padronizado"
                and c.argumentos.get("afirmacao_compativel") is True
                for c in e.de("validar_enquadramento")
            ),
        ),
        (
            "regra R-6201-SAAS -> incompativel",
            r.get("regra_aplicada") == "R-6201-SAAS" and r.get("compatibilidade") == "incompativel",
        ),
        ("status_afirmacao = contradita", r.get("status_afirmacao") == "contradita"),
        ("sugere 6311-9/00 e 6319-4/00", {"6311-9/00", "6319-4/00"} <= sugeridos),
        (
            "algum CNAE sugerido foi consultado no IBGE",
            bool(_ibge_codigos(e) & {"6311-9/00", "6319-4/00"}),
        ),
    ]


def checar_t04(e: Execucao) -> list[Checagem]:
    r = e.ultima("validar_enquadramento")
    return [
        ("IBGE encontrou 4711-3/02", "4711-3/02" in _ibge_codigos(e)),
        ("base respondeu nao_encontrado", r.get("status") == "nao_encontrado"),
        (
            "status_afirmacao = sem_evidencia_suficiente",
            r.get("status_afirmacao") == "sem_evidencia_suficiente",
        ),
        ("resposta não chama o CNAE de incompatível", "incompat" not in e.conteudo.lower()),
    ]


def _sem_veredito(e: Execucao) -> bool:
    return not any(
        c.resultado and c.resultado.get("status") == "ok" for c in e.de("validar_enquadramento")
    )


def checar_t05a(e: Execucao) -> list[Checagem]:
    return [
        ("pede esclarecimento (seção própria)", SECAO_ESCLARECIMENTO in e.conteudo),
        ("nenhum veredito da base foi dado", _sem_veredito(e)),
    ]


def checar_t05b(e: Execucao) -> list[Checagem]:
    invalida = any(c.status == "entrada_invalida" for c in e.chamadas)
    return [
        (
            "entrada_invalida vinda do código ou pedido de esclarecimento",
            invalida or SECAO_ESCLARECIMENTO in e.conteudo,
        ),
        ("nenhum veredito da base foi dado", _sem_veredito(e)),
    ]


def checar_t06a(e: Execucao) -> list[Checagem]:
    r = e.ultima("validar_enquadramento")
    return [
        ("IBGE devolveu indisponivel", bool(_ibge_codigos(e, "indisponivel"))),
        ("nenhuma consulta ao IBGE apresentada como ok", not _ibge_codigos(e)),
        ("resposta declara a indisponibilidade", "indispon" in e.conteudo.lower()),
        ("conclusão só pela base (contradita)", r.get("status_afirmacao") == "contradita"),
    ]


def checar_t06b(e: Execucao) -> list[Checagem]:
    texto = e.conteudo.lower()
    return [
        (
            "validar_enquadramento devolveu erro_fonte",
            e.ultima("validar_enquadramento").get("status") == "erro_fonte",
        ),
        ("nenhum veredito na resposta", "contradita" not in texto and "confirmada" not in texto),
    ]


def checar_t07(antes: str):
    def checar(e: Execucao) -> list[Checagem]:
        return [
            ("status_afirmacao", e.ultima("validar_enquadramento").get("status_afirmacao") == antes)
        ]

    return checar


# ---------------------------------------------------------------- casos


@dataclass
class Caso:
    id: str
    titulo: str
    mensagem: str
    checar: Callable[[Execucao], list[Checagem]]
    esperado: str
    env: dict = field(default_factory=dict)


def montar_casos() -> list[Caso]:
    msg_saas = _msg_form(
        cnae="6201-5/01", modelo_negocio="saas_padronizado", afirmacao_compativel="sim"
    )
    return [
        Caso(
            "T01",
            "Primeira ferramenta (IBGE) e informação conhecida confirmada",
            "O CNAE 6203-1/00 é de licenciamento de programas de computador não customizáveis? "
            "Confira na fonte oficial e mostre a evidência.",
            checar_t01,
            "consultar_cnae_ibge(6203-1/00) ok; descrição oficial 'DESENVOLVIMENTO E "
            "LICENCIAMENTO DE PROGRAMAS DE COMPUTADOR NÃO CUSTOMIZÁVEIS'; afirmação confirmada; "
            "URL + timestamp",
        ),
        Caso(
            "T02",
            "Segunda ferramenta (base de regras + Fator R)",
            _msg_form(
                cnae="6203-1/00",
                modelo_negocio="licenciamento_nao_customizavel",
                anexo_afirmado="III",
                folha_12m="30000",
                receita_bruta_12m="100000",
            ),
            checar_t02,
            "R-6203-LIC-NAO-CUSTOM compativel; Fator R 30% >= 28% -> Anexo III; confirmada",
        ),
        Caso(
            "T03",
            "Afirmação do usuário contradita pela base",
            "Vendo um SaaS padronizado a R$ 99/mês, igual para todos os clientes, e meu contador "
            "disse que posso usar o CNAE 6201-5/01. Está certo?",
            checar_t03,
            "R-6201-SAAS incompativel; contradita; sugere 6311-9/00 e 6319-4/00 consultados no IBGE",
        ),
        Caso(
            "T04",
            "CNAE real fora da base",
            _msg_form(
                cnae="4711-3/02", modelo_negocio="revenda_hardware", afirmacao_compativel="sim"
            ),
            checar_t04,
            "IBGE ok (4711-3/02); base nao_encontrado; sem_evidencia_suficiente; nada inventado",
        ),
        Caso(
            "T05a",
            "Pergunta ambígua (sem CNAE)",
            "Posso usar o CNAE de desenvolvimento?",
            checar_t05a,
            "Pedido de esclarecimento; nenhum veredito",
        ),
        Caso(
            "T05b",
            "CNAE malformado",
            "Meu CNAE é 62015 e vendo assinatura de um software padronizado pela internet. "
            "Esse CNAE serve?",
            checar_t05b,
            "entrada_invalida vinda do código ou pedido de esclarecimento; nenhum veredito",
        ),
        Caso(
            "T06a",
            "IBGE indisponível",
            msg_saas,
            checar_t06a,
            "IBGE indisponivel declarado; conclusão só pela base (contradita)",
            env={"IBGE_BASE_URL": IBGE_INVALIDO},
        ),
        Caso(
            "T06b",
            "Base de regras ausente",
            msg_saas,
            checar_t06b,
            "validar_enquadramento erro_fonte; nenhum veredito",
            env={"REGRAS_PATH": REGRAS_AUSENTE},
        ),
    ]


# ---------------------------------------------------------------- AgentOS


class AgentOS:
    def __init__(self, env_extra: dict, nome_log: str):
        self.env_extra = env_extra
        self.log = EVIDENCIAS / "logs" / f"agentos_{nome_log}.log"
        self.proc: subprocess.Popen | None = None

    def __enter__(self):
        self.log.parent.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, **self.env_extra, "PYTHONIOENCODING": "utf-8"}
        self._arquivo = self.log.open("w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "agente.servidor"],
            cwd=ROOT,
            env=env,
            stdout=self._arquivo,
            stderr=subprocess.STDOUT,
        )
        limite = time.time() + 90
        while time.time() < limite:
            if self.proc.poll() is not None:
                raise RuntimeError(f"AgentOS encerrou ao iniciar; veja {self.log}")
            try:
                if httpx.get(f"{config.agentos_url()}/health", timeout=2).status_code == 200:
                    return self
            except httpx.HTTPError:
                pass
            time.sleep(1)
        raise RuntimeError("AgentOS não ficou pronto em 90 s")

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self._arquivo.close()


def _sanitizar(texto: str) -> str:
    for nome in ("GOOGLE_API_KEY", "OS_SECURITY_KEY"):
        valor = os.getenv(nome)
        if valor:
            texto = texto.replace(valor, f"<{nome}>")
    return texto


# O plano gratuito do Gemini aceita 5 requisições por minuto e cada caso faz de 3 a 4
# chamadas ao modelo: no plano gratuito use CASOS_PAUSA_S=60 para um 429 não contaminar o caso seguinte.
PAUSA_ENTRE_CASOS_S = float(os.getenv("CASOS_PAUSA_S", "5"))
_ultimo_envio: float | None = None


def _aguardar_cota() -> None:
    global _ultimo_envio
    if _ultimo_envio is not None:
        restante = PAUSA_ENTRE_CASOS_S - (time.monotonic() - _ultimo_envio)
        if restante > 0:
            print(f"         (pausa de {restante:.0f} s pela cota do modelo)")
            time.sleep(restante)
    _ultimo_envio = time.monotonic()


def executar(caso_id: str, mensagem: str) -> tuple[dict, dict]:
    _aguardar_cota()
    url = f"{config.agentos_url()}/agents/{config.AGENT_ID}/runs"
    form = {"message": mensagem, "stream": "false", "session_id": f"{caso_id}-{uuid.uuid4()}"}
    headers = {}
    if config.os_security_key():
        headers["Authorization"] = f"Bearer {config.os_security_key()}"
    inicio = datetime.now(UTC).isoformat(timespec="seconds")
    requisicao = {"metodo": "POST", "url": url, "form": form, "enviado_em": inicio}
    try:
        resposta = httpx.post(url, data=form, headers=headers, timeout=config.agentos_timeout_s())
    except httpx.HTTPError as exc:
        # Registra o caso como falho em vez de abortar a bateria inteira.
        return requisicao, {"status_http": None, "corpo": {"erro_http": repr(exc)}}
    try:
        corpo = resposta.json()
    except ValueError:
        corpo = {"texto_bruto": resposta.text}
    return requisicao, {"status_http": resposta.status_code, "corpo": corpo}


def registrar(
    caso_id: str,
    titulo: str,
    esperado: str,
    requisicao: dict,
    resposta: dict,
    checar,
    extra: dict | None = None,
) -> dict:
    run = resposta["corpo"] if isinstance(resposta["corpo"], dict) else {}
    verificacao = verificar_resposta(run)
    execucao = Execucao(run, verificacao.ferramentas, run.get("content") or "")
    checagens = [("HTTP 200", resposta["status_http"] == 200)] + checar(execucao)
    checagens.append(("pós-validação do app web aprovou", verificacao.verificada))
    passou = all(ok for _, ok in checagens)
    base = {}
    if REGRAS.exists():
        dados = json.loads(REGRAS.read_text(encoding="utf-8"))
        base = {"versao": dados["versao"], "data_referencia": dados["data_referencia"]}
    registro = {
        "caso": caso_id,
        "titulo": titulo,
        "esperado": esperado,
        "situacao": "passou" if passou else "falhou",
        "checagens": [{"descricao": d, "ok": ok} for d, ok in checagens],
        "pos_validacao": {
            "verificada": verificacao.verificada,
            "falhas": verificacao.falhas,
            "status_afirmacao": verificacao.status_afirmacao,
        },
        "ferramentas_executadas": [
            {"nome": c.nome, "argumentos": c.argumentos, "status": c.status}
            for c in verificacao.ferramentas
        ],
        "modelo": run.get("model"),
        "base_regras": base,
        "requisicao": requisicao,
        "resposta": resposta,
        **(extra or {}),
    }
    arquivo = EVIDENCIAS / f"{caso_id}.json"
    arquivo.write_text(
        _sanitizar(json.dumps(registro, ensure_ascii=False, indent=2)), encoding="utf-8"
    )
    marca = "PASSOU" if passou else "FALHOU"
    print(f"[{marca}] {caso_id} {titulo} -> {arquivo.relative_to(ROOT)}")
    for d, ok in checagens:
        if not ok:
            print(f"         x {d}")
    return registro


def _regra_t07(base: dict) -> dict:
    return next(r for r in base["cnaes"]["6201-5/01"]["regras"] if r["id"] == REGRA_T07)


def executar_t07() -> dict:
    """Altera a regra R-6201-SAAS (incompativel -> compativel), repete a consulta em nova
    sessão e restaura a base. Sem cache: a ferramenta relê o JSON a cada chamada."""
    mensagem = _msg_form(
        cnae="6201-5/01", modelo_negocio="saas_padronizado", afirmacao_compativel="sim"
    )
    shutil.copy2(REGRAS, REGRAS_BAK)
    try:
        original = json.loads(REGRAS.read_text(encoding="utf-8"))
        antes_valor = _regra_t07(original)["resultado"]
        req, resp = executar("T07-antes", mensagem)
        r1 = registrar(
            "T07-antes",
            "Antes da alteração da base",
            "R-6201-SAAS incompativel -> contradita",
            req,
            resp,
            checar_t07("contradita"),
            {
                "dado_alterado": {
                    "chave": f"cnaes.6201-5/01.regras[id={REGRA_T07}].resultado",
                    "valor": antes_valor,
                }
            },
        )
        alterada = json.loads(REGRAS.read_text(encoding="utf-8"))
        regra = _regra_t07(alterada)
        regra["resultado"] = "compativel"
        regra["motivo"] = "[T07] Alteração temporária de teste: regra marcada como compatível."
        REGRAS.write_text(json.dumps(alterada, ensure_ascii=False, indent=2), encoding="utf-8")
        req, resp = executar("T07-depois", mensagem)
        r2 = registrar(
            "T07-depois",
            "Depois da alteração da base (nova sessão)",
            "R-6201-SAAS compativel -> confirmada",
            req,
            resp,
            checar_t07("confirmada"),
            {
                "dado_alterado": {
                    "chave": f"cnaes.6201-5/01.regras[id={REGRA_T07}].resultado",
                    "valor": "compativel",
                }
            },
        )
    finally:
        shutil.move(REGRAS_BAK, REGRAS)
    restaurada = _regra_t07(json.loads(REGRAS.read_text(encoding="utf-8")))["resultado"]
    print(f"         base restaurada: {REGRA_T07}.resultado = {restaurada}")
    return {"antes": r1["situacao"], "depois": r2["situacao"], "restaurado": restaurada}


def main(filtro: list[str]) -> int:
    if not os.getenv("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY não definida (.env). Veja .env.example.")
        return 2
    EVIDENCIAS.mkdir(exist_ok=True)
    casos = montar_casos()

    def quer(caso_id: str) -> bool:
        return not filtro or any(caso_id.startswith(f) for f in filtro)

    resumo = []
    normais = [c for c in casos if not c.env and quer(c.id)]
    if normais or quer("T07"):
        with AgentOS({}, "padrao"):
            for c in normais:
                req, resp = executar(c.id, c.mensagem)
                resumo.append(registrar(c.id, c.titulo, c.esperado, req, resp, c.checar))
            if quer("T07"):
                executar_t07()
    for c in (c for c in casos if c.env and quer(c.id)):
        with AgentOS(c.env, c.id):
            req, resp = executar(c.id, c.mensagem)
            resumo.append(registrar(c.id, c.titulo, c.esperado, req, resp, c.checar))

    print(f"\nModelo: {config.gemini_model_id()}  |  evidências em {EVIDENCIAS.relative_to(ROOT)}/")
    return 0 if all(r["situacao"] == "passou" for r in resumo) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
