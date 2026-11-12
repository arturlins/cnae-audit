"""App web "Verificador de CNAE" (FastAPI + Jinja2 + HTMX), cliente fino do AgentOS.

Uso: `uv run uvicorn web.main:app --port 8000`
"""

import json
import logging
import uuid
from pathlib import Path

import markdown
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from agente.ferramentas.enquadramento import ErroFonte, carregar_base
from agente.instrucoes import AVISO
from web.agentos_client import AgentOSError, run_agent
from web.mensagem import Formulario, ValorInvalido, montar_mensagem
from web.verificacao import verificar_resposta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("web")

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Verificador de CNAE")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _md(texto: str) -> Markup:
    # Neutraliza HTML vindo do modelo antes de converter o markdown.
    seguro = (texto or "").replace("<", "&lt;")
    return Markup(markdown.markdown(seguro, extensions=["sane_lists"]))


def _json(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, indent=2)


templates.env.filters["md"] = _md
templates.env.filters["tojson_pretty"] = _json


def _rotulos() -> dict[str, str]:
    """Rótulos em linguagem simples do enum modelo_negocio, lidos da própria base de regras."""
    try:
        base, _ = carregar_base()
    except ErroFonte:
        return {}
    return {chave: item["rotulo"] for chave, item in base["modelos_negocio"].items()}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request, "index.html", {"rotulos": _rotulos(), "session_id": str(uuid.uuid4())}
    )


@app.post("/verificar", response_class=HTMLResponse)
def verificar(
    request: Request,
    cnae: str = Form(""),
    modelo_negocio: str = Form(""),
    descricao_livre: str = Form(""),
    afirmacao_compativel: str = Form("nao_sei"),
    anexo_afirmado: str = Form(""),
    folha_12m: str = Form(""),
    receita_bruta_12m: str = Form(""),
    session_id: str = Form(""),
):
    form = Formulario(
        cnae=cnae,
        modelo_negocio=modelo_negocio,
        descricao_livre=descricao_livre,
        afirmacao_compativel=afirmacao_compativel,
        anexo_afirmado=anexo_afirmado,
        folha_12m=folha_12m,
        receita_bruta_12m=receita_bruta_12m,
    )
    try:
        mensagem = montar_mensagem(form, _rotulos())
    except ValorInvalido as exc:
        return templates.TemplateResponse(
            request, "_erro.html", {"titulo": "Confira os valores", "mensagem": str(exc)}
        )

    logger.info("Verificação solicitada: cnae=%r modelo=%r", cnae, modelo_negocio)
    try:
        run = run_agent(mensagem, session_id=session_id or None)
    except AgentOSError as exc:
        logger.warning("Falha ao chamar o AgentOS: %s (%s)", exc.kind, exc.message)
        return templates.TemplateResponse(
            request,
            "_erro.html",
            {
                "titulo": "Não foi possível verificar agora",
                "mensagem": exc.message,
                "tentar_novamente": True,
            },
        )

    verificacao = verificar_resposta(run)
    logger.info(
        "Resposta do agente: run_id=%s ferramentas=%s verificada=%s status_afirmacao=%s falhas=%s",
        run.get("run_id"),
        [c.nome for c in verificacao.ferramentas],
        verificacao.verificada,
        verificacao.status_afirmacao,
        verificacao.falhas,
    )
    return templates.TemplateResponse(
        request,
        "_resultado.html",
        {
            "v": verificacao,
            # O aviso já aparece fixo no topo da tela; evita repeti-lo.
            "conteudo": (run.get("content") or "").replace(AVISO, "", 1),
            "run_id": run.get("run_id"),
            "mensagem": mensagem,
        },
    )
