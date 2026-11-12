# Relatório dos casos de teste

## 1. Ambiente da execução final

| Item | Valor |
| --- | --- |
| Data | 12/11/2026, entre 03:34 e 03:42 UTC |
| Modelo | Google Gemini, id **`gemini-3.6-flash`** (`agno.models.google.Gemini`, temperatura 0), conta com faturamento ativo |
| Versões | Python 3.12, Agno 3.1.12, google-genai 3.2.0, FastAPI 0.162.5 (todas fixadas em `uv.lock`) |
| Base de regras | `data/regras_cnae.json`, versão `1.0.0`, data de referência `2026-11-11` |
| Fonte externa | API CNAE do IBGE (`https://servicodados.ibge.gov.br/api/v2/cnae`), consultada ao vivo |
| Como reproduzir | T01–T07: `uv run python scripts/run_casos.py`. T08: passo a passo no [README](../README.md#jornada-no-projeto-t08-passo-a-passo). Guia completo, com saídas esperadas: [`reproducao.md`](reproducao.md) |

Os casos T01 a T07 passam pela **API HTTP do AgentOS** (`POST /agents/verificador-cnae/runs`, `stream=false`). Cada caso usa uma sessão nova (`session_id` único). O script `scripts/run_casos.py`:

1. sobe o AgentOS;
2. envia a mensagem;
3. confere a resposta com checagens automáticas, inclusive a mesma pós-validação do app web (`web/verificacao.py`);
4. grava a requisição e a resposta HTTP **brutas** em `evidencias/<caso>.json`.

No JSON da resposta, o campo `resposta.corpo.tools` traz cada chamada de ferramenta feita pelo agente, com `tool_args` e `result`. É isso que liga a entrada à chamada da ferramenta, ao retorno dela e à resposta final.

**O resultado esperado foi definido pela inspeção da base e da API do IBGE**, antes da execução, e não pela resposta do modelo (`docs/solucao.md` §11). Exemplos:

- a regra `R-6201-SAAS` tem `resultado: "incompativel"`, logo a afirmação "o 6201-5/01 serve para SaaS" deve sair `contradita`;
- folha 30.000 / receita 100.000 = 30% ≥ 28%, e o 6203-1/00 tem `anexo_fator_r_alto: "III"`.

## 2. Casos

| Caso | Entrada | Esperado (pela inspeção da fonte) | Obtido | Ferramentas executadas (args → status) | Situação | Evidência |
| --- | --- | --- | --- | --- | --- | --- |
| **T01** — 1ª ferramenta e informação conhecida confirmada | "O CNAE 6203-1/00 é de licenciamento de programas de computador não customizáveis? Confira na fonte oficial e mostre a evidência." | IBGE devolve "DESENVOLVIMENTO E LICENCIAMENTO DE PROGRAMAS DE COMPUTADOR NÃO CUSTOMIZÁVEIS"; a afirmação **confere**; URL + data/hora | Descrição oficial citada e afirmação confirmada; "Onde conferir" com `…/subclasses/6203100`, consultado em `2026-11-12T03:34:04+00:00` | `consultar_cnae_ibge("6203-1/00")` → `ok` | **Passou** | [`evidencias/T01.json`](../evidencias/T01.json) |
| **T02** — 2ª ferramenta (regra + Fator R) | Formulário: CNAE 6203-1/00, "Vendo licenças de um programa pronto…", folha 30.000, receita 100.000, "me disseram Anexo III" | `compativel` pela regra `R-6203-LIC-NAO-CUSTOM`; Fator R 30% ≥ 28% → Anexo III; afirmação **confirmada** | `compativel`, `R-6203-LIC-NAO-CUSTOM`, razão `0.3` (30,00%), anexo `III`, comparação `anexo: III × III → confere`, `status_afirmacao: confirmada`; chave `cnaes.6203-1/00.regras[id=R-6203-LIC-NAO-CUSTOM]` v1.0.0 | `consultar_cnae_ibge("6203-1/00")` → `ok`; `validar_enquadramento(6203-1/00, licenciamento_nao_customizavel, folha 30000, receita 100000, anexo "Anexo III")` → `ok` | **Passou** | [`evidencias/T02.json`](../evidencias/T02.json) |
| **T03** — afirmação contradita pela fonte | "Vendo um SaaS padronizado a R$ 99/mês, igual para todos os clientes, e meu contador disse que posso usar o CNAE 6201-5/01. Está certo?" | `R-6201-SAAS` → `incompativel`; afirmação **contradita**; sugestões 6311-9/00 e 6319-4/00 (regras `compativel` para SaaS) consultadas no IBGE | `incompativel`, `contradita`, motivo da regra citado; sugeriu 6311-9/00 e 6319-4/00 com as descrições oficiais | `consultar_cnae_ibge("6201-5/01")` → `ok`; `validar_enquadramento(6201-5/01, saas_padronizado, afirmacao_compativel=true)` → `ok`; `consultar_cnae_ibge("6311-9/00")` → `ok`; `consultar_cnae_ibge("6319-4/00")` → `ok` | **Passou** (2ª tentativa; ver §3) | [`evidencias/T03.json`](../evidencias/T03.json) |
| **T04** — informação ausente na fonte | Formulário: CNAE 4711-3/02, "Revendo computadores…", "disseram que sim" | 4711-3/02 existe no IBGE (supermercados) mas **não está na base** → `nao_encontrado`, `indeterminado`, **sem evidência suficiente**; nada inventado | IBGE: "COMÉRCIO VAREJISTA DE MERCADORIAS EM GERAL, COM PREDOMINÂNCIA DE PRODUTOS ALIMENTÍCIOS - SUPERMERCADOS"; base: "não está na base… isso não significa que ele seja incompatível"; `sem_evidencia_suficiente` | `consultar_cnae_ibge("4711-3/02")` → `ok`; `validar_enquadramento(4711-3/02, revenda_hardware, afirmacao_compativel=true)` → `nao_encontrado` | **Passou** | [`evidencias/T04.json`](../evidencias/T04.json) |
| **T05a** — entrada ambígua | "Posso usar o CNAE de desenvolvimento?" | Sem CNAE e sem modelo de negócio → **pedido de esclarecimento**, sem veredito e sem CNAE inventado | Seção `## Preciso de mais informações`, pedindo o código de 7 dígitos e o modelo de negócio em linguagem simples | nenhuma (correto: não há o que consultar) | **Passou** (após correção; ver §3) | [`evidencias/T05a.json`](../evidencias/T05a.json) |
| **T05b** — entrada inválida | "Meu CNAE é 62015 e vendo assinatura de um software padronizado pela internet. Esse CNAE serve?" | Código com 5 dígitos é inválido → `entrada_invalida` da ferramenta **ou** pedido de esclarecimento; sem veredito | Pedido de esclarecimento: "possui apenas 5 dígitos… precisa ter 7 dígitos no formato NNNN-N/NN" | nenhuma nesta execução. Na 1ª execução, `consultar_cnae_ibge("62015")` → `entrada_invalida` | **Passou** (após correção; ver §3) | [`evidencias/T05b.json`](../evidencias/T05b.json) |
| **T06a** — fonte externa indisponível | Mesma entrada do T07, com `IBGE_BASE_URL=http://ibge-indisponivel.invalid/…` | IBGE `indisponivel`, ressalva explícita, conclusão só pela base (`contradita`), sem apresentar a consulta ao IBGE como bem-sucedida | Resultado com "A API pública do IBGE esteve indisponível… esta análise apoia-se inteiramente na base de regras"; `contradita` vindo da base | `consultar_cnae_ibge` ×3 → `indisponivel` ("Falha de conexão com o IBGE (ConnectError)"); `validar_enquadramento` → `ok` | **Passou** | [`evidencias/T06a.json`](../evidencias/T06a.json), [`logs/agentos_T06a.log`](../evidencias/logs/agentos_T06a.log) |
| **T06b** — base de regras indisponível | Mesma entrada, com `REGRAS_PATH=data/regras_cnae_AUSENTE.json` | `erro_fonte`, **nenhum veredito** | "não foi possível emitir veredito devido a erro de fonte na base de regras"; a tela mostraria "Sem veredito" | `consultar_cnae_ibge("6201-5/01")` → `ok`; `validar_enquadramento` → `erro_fonte` ("Base de regras não encontrada…") | **Passou** | [`evidencias/T06b.json`](../evidencias/T06b.json), [`logs/agentos_T06b.log`](../evidencias/logs/agentos_T06b.log) |
| **T07** — alteração de dado na fonte | Formulário: 6201-5/01, SaaS, "disseram que sim", repetido em **nova sessão** | Antes: `R-6201-SAAS.resultado = "incompativel"` → `contradita`. O script muda para `"compativel"`. Depois → `confirmada`. Base restaurada ao fim | Antes: `contradita`. Depois: `compativel`, motivo "[T07] Alteração temporária de teste…", `confirmada`. Restaurado: `incompativel` | Antes: IBGE ×3 + `validar_enquadramento` → `ok`. Depois: `consultar_cnae_ibge` + `validar_enquadramento` → `ok` | **Passou** | [`evidencias/T07-antes.json`](../evidencias/T07-antes.json), [`evidencias/T07-depois.json`](../evidencias/T07-depois.json) (campo `dado_alterado`) |
| **T08** — jornada completa no projeto | Tela `http://localhost:8000`: CNAE `6201-5/01`, "Vendo assinatura de um sistema na internet… (SaaS)", "Disseram que sim" → **Verificar** | Estado "Verificando…"; o app web chama o AgentOS; selo **"não confere com a base"**, explicação, "Onde conferir" e ferramentas executadas | Como esperado (capturas). Log do backend: `ferramentas=['consultar_cnae_ibge', 'validar_enquadramento', 'consultar_cnae_ibge', 'consultar_cnae_ibge'] verificada=True status_afirmacao=contradita` | As mesmas 4 do T03 | **Passou** (a 1ª tentativa caiu num 403 do Gemini, tratado na tela; ver §3) | [`evidencias/T08/`](../evidencias/T08/): `01_formulario_preenchido.png`, `02_verificando.png`, `03_resultado.png`, `04_ferramentas_executadas.png`, `extra_erro_tratado.png`, `backend_web.log`, `agentos.log` |

**Evidência de cada ferramenta pelo agente:** `consultar_cnae_ibge` em T01, T03, T04, T06a e T08; `validar_enquadramento` em T02, T03, T04, T06a, T06b, T07 e T08. Todas as chamadas estão no campo `tools` das respostas HTTP salvas.

**Chamada HTTP do README:** [`evidencias/curl_exemplo.json`](../evidencias/curl_exemplo.json) traz a resposta bruta do `curl` documentado.

## 3. Falhas encontradas e correções

Todas as falhas abaixo aconteceram em execuções com o modelo real e foram corrigidas. Os casos afetados foram executados de novo, e o resultado final é o da tabela acima.

| # | Falha | Casos | Causa | Correção | Reexecução |
| --- | --- | --- | --- | --- | --- |
| 1 | Timeout de 90 s no 1º caso, que abortou a bateria inteira | T01 | `gemini-3.7-flash` (o padrão anterior) respondia **503 UNAVAILABLE** ("high demand"), e o SDK repetia a chamada por ~115 s. O script não tratava o timeout HTTP | Padrão trocado para `gemini-3.6-flash`. Timeout de 30 s por requisição ao Gemini (`GEMINI_TIMEOUT_S`). O script registra o timeout como falha do caso e segue | T01 passou |
| 2 | Run com `status: ERROR` e o JSON do erro em `content` | T03, T06a, T06b, T07 | **429** do plano gratuito (5 requisições/min, depois 20/dia) e 503 transitório. Cada caso faz de 3 a 4 chamadas ao modelo | Até 2 novas tentativas no modelo, com espera de 8 s e 16 s, em 429/5xx. Pausa entre casos no script (`CASOS_PAUSA_S`; use 60 no plano gratuito). Timeout do app web para o AgentOS: 120 s. A bateria final rodou numa conta com faturamento | Todos passaram |
| 3 | **Pós-validação reprovou**: "CNAE citado sem origem em ferramenta: 6201-5/01" (T05a) e "…6201-5/02" (T05b) | T05a, T05b | Nos pedidos de esclarecimento, o modelo deu **códigos CNAE de exemplo** tirados do próprio conhecimento, o que viola o invariante "nunca inventar CNAE". A checagem em código pegou | Nova instrução em `agente/instrucoes.py`: em pedido de esclarecimento, não dar exemplos de código; descrever o formato de forma genérica (`NNNN-N/NN`). **A checagem não foi afrouxada** | T05a e T05b passaram |
| 4 | Run com **403 PERMISSION_DENIED** ("The caller does not have permission") | T03 (1ª tentativa), T08 (1ª tentativa) | Erro intermitente da chave nova logo após ativar o faturamento: o mesmo modelo alternava entre 200 e 403 em chamadas seguidas. O Agno trata 403 como erro definitivo e não repete a chamada | Nenhuma no código. O comportamento está correto: o AgentOS devolveu `status: ERROR`, e o app web mostrou "Não foi possível verificar agora" com "Tentar novamente", sem resultado parcial (`extra_erro_tratado.png`). O caso foi executado de novo | T03 e T08 passaram. Evidência da falha: [`evidencias/falhas/T03_tentativa1_403.json`](../evidencias/falhas/T03_tentativa1_403.json) |

## 4. Limitações conhecidas

- **Não determinismo do modelo.** Mesmo com temperatura 0, o texto varia entre execuções. Exemplo: no T05b, o agente às vezes chama a ferramenta (que devolve `entrada_invalida`) e às vezes pede esclarecimento direto. O veredito não varia, porque é calculado em código, e a pós-validação barra respostas fora do contrato.
- **A pós-validação confere a origem dos códigos CNAE, não de cada frase.** Uma explicação imprecisa em texto livre, sem código CNAE, passa pela checagem. Exemplo: no T05b, o agente disse que um código de 5 dígitos "corresponde ao grupo/classe". O selo e os dados exibidos continuam vindo das ferramentas.
- **Dependência de serviços externos.** O Gemini (cota, sobrecarga, 403 intermitente) e o IBGE ficam fora do controle do projeto. As falhas são declaradas, nunca mascaradas. Sem cache do IBGE, por decisão (`docs/solucao.md` §13).
- **Quebras de linha simples não são renderizadas.** Na seção "Resultado" da tela, as linhas "Compatibilidade" e "Status da afirmação" aparecem na mesma linha (`03_resultado.png`). É só estético: o selo é calculado à parte.
- **Base de regras didática e restrita** a 12 CNAEs de tecnologia, SaaS e infoprodutos. A compatibilidade CNAE × modelo de negócio é uma simplificação do autor, com base legal real; zonas cinzentas ficam como `indeterminado`.
- **Os horários dos logs do app web estão no fuso local (UTC−3).** Os timestamps das evidências do IBGE e do script estão em UTC.
