# Verificador de CNAE

Aplicação web que ajuda pessoas leigas (founders de startups, quem vende SaaS ou infoprodutos) a ter uma noção se o **CNAE** da empresa combina com o modelo de negócio, e serve de ponto de partida de pesquisa para contadores e advogados.

> ⚠️ Material de referência, não substitui consulta a um contador ou advogado. Não é consultoria.

Por trás da tela há um **agente Agno** exposto como **API HTTP pelo AgentOS**. O agente usa duas ferramentas autorais:

- `consultar_cnae_ibge` consulta a API pública do IBGE;
- `validar_enquadramento` aplica o motor de regras sobre `data/regras_cnae.json`, inclusive o Fator R.

O app web confere a resposta em código antes de exibi-la.

Entrega da atividade *Agente com ferramentas e validação de informações* (Sistemas Inteligentes Aplicados, CESMAC). Requisitos em [`docs/atividade.md`](docs/atividade.md).

```text
Usuário → app web (FastAPI, :8000) → API do AgentOS (:7777) → agente Agno (Gemini)
                                                                 ├─ consultar_cnae_ibge   → API do IBGE
                                                                 └─ validar_enquadramento → data/regras_cnae.json
Usuário ← tela com selo, explicação e "Onde conferir" ← pós-validação em código (web/verificacao.py)
```

## Onde está cada item da entrega

| Item da entrega (atividade §6) | Onde |
| --- | --- |
| 1. Código do agente, das ferramentas, da API e da integração | Agente: [`agente/agente.py`](agente/agente.py) e [`agente/instrucoes.py`](agente/instrucoes.py). Ferramentas: [`agente/ferramentas/`](agente/ferramentas/). AgentOS: [`agente/servidor.py`](agente/servidor.py). Integração: [`web/`](web/), com a chamada à API em [`web/agentos_client.py`](web/agentos_client.py) |
| 2. Dados de demonstração | [`data/regras_cnae.json`](data/regras_cnae.json), documentado em [`docs/dados.md`](docs/dados.md). A API do IBGE é pública e não exige carga |
| 3. Dependências e configuração | [`pyproject.toml`](pyproject.toml) + [`uv.lock`](uv.lock) (versões fixadas), [`.python-version`](.python-version) (3.12) e [`.env.example`](.env.example) |
| 4. README de execução | Este arquivo (resumo) e [`docs/reproducao.md`](docs/reproducao.md) (guia de reprodução passo a passo, com comandos para PowerShell e bash e a saída esperada de cada passo) |
| 5. Documentação da solução | [`docs/solucao.md`](docs/solucao.md) (objetivo, arquitetura, agente, validação), [`docs/ferramentas.md`](docs/ferramentas.md) (contratos) e [`docs/dados.md`](docs/dados.md) (fontes) |
| 6. Relatório dos oito casos de teste | [`docs/testes.md`](docs/testes.md), com evidências em [`evidencias/`](evidencias/) |
| 7. Participantes, contribuições e uso de IA | Seção [Participante](#participante) abaixo e [`docs/uso-de-ia.md`](docs/uso-de-ia.md) |

## Requisitos

- [uv](https://docs.astral.sh/uv/). Ele instala o Python 3.12 indicado em `.python-version`.
- Uma chave da API do Google Gemini ([Google AI Studio](https://aistudio.google.com/apikey)).
- Acesso à internet, para o Gemini e a API do IBGE.

## Instalação e configuração

```bash
uv sync                  # cria .venv com as versões do uv.lock
cp .env.example .env     # depois edite o .env e preencha GOOGLE_API_KEY
```

Variáveis (todas em [`.env.example`](.env.example)):

| Variável | Padrão | Para quê |
| --- | --- | --- |
| `GOOGLE_API_KEY` | — | Chave do Gemini (obrigatória). Só o AgentOS a lê; o navegador nunca a recebe |
| `GEMINI_MODEL_ID` | `gemini-3.6-flash` | Modelo usado pelo agente (provedor: Google Gemini, via `agno.models.google.Gemini`) |
| `GEMINI_TIMEOUT_S` | `30` | Timeout de cada requisição ao Gemini |
| `AGENTOS_PORT` / `AGENTOS_DB` | `7777` / `tmp/agentos.db` | Porta do AgentOS e SQLite **só de sessões** (não é fonte de dados do domínio) |
| `OS_SECURITY_KEY` | vazio | Opcional. Se definida, o AgentOS exige `Authorization: Bearer <chave>`, e o app web a envia |
| `IBGE_BASE_URL` / `IBGE_TIMEOUT_S` | API do IBGE / `5` | Fonte externa e timeout |
| `REGRAS_PATH` | `data/regras_cnae.json` | Base de regras |
| `AGENTOS_URL` / `AGENTOS_TIMEOUT_S` | `http://localhost:7777` / `120` | Para onde o app web envia as requisições e quanto espera |

**Preparação dos dados:** nenhuma. A base de regras já está versionada e é relida a cada chamada, sem cache. Para alterar um dado, basta editar o JSON (procedimento em [`docs/dados.md`](docs/dados.md)). A API do IBGE é consultada ao vivo.

## Como iniciar

São dois processos, cada um em seu terminal:

```bash
# 1) AgentOS (API do agente) em http://localhost:7777  (Swagger em /docs)
uv run python -m agente.servidor

# 2) App web em http://localhost:8000
uv run uvicorn web.main:app --port 8000
```

## Chamada HTTP de exemplo

O endpoint de execução recebe campos de formulário. Com `stream=false`, a resposta é um JSON: o texto do agente fica em `content`, e as chamadas de ferramenta, com argumentos e retornos, ficam em `tools`.

```bash
curl --fail-with-body -sS \
  http://localhost:7777/agents/verificador-cnae/runs \
  --data-urlencode 'message=Vendo assinatura de um sistema SaaS padronizado e meu contador disse que posso usar o CNAE 6201-5/01. Isso confere?' \
  --data-urlencode 'stream=false'
```

Resposta recebida (trecho; a íntegra está em [`evidencias/curl_exemplo.json`](evidencias/curl_exemplo.json)):

```json
{
  "run_id": "04314c2a-959c-4dc4-9ff6-df45969ac6ae",
  "agent_id": "verificador-cnae",
  "model": "gemini-3.6-flash",
  "status": "COMPLETED",
  "content": "> ⚠️ Material de referência, não substitui consulta a um contador ou advogado.\n\nEntendi seu negócio como: Vendo assinatura de um sistema na internet, igual para todos os clientes (SaaS).\n\n## Resultado\nCompatibilidade: incompativel\nStatus da afirmação: contradita\n\n## Em linguagem simples\n(...)",
  "tools": [
    {
      "tool_name": "consultar_cnae_ibge",
      "tool_args": {
        "codigo_cnae": "6201-5/01"
      },
      "result (JSON, resumido)": {
        "status": "ok",
        "codigo": "6201-5/01",
        "descricao": "DESENVOLVIMENTO DE PROGRAMAS DE COMPUTADOR SOB ENCOMENDA",
        "evidencia": {
          "fonte": "API CNAE do IBGE (servicodados.ibge.gov.br)",
          "url": "https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/6201501",
          "consultado_em": "2026-11-12T03:39:10+00:00"
        }
      }
    },
    {
      "tool_name": "validar_enquadramento",
      "tool_args": {
        "modelo_negocio": "saas_padronizado",
        "codigo_cnae": "6201-5/01",
        "afirmacao_compativel": true
      },
      "result (JSON, resumido)": {
        "status": "ok",
        "compatibilidade": "incompativel",
        "regra_aplicada": "R-6201-SAAS",
        "cnaes_sugeridos": [
          {
            "codigo": "6311-9/00",
            "denominacao": "Tratamento de dados, provedores de serviços de aplicação e serviços de hospedagem na internet",
            "regra": "R-6311-SAAS"
          },
          {
            "codigo": "6319-4/00",
            "denominacao": "Portais, provedores de conteúdo e outros serviços de informação na internet",
            "regra": "R-6319-SAAS"
          }
        ],
        "status_afirmacao": "contradita",
        "evidencia": {
          "arquivo": "data/regras_cnae.json",
          "versao": "1.0.0",
          "data_referencia": "2026-11-11",
          "chave": "cnaes.6201-5/01.regras[id=R-6201-SAAS]",
          "chave_tributacao": "cnaes.6201-5/01.tributacao"
        }
      }
    },
    {
      "...": "+ consultar_cnae_ibge 6311-9/00 e 6319-4/00"
    }
  ]
}
```

## Jornada no projeto (T08), passo a passo

1. Inicie os dois processos (seção anterior) e abra `http://localhost:8000`.
2. Em **CNAE registrado ou sugerido**, digite `6201-5/01`.
3. Em **O que sua empresa faz?**, escolha *"Vendo assinatura de um sistema na internet, igual para todos os clientes (SaaS)"*.
4. Em **Esse CNAE serve para o meu negócio?**, escolha *"Disseram que sim"*.
5. Clique em **Verificar**. O botão é desabilitado e aparece "Verificando…" enquanto o app web chama `POST /agents/verificador-cnae/runs`.
6. O resultado mostra:
   - o aviso no topo;
   - o selo **"O que te disseram não confere com a base"** (vem do `status_afirmacao` da ferramenta, não do texto do modelo);
   - a explicação em linguagem simples, com os CNAEs sugeridos (`6311-9/00` / `6319-4/00`);
   - **Onde conferir**: regra `R-6201-SAAS` da base, URLs do IBGE com data e hora, e artigos da LC 123/2006;
   - as **ferramentas executadas**, com argumentos e retornos brutos.
7. Se o AgentOS estiver fora do ar ou demorar demais, a tela mostra uma mensagem amigável com "tentar novamente", nunca um resultado parcial.

As capturas e o log do backend dessa jornada estão em [`evidencias/T08/`](evidencias/T08/).

## Testes

```bash
uv run pytest                          # testes unitários (ferramentas, regras, pós-validação, app web)
uv run ruff check .                    # lint
uv run python scripts/run_casos.py     # casos T01–T07 pela API, com o modelo real; grava evidencias/
```

O `run_casos.py` sobe o próprio AgentOS, então a porta 7777 precisa estar livre. No T06 ele reinicia o serviço com o IBGE ou a base indisponíveis. No T07 ele altera e depois restaura uma regra da base. A pausa entre os casos é de 5 s (`CASOS_PAUSA_S`). No plano gratuito do Gemini (5 requisições/min, 20/dia), use `CASOS_PAUSA_S=60`, e a bateria completa não cabe na cota de um dia. Relatório em [`docs/testes.md`](docs/testes.md). O passo a passo completo, com a saída esperada de cada comando, como conferir as evidências e a solução de problemas, está em [`docs/reproducao.md`](docs/reproducao.md).

## Participante

Atividade **individual**.

| Participante | Contribuição |
| --- | --- |
| Artur Lins | Todo o trabalho: recorte do problema, especificação, base de regras e conferência da base legal, ferramentas, agente e AgentOS, app web, testes e documentação. O uso de IA no desenvolvimento está registrado em [`docs/uso-de-ia.md`](docs/uso-de-ia.md) |

**Funcionalidade entregue ao projeto:** a tela "Verificador de CNAE" (`web/`), que consome a API do AgentOS e apresenta o resultado com evidências.
