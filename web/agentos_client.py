"""The only layer of the web app that talks to the AgentOS HTTP API.

Keeping it thin makes it easy to swap the frontend (e.g. React) without touching the agent.
"""

import logging
import time

import httpx

from agente import config

logger = logging.getLogger("web.agentos")


class AgentOSError(Exception):
    """The AgentOS could not produce a run (down, timed out or answered with an error)."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind  # "indisponivel" | "tempo_esgotado" | "erro_api"
        self.message = message


def run_agent(message: str, session_id: str | None = None) -> dict:
    """POST /agents/{id}/runs with stream=false and return the run JSON (RunOutput.to_dict)."""
    url = f"{config.agentos_url()}/agents/{config.AGENT_ID}/runs"
    data = {"message": message, "stream": "false"}
    if session_id:
        data["session_id"] = session_id
    headers = {}
    key = config.os_security_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    timeout = config.agentos_timeout_s()
    started = time.perf_counter()
    logger.info("POST %s session_id=%s", url, session_id)
    try:
        response = httpx.post(url, data=data, headers=headers, timeout=timeout)
    except httpx.TimeoutException as exc:
        logger.warning("AgentOS timeout after %.1fs", time.perf_counter() - started)
        raise AgentOSError(
            "tempo_esgotado", f"O agente não respondeu em {timeout:g} segundos."
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("AgentOS unreachable: %s", type(exc).__name__)
        raise AgentOSError(
            "indisponivel", "O serviço do agente (AgentOS) está fora do ar ou inacessível."
        ) from exc

    elapsed = time.perf_counter() - started
    logger.info("AgentOS HTTP %s in %.1fs", response.status_code, elapsed)
    if response.status_code != 200:
        raise AgentOSError(
            "erro_api", f"O serviço do agente respondeu com erro (HTTP {response.status_code})."
        )
    try:
        run = response.json()
    except ValueError as exc:
        raise AgentOSError(
            "erro_api", "O serviço do agente devolveu uma resposta inválida."
        ) from exc
    if not isinstance(run, dict):
        raise AgentOSError("erro_api", "O serviço do agente devolveu uma resposta inesperada.")
    if run.get("status") == "ERROR":
        raise AgentOSError("erro_api", "A execução do agente terminou com erro.")
    return run
