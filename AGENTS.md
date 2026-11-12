# AGENTS.md

Instruções para agentes de codificação (Claude Code, Codex, Gemini etc.) que trabalham neste repositório.
Leia este arquivo inteiro antes de alterar qualquer coisa.

## Regra de commits (inegociável)

É terminantemente proibido fazer commits com nome de Claude ou Co-authored by Claude. Isso polui a lista de contribuidores e atrapalha o git blame.

- Commits sempre com a identidade git já configurada do autor do repositório.
- Nenhuma linha `Co-authored-by`, nenhuma menção a IA na mensagem, no autor ou no committer.
- Não faça `push` sem pedido explícito.
- Mensagens no formato Conventional Commits, em português (`feat: ...`, `fix: ...`, `docs: ...`, `test: ...`, `chore: ...`).

## O que é este projeto

**Verificador de CNAE**: aplicação web que ajuda pessoas leigas (founders de startups, quem vende SaaS ou infoprodutos) a ter uma noção se o CNAE da empresa é coerente com o modelo de negócio, e serve de ponto de partida de pesquisa para contadores e advogados. **Não é consultoria** — toda a comunicação deve deixar isso claro.

Também é a entrega da atividade da disciplina descrita em `docs/atividade.md`.

## Fontes de verdade

| Arquivo | Papel | Pode editar? |
| --- | --- | --- |
| `docs/atividade.md` | Requisitos fixos da atividade (rubrica, casos T01–T08) | **Nunca** |
| `docs/solucao.md` | Especificação da solução: decisões, contratos, arquitetura | Sim, mantendo coerência com o código |
| `data/regras_cnae.json` | Base de regras do domínio (fonte persistida) | Sim, seguindo as regras de dados abaixo |
| `AGENTS.md` | Este arquivo | Sim |

Se código e `docs/solucao.md` divergirem, pare e alinhe os dois — não deixe a divergência para depois.

## Stack

- Python **3.12** (`.python-version`), gerenciado com **uv** (`pyproject.toml` + `uv.lock`, versões fixadas).
- **Agno 3.1.x** para o agente; **AgentOS** para expô-lo por HTTP (porta 7777).
- Modelo: **Google Gemini** via `agno.models.google.Gemini`, id configurável em `GEMINI_MODEL_ID`.
- App web ("o projeto"): **FastAPI + Jinja2 + HTMX** (porta 8000). Migração futura para React: mantenha o backend do app web como um cliente fino do AgentOS para facilitar a troca.
- Testes: **pytest**. Lint/format: **ruff** (config padrão).

## Comandos

```bash
uv sync                                         # instalar dependências
uv run pytest                                   # testes unitários (ferramentas, regras, verificação)
uv run ruff check . && uv run ruff format .     # lint e formatação
uv run python -m agente.servidor                # AgentOS em http://localhost:7777
uv run uvicorn web.main:app --port 8000         # app web em http://localhost:8000
uv run python scripts/run_casos.py              # executa T01–T07 via HTTP e grava evidencias/
```

Rode `uv run pytest` e `uv run ruff check .` antes de todo commit.

## Estrutura

```text
agente/
  servidor.py          # cria AgentOS, registra o agente, expõe `app`
  agente.py            # definição do Agent (modelo, instruções, limites, tools)
  instrucoes.py        # instruções do agente (texto versionado)
  config.py            # leitura de variáveis de ambiente
  ferramentas/
    ibge.py            # consultar_cnae_ibge
    enquadramento.py   # validar_enquadramento (motor de regras + Fator R + status da afirmação)
    cnae.py            # normalização/validação de código CNAE (compartilhado)
web/
  main.py              # rotas FastAPI
  agentos_client.py    # única camada que chama a API do AgentOS
  verificacao.py       # checagem em código da resposta do agente (pós-validação)
  mensagem.py          # monta a mensagem ao agente a partir do formulário
  render.py            # markdown seguro (só links http/https, sem HTML cru)
  templates/ static/
data/regras_cnae.json  # base de regras
scripts/run_casos.py   # casos de teste via HTTP + gravação de evidências
tests/                 # pytest
evidencias/            # respostas HTTP brutas dos casos (versionadas)
docs/                  # solucao.md, ferramentas.md, dados.md, testes.md, uso-de-ia.md
```

## Convenções de código

- **Idioma:** domínio, ferramentas, campos de dados e documentação em português (`consultar_cnae_ibge`, `folha_12m`). Infraestrutura genérica (config, cliente HTTP, rotas) em inglês.
- **Ferramentas do agente:** funções Python com parâmetros tipados, docstring clara (o Agno a usa como descrição para o modelo) e validação explícita no início.
- **Ferramentas nunca lançam exceção para o agente.** Sempre retornam um `dict` com `status` (`ok`, `nao_encontrado`, `entrada_invalida`, `indisponivel`, `erro_fonte`) e, em caso de sucesso, um bloco `evidencia` com a referência localizável (arquivo + chave + versão, ou URL + timestamp UTC).
- **Toda lógica determinística fica em código, não no prompt:** normalização de CNAE, checagem de enum, compatibilidade, Fator R, anexo resultante e o `status_afirmacao` (confirmada / contradita / sem evidência suficiente). O LLM apenas escolhe ferramentas, mapeia linguagem natural para parâmetros e explica o resultado.
- **Sem cache:** `validar_enquadramento` relê `data/regras_cnae.json` a cada chamada; `consultar_cnae_ibge` sempre consulta a API (necessário para o T07 e para não mascarar falhas no T06).
- **Timeouts explícitos** em toda chamada de rede (`IBGE_TIMEOUT_S`, `AGENTOS_TIMEOUT_S`). Nada de chamadas sem timeout.
- **Credenciais só em variáveis de ambiente** (`.env`, nunca commitado). `.env.example` contém apenas nomes e valores de exemplo. O navegador nunca recebe chave alguma — só o backend do app web fala com o AgentOS.

## Invariantes do domínio

1. **Nunca inventar** CNAE, descrição, anexo, alíquota, artigo de lei ou referência. Se não veio de uma ferramenta, não aparece na resposta.
2. **Ausência de registro ≠ afirmação falsa.** CNAE fora da base ou modelo de negócio não listado para o CNAE resulta em `indeterminado` / `sem_evidencia_suficiente`, nunca em `incompativel` / `contradita`.
3. **Base legal verídica, dados fictícios.** Todo `fundamento_legal` na base de regras cita dispositivo real (LC 123/2006, Resolução CGSN 140/2018, CONCLA/IBGE) e deve ter sido conferido na fonte oficial. Empresas, valores de folha/receita e afirmações usados em testes são fictícios. Nunca use dados pessoais reais.
4. **Zonas cinzentas são declaradas**, não resolvidas por chute (ex.: infoprodutos): marque a regra como `indeterminado` com nota explicativa.
5. **Linguagem simples sempre.** Respostas e telas falam com leigos; termos técnicos só acompanhados de explicação. Nunca usar "parecer", "consultoria" ou tom de recomendação profissional. O aviso "material de referência, não substitui consulta a um contador ou advogado" aparece no topo de todo resultado.
6. **Falha nunca vira sucesso.** IBGE indisponível → `status: indisponivel`, sem dados; a resposta declara a limitação. Base de regras indisponível → nenhum veredito.

## Escopo da v1 (não faça sem pedido)

Fora de escopo agora, documentado como expansão em `docs/solucao.md`: cache/fallback do IBGE e script de sincronização, cadastro de empresas, frontend React, RAG/banco vetorial, múltiplos agentes, deploy, CNAEs fora do recorte de tecnologia/SaaS/infoprodutos.

## Definição de pronto de uma etapa

- Testes passando e ruff limpo.
- `docs/solucao.md` (e `docs/ferramentas.md` / `docs/dados.md`, quando existirem) coerentes com o que foi implementado.
- Commit da etapa feito conforme a regra de commits.
