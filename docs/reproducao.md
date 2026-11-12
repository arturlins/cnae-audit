# Guia de reprodução da entrega

Este guia é para quem nunca viu o projeto. Ele percorre **tudo** em ordem: instalação, testes offline, inspeção das fontes, API do agente, casos T01–T07 pelo script, T06 e T07 à mão, T08 pela tela e comparação com as evidências versionadas. Cada passo traz o comando exato e a saída esperada.

Os comandos aparecem em duas versões:

- **PowerShell**: Windows, PowerShell 7 ou Windows PowerShell 5.1.
- **bash**: Linux, macOS ou Git Bash no Windows.

Quando os dois shells usam o mesmo comando (`uv run …`, `git …`), ele aparece uma vez só. Todos os comandos rodam **na raiz do projeto**, a pasta `cnae-audit/`.

> ⚠️ O Verificador de CNAE é material de referência e não substitui consulta a um contador ou advogado.

A tag da entrega é **`v1.1-atividade`**. Ela é a `v1.0-atividade` mais este guia e correções no `scripts/run_casos.py`:

- o T07 passou a contar no código de saída;
- o script recusa rodar se sobrar um `.bak`;
- a checagem de texto do T04 não reprova mais uma frase que *nega* a incompatibilidade (`docs/testes.md` §3, falha 5).

O agente, as ferramentas, a base e as evidências dos casos são os mesmos.

Validado em 12/11/2026, num clone limpo, no Windows 11 (PowerShell 7.6 e Git Bash), com uv 0.13.7 e `gemini-3.6-flash`. A bateria completa T01–T07 levou 172 s numa conta com faturamento.

**Quanto custa em chamadas ao modelo.** Os passos 0 a 5 não chamam o Gemini. Cada consulta ao agente faz de 3 a 4 requisições ao modelo:

| Passo | Consultas ao agente | Requisições ao Gemini (aprox.) |
| --- | --- | --- |
| 6 (curl) | 1 | 4 |
| 7 (bateria T01–T07) | 10 | 30 a 40 |
| 8 (T06 e T07 à mão) | 4 | 12 a 16 |
| 9 (T08 pela tela) | 1 | 4 |

---

## 0. Pré-requisitos

| Requisito | Para quê |
| --- | --- |
| **git** | Obter o código na tag da entrega |
| **uv** ([docs.astral.sh/uv](https://docs.astral.sh/uv/)) | Instala o Python 3.12 (`.python-version`) e as versões fixadas em `uv.lock` |
| **curl** | Chamar a API do IBGE e a do AgentOS. Vem no Windows 10/11, no macOS e na maioria das distribuições Linux |
| **Chave da API do Google Gemini** ([Google AI Studio](https://aistudio.google.com/apikey)) | O agente usa o Gemini. Ver no passo 3 o que muda entre o plano gratuito e o pago |
| **Internet** | Gemini e API pública do IBGE |
| **Portas 7777 e 8000 livres** | 7777: AgentOS (API do agente). 8000: app web |

### Como conferir cada um

**git, uv e curl.** No PowerShell, use `curl.exe`, não `curl`: no Windows PowerShell 5.1, `curl` é um apelido do `Invoke-WebRequest`.

```powershell
git --version
uv --version
curl.exe --version
```

```bash
git --version
uv --version
curl --version
```

Saída esperada: uma versão em cada linha, por exemplo `git version 2.5x…`, `uv 0.13.7 (…)` e `curl 8.x …`. O guia foi validado com uv 0.13.7; qualquer uv recente lê o `uv.lock`.

Se faltar o uv, instale com um destes comandos:

```powershell
winget install astral-sh.uv
# ou: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Depois de instalar, abra um terminal novo.

**Internet e IBGE:**

```powershell
curl.exe -sS https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/6201501
```

```bash
curl -sS https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/6201501
```

Saída esperada: um JSON que começa com `{"id":"6201501","descricao":"DESENVOLVIMENTO DE PROGRAMAS DE COMPUTADOR SOB ENCOMENDA",…`.

**Portas livres.** A saída esperada é **nenhuma linha**.

```powershell
Get-NetTCPConnection -LocalPort 7777,8000 -State Listen -ErrorAction SilentlyContinue
```

```bash
# Linux / macOS
lsof -nP -iTCP:7777 -iTCP:8000 -sTCP:LISTEN
# Git Bash no Windows
netstat -ano | grep -E ':(7777|8000) .*LISTEN'
```

Se aparecer algum processo, veja [Porta ocupada](#porta-ocupada).

**Chave do Gemini.** Ela é conferida no passo 3, depois da instalação, sem gastar cota.

---

## 1. Obter o código

```bash
git clone <URL-do-repositório> cnae-audit
cd cnae-audit
git checkout v1.1-atividade
```

Saída esperada do `checkout`:

```text
Note: switching to 'v1.1-atividade'.
You are in 'detached HEAD' state. (…)
HEAD is now at <commit> <mensagem do commit da tag>
```

O aviso de *detached HEAD* é normal, porque uma tag não é um ramo. Para confirmar onde você está:

```bash
git describe --tags      # v1.1-atividade
git status --short       # nenhuma linha: árvore limpa
```

Se você recebeu o projeto como pasta, já com o `.git`, pule o `clone` e rode só o `checkout`.

---

## 2. Instalar

```bash
uv sync --frozen
```

O `--frozen` instala **exatamente** o que está no `uv.lock`, sem tentar atualizar nada. Saída esperada (os tempos variam):

```text
Using CPython 3.12.12
Creating virtual environment at: .venv
Installed 64 packages in 644ms
```

Se o Python 3.12 não estiver na máquina, o uv baixa antes, e aparece também uma linha `Downloading cpython-3.12…`. A lista de pacotes (`+ agno==3.1.12`, `+ fastapi==…` etc.) pode aparecer entre as linhas acima.

---

## 3. Configurar

Copie o modelo de configuração:

```powershell
Copy-Item .env.example .env
notepad .env
```

```bash
cp .env.example .env
nano .env        # ou o editor de sua preferência
```

No `.env`, troque `sua-chave-aqui` pela sua chave em `GOOGLE_API_KEY=`. O `.env` está no `.gitignore` e nunca vai para o repositório. Só o AgentOS lê a chave; o navegador nunca a recebe.

**Conferir se a chave foi preenchida.** O comando não mostra a chave:

```powershell
(Select-String -Path .env -Pattern '^GOOGLE_API_KEY=.+' -Quiet) -and -not (Select-String -Path .env -Pattern 'sua-chave-aqui' -Quiet)
# esperado: True
```

```bash
grep -qE '^GOOGLE_API_KEY=.+' .env && ! grep -q 'sua-chave-aqui' .env && echo preenchida
# esperado: preenchida
```

**Conferir se a chave é aceita e se o modelo existe.** O comando consulta os metadados do modelo, sem gerar texto e sem gastar cota de geração:

```bash
uv run python -X utf8 -c "from agente import config; from google import genai; c = genai.Client(); print('chave aceita; modelo encontrado:', c.models.get(model=config.gemini_model_id()).name)"
```

Saída esperada:

```text
chave aceita; modelo encontrado: models/gemini-3.6-flash
```

Um erro `400 … API_KEY_INVALID` indica chave errada. Um `404` indica que o `GEMINI_MODEL_ID` não existe.

### Variáveis que importam para a reprodução

A lista completa está no [README](../README.md#instalação-e-configuração). Para reproduzir a entrega, estas três são as que importam:

| Variável | Padrão | O que faz |
| --- | --- | --- |
| `GEMINI_MODEL_ID` | `gemini-3.6-flash` | Modelo do agente. **As evidências foram geradas com `gemini-3.6-flash`**, e é bom manter esse modelo. Outro id precisa ter suporte a chamada de ferramentas. Com outro modelo o veredito continua o mesmo, porque é calculado em código, mas o texto muda mais |
| `AGENTOS_TIMEOUT_S` | `120` | Quanto o app web e o `run_casos.py` esperam por uma resposta do AgentOS. Cada requisição ao Gemini tem 30 s (`GEMINI_TIMEOUT_S`) e até 2 novas tentativas em 429/5xx. Com o modelo sobrecarregado, uma consulta de 4 requisições pode passar de 120 s; nesse caso, suba para `300` |
| `CASOS_PAUSA_S` | `5` | Pausa mínima, em segundos, entre o início de um caso e o do seguinte no `run_casos.py`. Não está no `.env.example`, mas pode ser posta no `.env` ou passada na linha de comando (passo 7) |

### Plano gratuito × plano pago do Gemini

| | Plano gratuito | Plano pago (faturamento ativo) |
| --- | --- | --- |
| Limite observado | **5 requisições/min** e **20 requisições/dia** (a cota parece compartilhada entre os modelos Flash) | Sem limite prático para este guia |
| `CASOS_PAUSA_S` | `60` | `5` (o padrão) |
| Bateria T01–T07 (passo 7) | **Não cabe numa cota de um dia** (30 a 40 requisições). Rode em partes, em dias diferentes. Exemplo: `T01 T02 T03 T04` num dia, `T05 T06 T07` no outro | Cabe numa execução de ~3 min |
| Sintoma de cota estourada | Run com `status: ERROR` e `429 RESOURCE_EXHAUSTED` | — |

A execução registrada em `docs/testes.md` usou uma conta com faturamento ativo.

---

## 4. Verificação offline

Os testes unitários não usam rede nem chave: o IBGE e o AgentOS são simulados.

```bash
uv run pytest
```

Saída esperada (última linha; o tempo varia):

```text
============================= 171 passed in 1.68s =============================
```

```bash
uv run ruff check .
uv run ruff format --check .
```

Saída esperada (o número de arquivos pode variar):

```text
All checks passed!
34 files already formatted
```

Nenhuma linha `Would reformat` deve aparecer.

---

## 5. Inspecionar as fontes (o esperado vem daqui, não do modelo)

O resultado esperado de cada caso foi definido **antes** da execução, lendo a base de regras e a API do IBGE (`docs/solucao.md` §11). Este passo refaz essa inspeção, sem o agente.

### 5.1. Base de regras `data/regras_cnae.json`

Abra o arquivo num editor e procure as chaves abaixo, ou use os comandos:

```powershell
Select-String -Path data/regras_cnae.json -Pattern '"R-6201-SAAS"','"R-6203-LIC-NAO-CUSTOM"' -Context 0,2
Select-String -Path data/regras_cnae.json -Pattern '4711'      # nenhuma linha: o CNAE não está na base
```

```bash
grep -n -A2 -E '"R-6201-SAAS"|"R-6203-LIC-NAO-CUSTOM"' data/regras_cnae.json
grep -n '4711' data/regras_cnae.json || echo "4711-3/02 não está na base"
```

Saída esperada (bash):

```text
137:          "id": "R-6201-SAAS",
138-          "modelo_negocio": "saas_padronizado",
139-          "resultado": "incompativel",
--
211:          "id": "R-6203-LIC-NAO-CUSTOM",
212-          "modelo_negocio": "licenciamento_nao_customizavel",
213-          "resultado": "compativel",
4711-3/02 não está na base
```

Uma leitura estruturada, igual nos dois shells:

```bash
uv run python -X utf8 -c "import json; b=json.load(open('data/regras_cnae.json', encoding='utf-8')); print('versao', b['versao'], b['data_referencia']); [print(c, r['id'], r['modelo_negocio'], r['resultado']) for c, v in b['cnaes'].items() for r in v['regras'] if r['id'] in ('R-6201-SAAS', 'R-6203-LIC-NAO-CUSTOM', 'R-6311-SAAS', 'R-6319-SAAS')]; t=b['cnaes']['6203-1/00']['tributacao']; print('6203-1/00 Fator R:', t['sujeito_fator_r'], 'alto', t['anexo_fator_r_alto'], 'baixo', t['anexo_fator_r_baixo']); print('4711-3/02 na base?', '4711-3/02' in b['cnaes'])"
```

Saída esperada:

```text
versao 1.0.0 2026-11-11
6201-5/01 R-6201-SAAS saas_padronizado incompativel
6203-1/00 R-6203-LIC-NAO-CUSTOM licenciamento_nao_customizavel compativel
6311-9/00 R-6311-SAAS saas_padronizado compativel
6319-4/00 R-6319-SAAS saas_padronizado compativel
6203-1/00 Fator R: True alto III baixo V
4711-3/02 na base? False
```

O limiar do Fator R (28%) está em código, em `agente/ferramentas/enquadramento.py` (`LIMIAR_FATOR_R_PERCENTUAL = 28`, LC 123/2006, art. 18, §§ 5º-J e 5º-M).

### 5.2. API do IBGE

```powershell
curl.exe -sS https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/6201501
curl.exe -sS https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/6203100
curl.exe -sS https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/4711302
curl.exe -sS -w "  HTTP %{http_code}" https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/9999999
```

```bash
for c in 6201501 6203100 4711302; do curl -sS "https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/$c" | head -c 160; echo; done
curl -sS -w '  HTTP %{http_code}\n' https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/9999999
```

Saída esperada:

```text
{"id":"6201501","descricao":"DESENVOLVIMENTO DE PROGRAMAS DE COMPUTADOR SOB ENCOMENDA",…
{"id":"6203100","descricao":"DESENVOLVIMENTO E LICENCIAMENTO DE PROGRAMAS DE COMPUTADOR NÃO CUSTOMIZÁVEIS",…
{"id":"4711302","descricao":"COMÉRCIO VAREJISTA DE MERCADORIAS EM GERAL, COM PREDOMINÂNCIA DE PRODUTOS ALIMENTÍCIOS - SUPERMERCADOS",…
[]  HTTP 200
```

Um código inexistente volta como `[]` com HTTP 200, e não como 404. A ferramenta `consultar_cnae_ibge` traduz isso para `status: nao_encontrado`.

### 5.3. Do que se inspecionou ao esperado de cada caso

| Caso | O que a inspeção mostra | Esperado |
| --- | --- | --- |
| T01 | IBGE `6203100` → "…LICENCIAMENTO DE PROGRAMAS DE COMPUTADOR NÃO CUSTOMIZÁVEIS" | A afirmação "o 6203-1/00 é de licenciamento não customizável" **confere**, com URL e data/hora |
| T02 | `R-6203-LIC-NAO-CUSTOM` = `compativel`. 6203-1/00 tem `anexo_fator_r_alto: III`. Folha 30.000 / receita 100.000 = 30% ≥ 28% | `compativel`, Fator R → **Anexo III**; "me disseram Anexo III" → **confirmada** |
| T03 | `R-6201-SAAS` = `incompativel`. `R-6311-SAAS` e `R-6319-SAAS` = `compativel` | "o 6201-5/01 serve para SaaS" → **contradita**; sugestões 6311-9/00 e 6319-4/00 |
| T04 | IBGE `4711302` existe (supermercados), mas `4711-3/02` **não está na base** | `nao_encontrado` → **sem_evidencia_suficiente**, nunca "incompatível" (ausência de registro ≠ afirmação falsa) |
| T05 | Não há CNAE, ou o código tem 5 dígitos (`62015`), que não é um formato de subclasse | Pedido de esclarecimento ou `entrada_invalida`; nenhum veredito |
| T06 | A conclusão do T03 vem da base (`R-6201-SAAS`), não do IBGE | 6a, IBGE fora: ressalva + `contradita` só pela base. 6b, base fora: **nenhum veredito** |
| T07 | Trocar `R-6201-SAAS.resultado` para `compativel` | Antes: **contradita**. Depois: **confirmada** |

---

## 6. Subir o AgentOS e chamar a API do agente

### 6.1. Terminal 1: AgentOS

```bash
uv run python -m agente.servidor
```

Saída esperada (fica rodando; o PID varia):

```text
╔═══════════════ AgentOS ════════════════╗
║  OS running on: http://localhost:7777  ║
╚════════════════════════════════════════╝
INFO:     Started server process [51380]
INFO:     Waiting for application startup.
INFO    Database ready: SqliteDb id=…
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:7777 (Press CTRL+C to quit)
```

O `SqliteDb` é `tmp/agentos.db` e guarda **só sessões**. Não é fonte de dados do domínio.

### 6.2. Terminal 2: conferir `/health` e `/docs`

```powershell
curl.exe -sS http://localhost:7777/health
curl.exe -sS -o NUL -w "docs HTTP %{http_code}" http://localhost:7777/docs
curl.exe -sS http://localhost:7777/agents
```

```bash
curl -sS http://localhost:7777/health; echo
curl -sS -o /dev/null -w 'docs HTTP %{http_code}\n' http://localhost:7777/docs
curl -sS http://localhost:7777/agents; echo
```

Saída esperada:

```text
{"status":"ok","instantiated_at":"2026-11-12T03:49:37.698119Z"}
docs HTTP 200
[{"id":"verificador-cnae","name":"Verificador de CNAE",…
```

Abra `http://localhost:7777/docs` no navegador para ver o Swagger. O endpoint usado em todo o guia é `POST /agents/{agent_id}/runs`.

### 6.3. Terminal 2: a chamada HTTP do README

É a mesma chamada do README, com a resposta salva em `tmp/resposta.json` (`tmp/` está no `.gitignore`). Leva de 15 a 30 s.

```powershell
curl.exe --fail-with-body -sS --create-dirs -o tmp/resposta.json -w "HTTP %{http_code}" http://localhost:7777/agents/verificador-cnae/runs --data-urlencode "message=Vendo assinatura de um sistema SaaS padronizado e meu contador disse que posso usar o CNAE 6201-5/01. Isso confere?" --data-urlencode "stream=false"
```

```bash
curl --fail-with-body -sS --create-dirs -o tmp/resposta.json -w 'HTTP %{http_code}\n' \
  http://localhost:7777/agents/verificador-cnae/runs \
  --data-urlencode 'message=Vendo assinatura de um sistema SaaS padronizado e meu contador disse que posso usar o CNAE 6201-5/01. Isso confere?' \
  --data-urlencode 'stream=false'
```

Saída esperada: `HTTP 200`.

### 6.4. Como ler a resposta

A resposta é o JSON de uma execução do agente. Os campos que importam:

| Campo | Conteúdo |
| --- | --- |
| `status` | `COMPLETED`. `ERROR` indica falha do modelo (429/403/5xx); veja [Solução de problemas](#11-solução-de-problemas) |
| `model` | `gemini-3.6-flash` |
| `content` | Texto final do agente, em markdown: aviso no topo, "Entendi seu negócio como: …", `## Resultado`, `## Em linguagem simples`, `## Por que chegamos nisso`, `## Onde conferir` |
| `tools[]` | Uma entrada por chamada de ferramenta, na ordem em que aconteceu |
| `tools[].tool_name` | `consultar_cnae_ibge` ou `validar_enquadramento` |
| `tools[].tool_args` | Os argumentos que o modelo escolheu, por exemplo `{"codigo_cnae": "6201-5/01"}` |
| `tools[].result` | O retorno da ferramenta, como **string JSON**: `status`, dados e o bloco `evidencia` (URL + `consultado_em` no IBGE; arquivo + chave + versão na base) |

Para ler a resposta sem `jq`, igual nos dois shells:

```bash
uv run python -X utf8 -c "import json; d=json.load(open('tmp/resposta.json', encoding='utf-8')); print(d['status'], d['model']); print(d['content']); [print('-', t['tool_name'], t['tool_args'], '->', {k: v for k, v in json.loads(t['result']).items() if k in ('status', 'descricao', 'compatibilidade', 'regra_aplicada', 'status_afirmacao')}) for t in d['tools']]"
```

Saída esperada (o texto de `content` varia; o resto não):

```text
COMPLETED gemini-3.6-flash
> ⚠️ Material de referência, não substitui consulta a um contador ou advogado.

Entendi seu negócio como: Vendo assinatura de um sistema na internet, igual para todos os clientes (SaaS).

## Resultado
Compatibilidade: incompativel
Status da afirmação: contradita
(…)
- consultar_cnae_ibge {'codigo_cnae': '6201-5/01'} -> {'status': 'ok', 'descricao': 'DESENVOLVIMENTO DE PROGRAMAS DE COMPUTADOR SOB ENCOMENDA'}
- validar_enquadramento {'afirmacao_compativel': True, 'modelo_negocio': 'saas_padronizado', 'codigo_cnae': '6201-5/01'} -> {'status': 'ok', 'compatibilidade': 'incompativel', 'regra_aplicada': 'R-6201-SAAS', 'status_afirmacao': 'contradita'}
- consultar_cnae_ibge {'codigo_cnae': '6311-9/00'} -> {'status': 'ok', 'descricao': 'TRATAMENTO DE DADOS, PROVEDORES DE SERVIÇOS DE APLICAÇÃO E SERVIÇOS DE HOSPEDAGEM NA INTERNET'}
- consultar_cnae_ibge {'codigo_cnae': '6319-4/00'} -> {'status': 'ok', 'descricao': 'PORTAIS, PROVEDORES DE CONTEÚDO E OUTROS SERVIÇOS DE INFORMAÇÃO NA INTERNET'}
```

É isso que liga a entrada (`message`) à chamada de ferramenta (`tool_args`), ao retorno (`result`) e à resposta final (`content`). O `contradita` em `content` é cópia do `status_afirmacao` que o código devolveu, não uma opinião do modelo. A íntegra de uma resposta como esta está em [`evidencias/curl_exemplo.json`](../evidencias/curl_exemplo.json).

**Antes do passo 7, pare o AgentOS:** `Ctrl+C` no terminal 1. O script sobe o próprio AgentOS e precisa da porta 7777 livre.

---

## 7. Casos T01–T07 automáticos

### 7.1. Guardar uma cópia das evidências versionadas

O script **sobrescreve** `evidencias/*.json` e `evidencias/logs/*`. Para comparar depois (passo 10), guarde uma cópia antes. Se `tmp/evidencias_versionadas` já existir de uma execução anterior, apague-a antes; senão a cópia vai parar numa subpasta.

```powershell
New-Item -ItemType Directory -Force tmp | Out-Null; Copy-Item -Recurse evidencias tmp/evidencias_versionadas
```

```bash
mkdir -p tmp && cp -r evidencias tmp/evidencias_versionadas
```

### 7.2. Rodar a bateria

Confira que a porta 7777 está livre (passo 0) e rode:

```powershell
uv run python scripts/run_casos.py
# plano gratuito:
$env:CASOS_PAUSA_S = "60"; uv run python scripts/run_casos.py; Remove-Item Env:CASOS_PAUSA_S
```

```bash
uv run python scripts/run_casos.py
# plano gratuito:
CASOS_PAUSA_S=60 uv run python scripts/run_casos.py
# no Git Bash, se os acentos saírem trocados, prefixe com PYTHONUTF8=1
```

Saída esperada. No Windows, os caminhos aparecem com `\`. Com `CASOS_PAUSA_S=60`, aparecem também linhas `(pausa de N s pela cota do modelo)`.

```text
[PASSOU] T01 Primeira ferramenta (IBGE) e informação conhecida confirmada -> evidencias/T01.json
[PASSOU] T02 Segunda ferramenta (base de regras + Fator R) -> evidencias/T02.json
[PASSOU] T03 Afirmação do usuário contradita pela base -> evidencias/T03.json
[PASSOU] T04 CNAE real fora da base -> evidencias/T04.json
[PASSOU] T05a Pergunta ambígua (sem CNAE) -> evidencias/T05a.json
[PASSOU] T05b CNAE malformado -> evidencias/T05b.json
[PASSOU] T07-antes Antes da alteração da base -> evidencias/T07-antes.json
[PASSOU] T07-depois Depois da alteração da base (nova sessão) -> evidencias/T07-depois.json
         base restaurada: R-6201-SAAS.resultado = incompativel
[PASSOU] T06a IBGE indisponível -> evidencias/T06a.json
[PASSOU] T06b Base de regras ausente -> evidencias/T06b.json

Modelo: gemini-3.6-flash  |  evidências em evidencias/
```

Quando um caso falha, ele aparece como `[FALHOU]`, com uma linha `x <checagem>` para cada checagem reprovada. O script continua com os casos seguintes.

**Código de saída:** `0` se todos os casos executados passaram; `1` se algum falhou; `2` se faltou `GOOGLE_API_KEY` ou se sobrou `data/regras_cnae.json.bak` (ver [Solução de problemas](#sobrou-dataregras_cnaejsonbak)). Para ver o código: `$LASTEXITCODE` no PowerShell, `echo $?` no bash.

### 7.3. O que o script faz em cada caso

Todos os casos passam pela **API HTTP** (`POST /agents/verificador-cnae/runs`, `stream=false`), cada um com um `session_id` novo. Os casos T02, T04, T06 e T07 enviam **a mesma mensagem que o app web monta** a partir do formulário (`web/mensagem.py`).

| Caso | Mensagem | O que o script faz |
| --- | --- | --- |
| T01 | Texto livre sobre o 6203-1/00 | Envia e confere a descrição do IBGE, a URL/data e a confirmação |
| T02 | Formulário: 6203-1/00, licenciamento não customizável, folha 30.000, receita 100.000, "Anexo III" | Confere os argumentos repassados, `R-6203-LIC-NAO-CUSTOM`, anexo `III` e `confirmada` |
| T03 | Texto livre: SaaS a R$ 99/mês, "posso usar o 6201-5/01?" | Confere `R-6201-SAAS`, `incompativel`, `contradita` e as sugestões consultadas no IBGE |
| T04 | Formulário: 4711-3/02, revenda de hardware, "disseram que sim" | Confere IBGE `ok`, base `nao_encontrado` e `sem_evidencia_suficiente` |
| T05a / T05b | "Posso usar o CNAE de desenvolvimento?" / código `62015` | Confere o pedido de esclarecimento (ou `entrada_invalida`) e que não houve veredito |
| T06a | Formulário do T03 | **Para o AgentOS e sobe outro** com `IBGE_BASE_URL=http://ibge-indisponivel.invalid/api/v2/cnae`. Confere IBGE `indisponivel`, a ressalva no texto e `contradita` só pela base. Log em `evidencias/logs/agentos_T06a.log` |
| T06b | Formulário do T03 | Sobe o AgentOS com `REGRAS_PATH=data/regras_cnae_AUSENTE.json`. Confere `erro_fonte` e nenhum veredito. Log em `evidencias/logs/agentos_T06b.log` |
| T07 | Formulário do T03, duas vezes | 1) **Backup** de `data/regras_cnae.json` em `data/regras_cnae.json.bak`. 2) Executa e espera `contradita` (`T07-antes`). 3) **Edita** `R-6201-SAAS`: `resultado` passa a `compativel`. 4) Executa de novo, em **nova sessão** e sem reiniciar o AgentOS, porque a base é relida a cada chamada, e espera `confirmada` (`T07-depois`). 5) **Restaura** o backup, mesmo se der erro ou se você apertar `Ctrl+C` |

Em todos os casos, o script aplica também a **mesma pós-validação do app web** (`web/verificacao.py`): todo CNAE citado precisa ter vindo de uma ferramenta, o veredito precisa bater com o da ferramenta etc.

### 7.4. Onde ficam as evidências e como conferir cada JSON

| Arquivo | Conteúdo |
| --- | --- |
| `evidencias/<caso>.json` | Um por caso (`T01.json` … `T06b.json`, `T07-antes.json`, `T07-depois.json`) |
| `evidencias/logs/agentos_padrao.log` | Log do AgentOS dos casos T01–T05 e T07 |
| `evidencias/logs/agentos_T06a.log`, `agentos_T06b.log` | Log do AgentOS reiniciado com a fonte indisponível |

Campos de cada `evidencias/<caso>.json`:

| Campo | O que conferir |
| --- | --- |
| `situacao` | `passou` |
| `checagens[]` | Cada checagem automática, com `descricao` e `ok`. Todas `true` |
| `ferramentas_executadas[]` | `nome`, `argumentos` e `status` de cada chamada de ferramenta |
| `pos_validacao` | `verificada: true`, `falhas: []` e o `status_afirmacao` que o selo da tela usaria |
| `modelo`, `base_regras` | `gemini-3.6-flash`; `versao` `1.0.0` e `data_referencia` `2026-11-11` |
| `requisicao` | Método, URL, formulário enviado (`message`, `stream`, `session_id`) e `enviado_em` (UTC) |
| `resposta` | Resposta HTTP **bruta**: `status_http` e `corpo` (o mesmo JSON do passo 6.4, com `content` e `tools`) |
| `dado_alterado` | Só no T07: a chave alterada e o valor antes/depois |

Resumo de um caso, igual nos dois shells (troque `T03` pelo caso desejado):

```bash
uv run python -X utf8 -c "import json; d=json.load(open('evidencias/T03.json', encoding='utf-8')); print(d['caso'], d['situacao'], d['modelo'], d['base_regras']); [print('  ok ' if c['ok'] else '  FALHOU ', c['descricao']) for c in d['checagens']]; print('pos_validacao:', d['pos_validacao']); [print('  ', f['nome'], f['argumentos'], '->', f['status']) for f in d['ferramentas_executadas']]"
```

Saída esperada para o T03:

```text
T03 passou gemini-3.6-flash {'versao': '1.0.0', 'data_referencia': '2026-11-11'}
  ok  HTTP 200
  ok  validar_enquadramento com saas_padronizado e afirmação 'serve'
  ok  regra R-6201-SAAS -> incompativel
  ok  status_afirmacao = contradita
  ok  sugere 6311-9/00 e 6319-4/00
  ok  algum CNAE sugerido foi consultado no IBGE
  ok  pós-validação do app web aprovou
pos_validacao: {'verificada': True, 'falhas': [], 'status_afirmacao': 'contradita'}
   consultar_cnae_ibge {'codigo_cnae': '6201-5/01'} -> ok
   validar_enquadramento {'codigo_cnae': '6201-5/01', 'afirmacao_compativel': True, 'modelo_negocio': 'saas_padronizado'} -> ok
   consultar_cnae_ibge {'codigo_cnae': '6311-9/00'} -> ok
   consultar_cnae_ibge {'codigo_cnae': '6319-4/00'} -> ok
```

### 7.5. Rodar um caso só, ou alguns

Os argumentos são prefixos do id do caso:

```bash
uv run python scripts/run_casos.py T03          # só o T03 (~25 s)
uv run python scripts/run_casos.py T06          # T06a e T06b
uv run python scripts/run_casos.py T07          # T07-antes e T07-depois
uv run python scripts/run_casos.py T01 T02 T04  # vários
```

Saída esperada para `T03`:

```text
[PASSOU] T03 Afirmação do usuário contradita pela base -> evidencias/T03.json

Modelo: gemini-3.6-flash  |  evidências em evidencias/
```

---

## 8. T06 e T07 à mão (opcional)

O script automatiza estes passos. Aqui eles são refeitos sem o script, para ver cada peça. Use dois terminais. Nos dois casos, a mensagem é a do curl do passo 6.3, que tem o mesmo esperado do T03.

### 8.1. T06a: IBGE indisponível

**Terminal 1.** Suba o AgentOS apontando o IBGE para um host que não existe. Variáveis de ambiente reais têm precedência sobre o `.env`.

```powershell
$env:IBGE_BASE_URL = "http://ibge-indisponivel.invalid/api/v2/cnae"; uv run python -m agente.servidor
```

```bash
IBGE_BASE_URL=http://ibge-indisponivel.invalid/api/v2/cnae uv run python -m agente.servidor
```

**Terminal 2.** Repita o curl do passo 6.3 (ele sobrescreve `tmp/resposta.json`) e leia a resposta com o comando do passo 6.4. Esperado:

- `consultar_cnae_ibge` → `{'status': 'indisponivel'}`, uma ou mais vezes;
- `validar_enquadramento` → `ok`, `incompativel`, `R-6201-SAAS`, `contradita`;
- `content` com uma ressalva explícita de que o IBGE esteve indisponível e de que a conclusão se apoia só na base.

**Terminal 1.** `Ctrl+C` e, no PowerShell, limpe a variável: `Remove-Item Env:IBGE_BASE_URL`. No bash, o prefixo valeu só para aquele comando.

### 8.2. T06b: base de regras ausente

**Terminal 1:**

```powershell
$env:REGRAS_PATH = "data/regras_cnae_AUSENTE.json"; uv run python -m agente.servidor
```

```bash
REGRAS_PATH=data/regras_cnae_AUSENTE.json uv run python -m agente.servidor
```

**Terminal 2.** Repita o curl do passo 6.3 e leia a resposta. Esperado:

- `validar_enquadramento` → `{'status': 'erro_fonte'}`;
- `content` **sem veredito**: não aparece nem `contradita` nem `confirmada`, e o texto declara o erro da base.

**Terminal 1.** `Ctrl+C` e, no PowerShell, `Remove-Item Env:REGRAS_PATH`.

### 8.3. T07: alteração de dado na fonte

**Terminal 1.** Suba o AgentOS normal: `uv run python -m agente.servidor`.

**Terminal 2.**

1. **Antes.** Repita o curl do passo 6.3 acrescentando `--data-urlencode "session_id=t07-antes-manual"` e leia a resposta. Esperado: `validar_enquadramento` → `incompativel`, `contradita`.
2. **Edite a base.** Abra `data/regras_cnae.json` e, dentro do bloco `"id": "R-6201-SAAS"` (linha 139), troque `"resultado": "incompativel"` por `"resultado": "compativel"`. Salve. **Não reinicie o AgentOS**: a ferramenta relê o arquivo a cada chamada. Se preferir um comando, este faz a mesma troca (ele reescreve o JSON inteiro, com outra indentação; a restauração do item 4 desfaz tudo):

   ```bash
   uv run python -X utf8 -c "import json; p='data/regras_cnae.json'; b=json.load(open(p, encoding='utf-8')); [r.update(resultado='compativel') for r in b['cnaes']['6201-5/01']['regras'] if r['id'] == 'R-6201-SAAS']; open(p, 'w', encoding='utf-8').write(json.dumps(b, ensure_ascii=False, indent=2))"
   ```

3. **Depois.** Repita o curl com `--data-urlencode "session_id=t07-depois-manual"`, uma **sessão nova**. Esperado: `validar_enquadramento` → `compativel`, `R-6201-SAAS`, `confirmada`.
4. **Restaure a base e confira:**

   ```bash
   git checkout -- data/regras_cnae.json
   git status --short data/          # nenhuma linha
   ```

   Rode de novo o comando de leitura estruturada do passo 5.1. A linha da regra deve voltar a `6201-5/01 R-6201-SAAS saas_padronizado incompativel`.

**Terminal 1.** `Ctrl+C`.

---

## 9. T08: a jornada pela tela

### 9.1. Subir os dois processos

**Terminal 1** (AgentOS):

```bash
uv run python -m agente.servidor
```

**Terminal 2** (app web):

```bash
uv run uvicorn web.main:app --port 8000
```

Saída esperada no terminal 2:

```text
INFO:     Started server process […]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 9.2. Clique a clique

1. Abra `http://localhost:8000`. Aparece a página **Verificador de CNAE**, com o aviso de material de referência no topo e o formulário.
2. Em **CNAE registrado ou sugerido**, digite `6201-5/01`.
3. Em **O que sua empresa faz?**, escolha *"Vendo assinatura de um sistema na internet, igual para todos os clientes (SaaS)"*.
4. Em **Esse CNAE serve para o meu negócio?**, escolha *"Disseram que sim"*.
5. Deixe os demais campos (anexo, folha, receita) em branco e clique em **Verificar**.
6. O botão fica desabilitado e aparece **"Verificando… isso pode levar alguns segundos."** por cerca de 20 s.
7. O resultado mostra, de cima para baixo:
   - o aviso **"⚠️ Material de referência, não substitui consulta a um contador ou advogado."**;
   - o selo de alerta **"O que te disseram não confere com a base"**. Ele vem do `status_afirmacao: contradita` da ferramenta, não do texto do modelo;
   - "Entendi seu negócio como: …" e as seções **Resultado**, **Em linguagem simples** (com as sugestões `6311-9/00` e `6319-4/00` e as descrições oficiais), **Por que chegamos nisso** e **Onde conferir**;
   - em **Onde conferir**: a regra `R-6201-SAAS` de `data/regras_cnae.json` (versão 1.0.0), as URLs `https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/…` com data e hora UTC, e os artigos da LC 123/2006;
   - **Ferramentas executadas (4)**, um bloco recolhível. Ao abrir, aparecem `consultar_cnae_ibge`, `validar_enquadramento`, `consultar_cnae_ibge` e `consultar_cnae_ibge`, cada uma com status, argumentos e retorno brutos, e o `run_id` no fim.

Compare com as capturas em [`evidencias/T08/`](../evidencias/T08/): `01_formulario_preenchido.png`, `02_verificando.png`, `03_resultado.png` e `04_ferramentas_executadas.png`.

**Linha esperada no log do backend (terminal 2).** O `run_id` e o horário variam; os horários estão no fuso local.

```text
… INFO web: Verificação solicitada: cnae='6201-5/01' modelo='saas_padronizado'
… INFO web.agentos: POST http://localhost:7777/agents/verificador-cnae/runs session_id=…
… INFO web.agentos: AgentOS HTTP 200 in 19.2s
… INFO web: Resposta do agente: run_id=… ferramentas=['consultar_cnae_ibge', 'validar_enquadramento', 'consultar_cnae_ibge', 'consultar_cnae_ibge'] verificada=True status_afirmacao=contradita falhas=[]
```

O `verificada=True` indica que a resposta passou na pós-validação em código. Se não passasse, a tela mostraria o selo **"Resposta não verificada"** e só os dados das ferramentas.

### 9.3. Teste de erro: AgentOS fora do ar

1. No **terminal 1**, pare o AgentOS com `Ctrl+C`. Deixe o app web rodando.
2. Na tela, com o mesmo formulário preenchido, clique em **Verificar**.
3. Esperado, em poucos segundos:
   - o título **"Não foi possível verificar agora"**;
   - a mensagem "O serviço do agente (AgentOS) está fora do ar ou inacessível.";
   - o texto "Nenhum resultado foi gerado. Tente novamente em instantes.";
   - o botão **"Tentar novamente"**. Nenhum selo nem resultado parcial aparece.
4. No log do backend:

   ```text
   … WARNING web.agentos: AgentOS unreachable: ConnectError
   … WARNING web: Falha ao chamar o AgentOS: indisponivel (O serviço do agente (AgentOS) está fora do ar ou inacessível.)
   ```

5. Suba o AgentOS de novo no terminal 1 e clique em **Tentar novamente**. O resultado normal aparece.

Um erro do modelo (429/403/5xx) cai no mesmo tratamento, com a mensagem "A execução do agente terminou com erro." (captura `evidencias/T08/extra_erro_tratado.png`).

---

## 10. Comparar com as evidências versionadas

O modelo não é determinístico, mesmo com temperatura 0. Por isso a comparação separa o que **pode** variar do que **não pode**.

| Pode variar | Não pode variar |
| --- | --- |
| O texto de `content`: redação, ordem das frases, tamanho | `situacao: passou` e todas as `checagens` com `ok: true` |
| `run_id`, `session_id`, `created_at`, métricas e tokens, tempos de resposta | `status_afirmacao` (`confirmada` / `contradita` / `sem_evidencia_suficiente`) e o selo que ele gera |
| `consultado_em` (timestamp UTC do IBGE) e `enviado_em` | `compatibilidade`, `regra_aplicada` (ex.: `R-6201-SAAS`) e `cnaes_sugeridos` |
| Quantas vezes o IBGE é consultado no T06a (o agente pode tentar de novo) | `tributacao.anexo_resultante` (`III` no T02) |
| No T05b: o agente chama a ferramenta (que devolve `entrada_invalida`) **ou** pede esclarecimento direto, sem ferramenta (`docs/testes.md` §4) | As ferramentas exigidas pelo caso e o `status` de cada uma: `consultar_cnae_ibge` → `ok` (T01/T03/T04) ou `indisponivel` (T06a); `validar_enquadramento` → `ok`, `nao_encontrado` (T04) ou `erro_fonte` (T06b) |
| | `pos_validacao.verificada: true`, `modelo` e `base_regras` (`1.0.0` / `2026-11-11`) |

Comparação automática dos campos que não podem variar, entre `evidencias/` (execução nova) e `tmp/evidencias_versionadas/` (cópia do passo 7.1). Igual nos dois shells:

```bash
uv run python -X utf8 -c "import json, glob, os; r=lambda p: json.load(open(p, encoding='utf-8')); v=lambda d: [json.loads(t['result']) for t in (d['resposta']['corpo'].get('tools') or []) if t['tool_name'] == 'validar_enquadramento' and t.get('result')]; k=lambda d: (d['situacao'], d['pos_validacao']['verificada'], d['pos_validacao']['status_afirmacao'], [(x.get('status'), x.get('compatibilidade'), x.get('regra_aplicada'), (x.get('tributacao') or {}).get('anexo_resultante')) for x in v(d)[-1:]]); [print(os.path.basename(p), 'IGUAL' if k(r(p)) == k(r(os.path.join('tmp', 'evidencias_versionadas', os.path.basename(p)))) else 'DIFERENTE', k(r(p))) for p in sorted(glob.glob(os.path.join('evidencias', 'T*.json')))]"
```

Saída esperada (`situacao`, `verificada`, `status_afirmacao`, último `validar_enquadramento`: `status`, `compatibilidade`, regra e anexo):

```text
T01.json IGUAL ('passou', True, None, [])
T02.json IGUAL ('passou', True, 'confirmada', [('ok', 'compativel', 'R-6203-LIC-NAO-CUSTOM', 'III')])
T03.json IGUAL ('passou', True, 'contradita', [('ok', 'incompativel', 'R-6201-SAAS', None)])
T04.json IGUAL ('passou', True, 'sem_evidencia_suficiente', [('nao_encontrado', 'indeterminado', None, None)])
T05a.json IGUAL ('passou', True, None, [])
T05b.json IGUAL ('passou', True, None, [])
T06a.json IGUAL ('passou', True, 'contradita', [('ok', 'incompativel', 'R-6201-SAAS', None)])
T06b.json IGUAL ('passou', True, None, [('erro_fonte', None, None, None)])
T07-antes.json IGUAL ('passou', True, 'contradita', [('ok', 'incompativel', 'R-6201-SAAS', None)])
T07-depois.json IGUAL ('passou', True, 'confirmada', [('ok', 'compativel', 'R-6201-SAAS', None)])
```

Os casos que você não executou também aparecem como `IGUAL`, porque o arquivo continua sendo o versionado. Para ver o que mudou no texto, use `git diff --stat evidencias/` ou `git diff evidencias/T03.json`. Para voltar às evidências versionadas, use `git checkout -- evidencias/`.

---

## 11. Solução de problemas

### 429 `RESOURCE_EXHAUSTED`

**Sintoma.** A resposta vem com `status: ERROR` e o erro do Gemini em `content`. No log do AgentOS aparece `429`. No script, o caso aparece como `[FALHOU]`. Na tela, aparece "Não foi possível verificar agora".

**Causa.** Cota do plano gratuito: 5 requisições/min e 20/dia. O agente já tenta de novo até 2 vezes, com espera de 8 s e 16 s.

**O que fazer.**
- Por minuto: use `CASOS_PAUSA_S=60` e rode de novo só os casos que falharam (`run_casos.py T03 T06`).
- Por dia: espere a cota renovar (meia-noite no horário do Pacífico) ou ative o faturamento.

### 503 `UNAVAILABLE` / 504 `DEADLINE_EXCEEDED`

**Causa.** Sobrecarga do modelo no Google ("high demand"). As novas tentativas automáticas cobrem picos curtos.

**O que fazer.**
- Espere alguns minutos e rode de novo.
- Se o script relatar timeout, suba `AGENTOS_TIMEOUT_S` (ex.: `300`).
- Em último caso, troque `GEMINI_MODEL_ID` por outro Flash com chamada de ferramentas. Os vereditos não mudam, mas as evidências versionadas foram geradas com `gemini-3.6-flash`. Em 12/11/2026, `gemini-3.7-flash` e `gemini-3.8-flash` respondiam 503 com frequência.

### 403 `PERMISSION_DENIED` intermitente

**Sintoma.** "The caller does not have permission", alternando com respostas 200 para o mesmo modelo.

**Causa.** Foi observado com uma chave recém-criada logo depois de ativar o faturamento. O Agno trata 403 como erro definitivo e não tenta de novo.

**O que fazer.** Rode de novo; o caso costuma passar na segunda tentativa. Se o 403 for constante, a chave não tem acesso ao modelo: confira o projeto da chave no AI Studio.

Exemplo registrado: [`evidencias/falhas/T03_tentativa1_403.json`](../evidencias/falhas/T03_tentativa1_403.json).

### Porta ocupada

**Sintoma.** O AgentOS ou o uvicorn não sobe (`address already in use`, `[Errno 10048]`), ou o script falha com "AgentOS encerrou ao iniciar".

**Atenção.** Se já houver **outro** AgentOS na 7777, o script pode conversar com ele em vez do que subiu com o IBGE ou a base indisponíveis, e o T06 falha. A porta precisa estar realmente livre.

```powershell
Get-NetTCPConnection -LocalPort 7777,8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Get-Process -Id $_.OwningProcess }
# para encerrar:
Get-NetTCPConnection -LocalPort 7777 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

```bash
# Linux / macOS
lsof -nP -iTCP:7777 -sTCP:LISTEN
kill <PID>
# Git Bash no Windows
netstat -ano | grep -E ':7777 .*LISTEN'     # o PID é a última coluna
taskkill //PID <PID> //F
```

Outra saída é usar outra porta: `AGENTOS_PORT=7778` e `AGENTOS_URL=http://localhost:7778` no `.env`. Para o app web, use `--port 8001`.

### Sobrou `data/regras_cnae.json.bak`

**Causa.** O T07 foi interrompido de forma abrupta: terminal fechado, processo morto ou queda de energia. Um `Ctrl+C` comum restaura a base sozinho. O `.bak` é a base **original**, e `data/regras_cnae.json` pode ter ficado com `R-6201-SAAS` alterada para `compativel`.

Enquanto o `.bak` existir, o script se recusa a rodar o T07 e sai com código 2:

```text
data/regras_cnae.json.bak existe: um T07 anterior foi interrompido.
Restaure a base (git checkout -- data/regras_cnae.json), apague o .bak e rode de novo.
```

Para restaurar, use a versão do git:

```powershell
git checkout -- data/regras_cnae.json
Remove-Item data/regras_cnae.json.bak
git status --short data/
```

```bash
git checkout -- data/regras_cnae.json
rm data/regras_cnae.json.bak
git status --short data/          # nenhuma linha
```

Se você editou a base de propósito e quer recuperar a sua versão de antes do T07, mova o backup por cima em vez de usar o `git checkout`: `Move-Item -Force data/regras_cnae.json.bak data/regras_cnae.json` (PowerShell) ou `mv data/regras_cnae.json.bak data/regras_cnae.json` (bash).

Depois, confira com o comando do passo 5.1: `R-6201-SAAS` deve estar `incompativel`.

### `tmp/agentos.db`

É o SQLite das **sessões** do AgentOS. É criado na primeira subida e não guarda dado do domínio. Ele pode ser apagado com o AgentOS parado:

```powershell
Remove-Item tmp/agentos.db
```

```bash
rm tmp/agentos.db
```

**Quando apagar.**
- Com erro `database is locked`. Costuma ser outro AgentOS aberto: veja [Porta ocupada](#porta-ocupada).
- Com erro de esquema depois de trocar de versão do projeto.
- Para começar sem histórico.

**Efeito.** Cada caso do script usa um `session_id` novo, então o histórico antigo não interfere nos resultados.

### Acentos trocados no Git Bash

No Git Bash, o Python escreve em `cp1252` quando a saída não é um console, e o terminal mostra `AfirmaþÒo` em vez de `Afirmação`. Use `PYTHONUTF8=1 uv run python scripts/run_casos.py` ou `export PYTHONUTF8=1` na sessão. Os comandos de leitura deste guia já usam `-X utf8`, que tem o mesmo efeito. Os arquivos de evidência são sempre gravados em UTF-8.

---

## 12. Limpeza

1. Pare os processos: `Ctrl+C` no terminal do AgentOS e no do app web. Depois, confira as portas (passo 0): nenhuma linha.
2. Confira e restaure a base:

   ```bash
   git status --short
   git checkout -- data/regras_cnae.json
   ```

   Se sobrou um `.bak`, veja [Sobrou `data/regras_cnae.json.bak`](#sobrou-dataregras_cnaejsonbak).
3. Opcional: volte às evidências versionadas. A bateria sobrescreveu `evidencias/`.

   ```bash
   git checkout -- evidencias/
   ```

4. Opcional: apague os arquivos temporários (`tmp/`: sessões, `resposta.json` e a cópia das evidências).

   ```powershell
   Remove-Item -Recurse -Force tmp
   ```

   ```bash
   rm -rf tmp
   ```

5. Em máquina compartilhada, apague o `.env`, que contém a sua chave.

No fim, `git status --short` não deve mostrar nenhuma linha. O `.env` e o `tmp/` estão no `.gitignore` e não aparecem.

---

## Sequência rápida

Os mesmos comandos, sem explicação. As linhas marcadas `[T1]` e `[T2]` rodam em terminais separados e ficam rodando até `Ctrl+C`.

### PowerShell

```powershell
# 0-1. pré-requisitos e código
git --version; uv --version; curl.exe --version
Get-NetTCPConnection -LocalPort 7777,8000 -State Listen -ErrorAction SilentlyContinue   # nenhuma linha
git clone <URL-do-repositório> cnae-audit
cd cnae-audit
git checkout v1.1-atividade

# 2-3. instalar e configurar
uv sync --frozen
Copy-Item .env.example .env
notepad .env                     # preencha GOOGLE_API_KEY
uv run python -X utf8 -c "from agente import config; from google import genai; c = genai.Client(); print('chave aceita; modelo encontrado:', c.models.get(model=config.gemini_model_id()).name)"

# 4. offline
uv run pytest
uv run ruff check .

# 5. fontes
Select-String -Path data/regras_cnae.json -Pattern '"R-6201-SAAS"','"R-6203-LIC-NAO-CUSTOM"' -Context 0,2
curl.exe -sS https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/6201501
curl.exe -sS https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/9999999

# 6. AgentOS + curl
uv run python -m agente.servidor                                             # [T1]
curl.exe -sS http://localhost:7777/health                                    # [T2]
curl.exe --fail-with-body -sS --create-dirs -o tmp/resposta.json -w "HTTP %{http_code}" http://localhost:7777/agents/verificador-cnae/runs --data-urlencode "message=Vendo assinatura de um sistema SaaS padronizado e meu contador disse que posso usar o CNAE 6201-5/01. Isso confere?" --data-urlencode "stream=false"
uv run python -X utf8 -c "import json; d=json.load(open('tmp/resposta.json', encoding='utf-8')); print(d['status'], d['model']); print(d['content']); [print('-', t['tool_name'], t['tool_args'], '->', {k: v for k, v in json.loads(t['result']).items() if k in ('status', 'descricao', 'compatibilidade', 'regra_aplicada', 'status_afirmacao')}) for t in d['tools']]"
# Ctrl+C no [T1]

# 7. casos T01-T07 (porta 7777 livre)
New-Item -ItemType Directory -Force tmp | Out-Null; Copy-Item -Recurse evidencias tmp/evidencias_versionadas
uv run python scripts/run_casos.py
# plano gratuito: $env:CASOS_PAUSA_S = "60"; uv run python scripts/run_casos.py T01 T02 T03 T04
uv run python scripts/run_casos.py T03                                       # um caso só

# 9. T08 pela tela
uv run python -m agente.servidor                                             # [T1]
uv run uvicorn web.main:app --port 8000                                      # [T2]
# navegador: http://localhost:8000 -> 6201-5/01, SaaS, "Disseram que sim" -> Verificar
# erro: Ctrl+C no [T1] -> Verificar -> "Não foi possível verificar agora" + "Tentar novamente"

# 10. comparar
uv run python -X utf8 -c "import json, glob, os; r=lambda p: json.load(open(p, encoding='utf-8')); v=lambda d: [json.loads(t['result']) for t in (d['resposta']['corpo'].get('tools') or []) if t['tool_name'] == 'validar_enquadramento' and t.get('result')]; k=lambda d: (d['situacao'], d['pos_validacao']['verificada'], d['pos_validacao']['status_afirmacao'], [(x.get('status'), x.get('compatibilidade'), x.get('regra_aplicada'), (x.get('tributacao') or {}).get('anexo_resultante')) for x in v(d)[-1:]]); [print(os.path.basename(p), 'IGUAL' if k(r(p)) == k(r(os.path.join('tmp', 'evidencias_versionadas', os.path.basename(p)))) else 'DIFERENTE', k(r(p))) for p in sorted(glob.glob(os.path.join('evidencias', 'T*.json')))]"

# 12. limpeza (Ctrl+C em [T1] e [T2] antes)
git checkout -- data/regras_cnae.json evidencias/
Remove-Item -Recurse -Force tmp
git status --short
```

### bash

```bash
# 0-1. pré-requisitos e código
git --version; uv --version; curl --version
lsof -nP -iTCP:7777 -iTCP:8000 -sTCP:LISTEN          # nenhuma linha (Git Bash: netstat -ano | grep -E ':(7777|8000) .*LISTEN')
git clone <URL-do-repositório> cnae-audit
cd cnae-audit
git checkout v1.1-atividade

# 2-3. instalar e configurar
uv sync --frozen
cp .env.example .env
nano .env                        # preencha GOOGLE_API_KEY
uv run python -X utf8 -c "from agente import config; from google import genai; c = genai.Client(); print('chave aceita; modelo encontrado:', c.models.get(model=config.gemini_model_id()).name)"

# 4. offline
uv run pytest
uv run ruff check .

# 5. fontes
grep -n -A2 -E '"R-6201-SAAS"|"R-6203-LIC-NAO-CUSTOM"' data/regras_cnae.json
grep -n '4711' data/regras_cnae.json || echo "4711-3/02 não está na base"
curl -sS https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/6201501; echo
curl -sS https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/9999999; echo

# 6. AgentOS + curl
uv run python -m agente.servidor                                             # [T1]
curl -sS http://localhost:7777/health; echo                                  # [T2]
curl --fail-with-body -sS --create-dirs -o tmp/resposta.json -w 'HTTP %{http_code}\n' \
  http://localhost:7777/agents/verificador-cnae/runs \
  --data-urlencode 'message=Vendo assinatura de um sistema SaaS padronizado e meu contador disse que posso usar o CNAE 6201-5/01. Isso confere?' \
  --data-urlencode 'stream=false'
uv run python -X utf8 -c "import json; d=json.load(open('tmp/resposta.json', encoding='utf-8')); print(d['status'], d['model']); print(d['content']); [print('-', t['tool_name'], t['tool_args'], '->', {k: v for k, v in json.loads(t['result']).items() if k in ('status', 'descricao', 'compatibilidade', 'regra_aplicada', 'status_afirmacao')}) for t in d['tools']]"
# Ctrl+C no [T1]

# 7. casos T01-T07 (porta 7777 livre)
mkdir -p tmp && cp -r evidencias tmp/evidencias_versionadas
uv run python scripts/run_casos.py
# plano gratuito: CASOS_PAUSA_S=60 uv run python scripts/run_casos.py T01 T02 T03 T04
uv run python scripts/run_casos.py T03                                       # um caso só

# 9. T08 pela tela
uv run python -m agente.servidor                                             # [T1]
uv run uvicorn web.main:app --port 8000                                      # [T2]
# navegador: http://localhost:8000 -> 6201-5/01, SaaS, "Disseram que sim" -> Verificar
# erro: Ctrl+C no [T1] -> Verificar -> "Não foi possível verificar agora" + "Tentar novamente"

# 10. comparar
uv run python -X utf8 -c "import json, glob, os; r=lambda p: json.load(open(p, encoding='utf-8')); v=lambda d: [json.loads(t['result']) for t in (d['resposta']['corpo'].get('tools') or []) if t['tool_name'] == 'validar_enquadramento' and t.get('result')]; k=lambda d: (d['situacao'], d['pos_validacao']['verificada'], d['pos_validacao']['status_afirmacao'], [(x.get('status'), x.get('compatibilidade'), x.get('regra_aplicada'), (x.get('tributacao') or {}).get('anexo_resultante')) for x in v(d)[-1:]]); [print(os.path.basename(p), 'IGUAL' if k(r(p)) == k(r(os.path.join('tmp', 'evidencias_versionadas', os.path.basename(p)))) else 'DIFERENTE', k(r(p))) for p in sorted(glob.glob(os.path.join('evidencias', 'T*.json')))]"

# 12. limpeza (Ctrl+C em [T1] e [T2] antes)
git checkout -- data/regras_cnae.json evidencias/
rm -rf tmp
git status --short
```
