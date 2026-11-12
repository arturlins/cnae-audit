"""AgentOS que expõe o agente "verificador-cnae" por HTTP (porta 7777 por padrão).

Uso: `uv run python -m agente.servidor`
Execução: `POST /agents/verificador-cnae/runs` (form: message, stream=false, session_id).
"""

from agno.os import AgentOS

from agente import config
from agente.agente import criar_agente

agent_os = AgentOS(
    id="cnae-audit",
    name="Verificador de CNAE",
    description="API do agente que confere CNAE x modelo de negócio com evidências.",
    agents=[criar_agente()],
    telemetry=False,
)
app = agent_os.get_app()


if __name__ == "__main__":
    agent_os.serve(app="agente.servidor:app", port=config.agentos_port())
