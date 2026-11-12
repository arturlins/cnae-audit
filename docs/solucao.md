# Verificador de CNAE — Especificação da Solução

> **Status:** especificação da v1 (entrega da atividade de Sistemas Inteligentes Aplicados — CESMAC).
> Modalidade **individual**. Requisitos fixos em [`atividade.md`](atividade.md).

> ⚠️ **Material de referência.** O Verificador de CNAE dá uma noção inicial sobre a coerência entre CNAE e modelo de negócio. Ele **não substitui a consulta a um contador ou advogado** e não constitui consultoria tributária.

---

## 1. Motivação e problema

A pergunta que originou o projeto: *"o CNAE de quem vende SaaS é o mesmo de quem desenvolve software?"*. Não é. Um empresário conhecido de um professor foi multado em cerca de R$ 40 mil porque o CNAE escolhido na abertura da empresa não correspondia à atividade exercida.

Erros desse tipo são comuns em startups de tecnologia: o CNAE de **desenvolvimento sob encomenda** (`6201-5/01`) é usado para vender **software padronizado por assinatura**, ou um infoproduto é registrado como atividade de marketing. As consequências vão de enquadramento errado no Simples Nacional a autuações.

## 2. Usuários

| Perfil | Necessidade | Como o produto atende |
| --- | --- | --- |
| **Leigo (principal):** founder, quem vende SaaS, cursos ou e-books | Ter uma noção, em linguagem simples, se "o que o contador fez" faz sentido | Formulário com opções em linguagem do dia a dia; resultado com selo "confere / não confere" e próximos passos |
| **Profissional (secundário):** contador, advogado | Ponto de partida de pesquisa | Seção "Onde conferir" com artigo de lei, link do IBGE e registro da base |

## 3. Escopo da v1

**Dentro:**
- 12 CNAEs do recorte tecnologia, SaaS e infoprodutos (seção 7.3).
- Verificação de compatibilidade CNAE × modelo de negócio.
- Fator R e anexo do Simples Nacional resultante.
- Confronto de uma afirmação do usuário com a base.
- Execução local.

**Fora (expansão, seção 12):** demais setores, cadastro de empresas, React, cache do IBGE, deploy.

## 4. Jornada do usuário (T08)

1. O usuário abre `http://localhost:8000` (Verificador de CNAE).
2. Preenche o formulário:
   - **CNAE** registrado ou sugerido. Aceita `6201-5/01`, `6201501` ou `62.01-5-01`.
   - **O que sua empresa faz**: um select com rótulos simples que mapeiam 1:1 para o enum `modelo_negocio`. A opção *"Não sei / outro"* abre um campo de texto livre.
   - **O que te disseram** (opcional): "esse CNAE serve para o meu negócio" (sim / não / não sei) e o anexo informado (I a V / não sei).
   - **Folha de pagamento e receita bruta dos últimos 12 meses** (opcionais, para o Fator R).
3. Ao clicar em **Verificar**, o botão é desabilitado e aparece "Verificando…".
4. O backend (`web/`) monta a mensagem, chama `POST /agents/verificador-cnae/runs` no AgentOS e aplica a **pós-validação em código** (seção 9.3).
5. A tela mostra o resultado (seção 10), ou um erro amigável se o AgentOS estiver indisponível ou exceder o tempo.

## 5. Arquitetura

```text
Usuário (navegador)
   │  formulário HTMX
   ▼
App web "Verificador de CNAE"  — FastAPI + Jinja2 (porta 8000)        [web/]
   │  POST /agents/verificador-cnae/runs  (form: message, stream=false, session_id)
   │  Authorization: Bearer $OS_SECURITY_KEY   (opcional, só no servidor)
   ▼
AgentOS — API HTTP (porta 7777)                                       [agente/servidor.py]
   ▼
Agente Agno "verificador-cnae" — Gemini, temperatura 0, tool_call_limit=6
   ├──► consultar_cnae_ibge(codigo_cnae)  ──► API pública do IBGE (CNAE 2.3, subclasses)
   └──► validar_enquadramento(...)        ──► data/regras_cnae.json  (motor de regras em Python)
   ▼
Resposta (markdown com seções fixas) + tool calls com argumentos e retornos
   ▼
App web: pós-validação em código → resultado com selo, explicação, "Onde conferir" e ferramentas executadas
```

O app web e o AgentOS são **processos separados**. O app web é um cliente fino da API do AgentOS (`web/agentos_client.py`), o que permite trocar o frontend por React sem mexer no agente.

## 6. Agente

| Item | Valor |
| --- | --- |
| ID no AgentOS | `verificador-cnae` |
| Framework | Agno 3.1.x + AgentOS |
| Modelo | Google Gemini (`agno.models.google.Gemini`, chave em `GOOGLE_API_KEY`). O id vem de `GEMINI_MODEL_ID`; o padrão é `gemini-3.7-flash` (o padrão do Agno 3.1.12), e o id efetivamente usado fica registrado em `docs/testes.md` |
| Temperatura | 0 |
| Limite de ferramentas | `tool_call_limit=6` (o T03 usa até 4) |
| Sessões | `SqliteDb` em `tmp/agentos.db` (só sessões; **não** é fonte de dados do domínio). Histórico das 3 últimas execuções da sessão, para responder a pedidos de esclarecimento |
| Retorno das ferramentas | As ferramentas devolvem `dict`; o agente as recebe envolvidas por `como_json` (`agente/agente.py`), que serializa em JSON. Sem isso o Agno usaria `str(dict)` (repr de Python), ilegível para o pós-validador |
| Timeouts | IBGE 5 s (`IBGE_TIMEOUT_S`); app web → AgentOS 90 s (`AGENTOS_TIMEOUT_S`) |

### 6.1. Instruções (resumo; texto integral em `agente/instrucoes.py`)

1. **Objetivo:** verificar se um CNAE é coerente com o modelo de negócio informado e confrontar o que o usuário ouviu com a base.
2. **Toda informação fiscal vem de ferramentas.** É proibido citar CNAE, descrição, anexo, percentual ou artigo que não esteja num retorno de ferramenta.
3. **Ordem:**
   1. `consultar_cnae_ibge` para cada CNAE citado.
   2. `validar_enquadramento` com o `modelo_negocio` do enum.
   3. Se sugerir outro CNAE, consultar esse CNAE no IBGE também.
4. **Ambiguidade:** sem CNAE, com CNAE malformado, ou com descrição de negócio que não se encaixe claramente em um valor do enum, o agente **pede esclarecimento** (seção `## Preciso de mais informações`) e não chuta. Quando mapeia texto livre para o enum, declara a interpretação ("Entendi seu negócio como: …").
5. **O veredito não é do modelo.** O status da afirmação é o `status_afirmacao` devolvido pela ferramenta. O agente explica, mas não altera.
6. **Falhas:** se uma ferramenta devolver `indisponivel`, `erro_fonte` ou `nao_encontrado`, o agente declara a limitação e nunca apresenta a consulta como bem-sucedida.
7. **Fora do escopo** (cálculo de impostos devidos, planejamento tributário, abertura de empresa, outros assuntos): recusa educadamente (seção `## Fora do escopo`) e explica o que a ferramenta faz.
8. **Linguagem simples**, sem "parecer" ou "consultoria". Aviso de material de referência no topo.
9. **Template fixo de resposta:** `## Resultado`, `## Em linguagem simples`, `## Por que chegamos nisso`, `## Onde conferir`.

## 7. Fontes de dados

### 7.1. API pública do IBGE (externa, ao vivo)

- Endpoint: `GET https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/{codigo7}`. A base é configurável em `IBGE_BASE_URL`.
- Comportamento verificado em 11/11/2026:
  - Código existente: **HTTP 200 com objeto** (`id`, `descricao`, `classe{…grupo{…divisao{…secao}}}`, `observacoes`, `atividades`).
  - Código inexistente (`9999999`): **HTTP 200 com `[]`**. Não é 404.
- Reprodução manual: `curl https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/6201501`.

### 7.2. Base de regras `data/regras_cnae.json` (persistida, inspecionável)

A base é o motor de verdade do projeto. Ela é relida a cada chamada, sem cache. Estrutura prevista (detalhes em `docs/dados.md`):

```jsonc
{
  "versao": "1.0.0",
  "data_referencia": "2026-11-11",
  "aviso": "Dados simplificados para fins didáticos. Material de referência; não substitui consulta profissional.",
  "fontes_legais": { "LC123-18-5D-IV": { "norma": "Lei Complementar nº 123/2006", "dispositivo": "art. 18, § 5º-D, IV", "trecho": "elaboração de programas de computadores (...)", "url": "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm" } },
  "modelos_negocio": {
    "saas_padronizado": { "rotulo": "Vendo assinatura de um sistema na internet, igual para todos os clientes (SaaS)" }
  },
  "cnaes": {
    "6201-5/01": {
      "denominacao": "Desenvolvimento de programas de computador sob encomenda",
      "tributacao": { "sujeito_fator_r": true, "anexo_fator_r_alto": "III", "anexo_fator_r_baixo": "V", "confianca": "alta",
                      "fundamentos": ["LC123-18-5D-IV", "LC123-18-5M", "LC123-18-24"], "nota": "…" },
      "regras": [
        { "id": "R-6201-SAAS", "modelo_negocio": "saas_padronizado", "resultado": "incompativel", "motivo": "…" }
      ]
    }
  }
}
```

### 7.3. Recorte de CNAEs e base legal

São 12 CNAEs. As descrições foram conferidas na API do IBGE e os dispositivos no texto da LC 123/2006 (Planalto), ambos em 11/11/2026. O anexo sai do **art. 18 da LC 123/2006**. A Resolução CGSN 140/2018 não traz uma tabela CNAE → anexo: os Anexos VI e VII dela listam CNAEs *impeditivos* e *ambíguos*.

| CNAE | Descrição oficial (IBGE) | Anexo na base | Confiança |
| --- | --- | --- | --- |
| 6201-5/01 | Desenvolvimento de programas de computador sob encomenda | III; V se Fator R < 28% (§5º-D, IV + §5º-M) | alta |
| 6202-3/00 | Desenvolvimento e licenciamento de programas customizáveis | III; V se Fator R < 28% (§5º-D, IV/V + §5º-M) | alta |
| 6203-1/00 | Desenvolvimento e licenciamento de programas não customizáveis | III; V se Fator R < 28% (§5º-D, V + §5º-M) | alta |
| 6204-0/00 | Consultoria em tecnologia da informação | V; III se Fator R ≥ 28% (§5º-I, IX + §5º-J) | alta |
| 7490-1/04 | Intermediação e agenciamento de serviços e negócios | V; III se Fator R ≥ 28% (§5º-I, VII + §5º-J) | alta |
| 8599-6/04 | Treinamento em desenvolvimento profissional e gerencial | III, sem Fator R (§5º-B, I: "gerenciais") | alta |
| 8599-6/99 | Outras atividades de ensino | III, sem Fator R (§5º-B, I: "escolas livres") | média |
| 4751-2/01 | Comércio varejista de equipamentos de informática (contraexemplo) | I (§4º, I) | alta |
| 6209-1/00 | Suporte técnico, manutenção e outros serviços em TI | **não definido**: §5º-F (III) × §5º-I (V/III) | indeterminada |
| 6311-9/00 | Tratamento de dados, provedores de aplicação, hospedagem | **não definido**: §5º-F (III) × §5º-D, V (III/V) | indeterminada |
| 6319-4/00 | Portais, provedores de conteúdo e outros serviços de informação | **não definido**: §5º-F (III) × §5º-D, V (III/V) | indeterminada |
| 7319-0/02 | Promoção de vendas (contraexemplo) | **não definido**: §5º-I, X (V/III) × §5º-F (III) | indeterminada |

Quando a confiança é **indeterminada**, a base não escolhe um anexo. A ferramenta devolve `anexo_resultante: null` com uma nota explicando as duas leituras, e qualquer afirmação sobre o anexo fica como "sem evidência suficiente". A ferramenta não inventa o anexo.

**Achado importante para SaaS:** segundo o CONCLA/IBGE, o 6203-1/00 "NÃO compreende o acesso a programas de computador pela internet (6319-4/00)", e o 6319-4/00 "compreende ainda o acesso a programas na internet". Por isso, na base:
- SaaS × 6319-4/00 e SaaS × 6311-9/00 ("provedores de serviços de aplicação") são **compatíveis**;
- SaaS × 6203-1/00 é **zona cinzenta**, porque é um uso comum na prática mas contraria a nota oficial;
- SaaS × 6201-5/01 é **incompatível**.

**Fora do recorte:** `5811-5/00` (edição de livros), porque não foi possível fundamentar o anexo com segurança, e `5819-1/00`, que trata de cadastros e listas e não de e-books. Detalhes em [`dados.md`](dados.md).

### 7.4. Enum `modelo_negocio`

`saas_padronizado`, `desenvolvimento_sob_encomenda`, `licenciamento_customizavel`, `licenciamento_nao_customizavel`, `consultoria_ti`, `suporte_tecnico`, `hospedagem_infraestrutura`, `portal_conteudo`, `curso_online_gravado`, `mentoria_treinamento_ao_vivo`, `ebook_publicacao_digital`, `marketplace_intermediacao`, `revenda_hardware`, `promocao_vendas`.

O rótulo em linguagem simples de cada valor fica na própria base, em `modelos_negocio.*.rotulo`. A tela e a ferramenta usam a mesma fonte.

## 8. Ferramentas

As duas são **autorais**. As tabelas completas exigidas no item 2.2 da atividade ficam em `docs/ferramentas.md`.

### 8.1. `consultar_cnae_ibge(codigo_cnae: str) -> dict`

- **Quando usar:** para obter a descrição oficial de qualquer CNAE citado ou sugerido.
- **Entrada:** código em qualquer formato usual. O código é normalizado para 7 dígitos e o formato é validado em código.
- **Saída:**
  - Com sucesso: `status: ok`, `codigo` (formatado `NNNN-N/NN`), `descricao`, `hierarquia` (seção/divisão/grupo/classe), `observacoes` (trecho) e `evidencia: {fonte: "API IBGE CNAE", url, consultado_em (ISO UTC)}`.
  - Em caso de problema: `entrada_invalida` (formato), `nao_encontrado` (resposta `[]`) ou `indisponivel` (timeout, erro de rede, 5xx ou JSON inesperado), sempre com `mensagem` e **sem dados**.

### 8.2. `validar_enquadramento(codigo_cnae: str, modelo_negocio: str, folha_12m: float | None = None, receita_bruta_12m: float | None = None, afirmacao_compativel: bool | None = None, anexo_afirmado: str | None = None) -> dict`

- **Quando usar:** para verificar CNAE × modelo de negócio, calcular o Fator R e confrontar o que o usuário ouviu.
- **Validações em código:**
  - formato do CNAE;
  - `modelo_negocio` pertence ao enum. Se não pertencer, devolve `entrada_invalida` com a lista de valores válidos;
  - valores numéricos ≥ 0 e receita > 0;
  - `anexo_afirmado` ∈ {I, II, III, IV, V}.
- **Regras (determinísticas):**
  - **Compatibilidade:** existe regra para (CNAE, modelo)? Se existe, vale o `resultado` dela (`compativel` ou `incompativel`). Se não existe, o resultado é `indeterminado` (ausência ≠ incompatível). CNAE fora da base resulta em `nao_encontrado`.
  - **Fator R** (se o CNAE é sujeito): `razao = folha_12m / receita_bruta_12m`. Se `razao ≥ 0,28`, vale o anexo da faixa ≥ 28%; se for menor, o da faixa < 28% (LC 123, art. 18, §§ 5º-J e 5º-M). Sem folha ou receita, o anexo fica `indeterminado` com a mensagem "informe folha e receita".
  - **`status_afirmacao`:** compara campo a campo o que foi afirmado (compatibilidade e anexo) com o resultado calculado. Se algum campo diverge, `contradita`. Se todos os campos afirmados conferem, `confirmada`. Nos demais casos, `sem_evidencia_suficiente`: nada foi afirmado, ou algum campo afirmado ficou `indeterminado`. A regra é conservadora: só confirma o que a base permite confirmar por inteiro.
  - **CNAEs sugeridos:** são calculados, não armazenados. São todos os CNAEs da base com regra `compativel` para o mesmo modelo de negócio.
- **Saída:** `status`, `compatibilidade`, `regra_aplicada` (id), `motivo`, `cnaes_sugeridos`, `tributacao` (anexo, sujeição ao Fator R, `calculo_fator_r: {folha_12m, receita_bruta_12m, razao, limiar: 0.28, anexo_resultante}`), `status_afirmacao`, `comparacao` (por campo: afirmado × apurado), `fundamento_legal` (lista de dispositivos com URL) e `evidencia: {arquivo: "data/regras_cnae.json", chave: "cnaes.<código>.regras[<id>]", versao, data_referencia}`.
- **Falhas:** arquivo ausente ou JSON inválido resultam em `erro_fonte`, sem veredito.

## 9. Estratégia de validação e evidências

### 9.1. No código das ferramentas
- Normalização e validação de CNAE.
- Validação do enum e dos valores numéricos.
- Compatibilidade, Fator R e `status_afirmacao`.

O LLM não decide nenhum desses resultados.

### 9.2. Nas instruções do agente
Seção 6.1: só usar dados vindos de ferramentas, pedir esclarecimento quando houver ambiguidade e declarar as falhas.

### 9.3. No app web (pós-validação em código, `web/verificacao.py`)
Antes de exibir o resultado, o backend confere quatro coisas:
1. A execução teve pelo menos uma chamada de ferramenta bem-sucedida, exceto nos pedidos de esclarecimento e nas recusas (reconhecidos pelas seções `## Preciso de mais informações` e `## Fora do escopo`).
2. As seções obrigatórias do template estão presentes.
3. Todo código CNAE citado no texto (regex `\d{4}-?\d/?\d{2}`) aparece nos argumentos ou retornos das ferramentas.
4. O selo exibido vem do `status_afirmacao` da última chamada de `validar_enquadramento`, nunca do texto. Se a base devolveu `erro_fonte` ou não foi consultada, a tela mostra "Sem veredito".

As tool calls são lidas do campo `tools` da resposta do AgentOS (`tool_name`, `tool_args`, `result`).

Se alguma checagem falhar, a tela mostra **"Resposta não verificada"** e exibe só os dados brutos das ferramentas.

### 9.4. Referências apresentadas
- **Base:** arquivo, chave e id da regra, versão e data de referência.
- **IBGE:** URL consultada e data/hora UTC.
- **Lei:** norma, dispositivo e link do Planalto.

## 10. Tela de resultado

Em ordem:
1. **Aviso** de material de referência, no topo.
2. **Selo**, a partir do `status_afirmacao`: *"O que te disseram confere com a base"*, *"não confere com a base"* ou *"Não dá para concluir com os dados disponíveis"*.
3. **Em linguagem simples:** de 3 a 5 frases, com o próximo passo (por exemplo: "converse com seu contador sobre…").
4. **Por que chegamos nisso:** a regra e o Fator R explicados em frases simples, com os números usados.
5. **Onde conferir:** artigo da lei, link do IBGE e registro da base, apresentados como "fontes para você ou seu contador conferirem".
6. **Ferramentas executadas** (recolhível): argumentos e retornos brutos.
7. **Erros:** AgentOS fora do ar ou tempo excedido resultam em mensagem amigável e botão "tentar novamente", nunca em resultado parcial disfarçado.

## 11. Casos de teste (planejamento; o relatório fica em `docs/testes.md`)

Os casos T01–T07 rodam via HTTP com `scripts/run_casos.py`. As respostas brutas ficam salvas em `evidencias/`. O resultado esperado é definido pela inspeção da base, não pela resposta do modelo.

| Caso | Entrada | Esperado |
| --- | --- | --- |
| T01 | "O CNAE 6203-1/00 é de licenciamento de software não customizável?" | `consultar_cnae_ibge` confirma a descrição oficial (afirmação conhecida **confirmada**) e mostra URL + timestamp |
| T02 | CNAE 6203-1/00, `licenciamento_nao_customizavel`, folha 30.000, receita 100.000, "me disseram Anexo III" | `validar_enquadramento`: compatível (`R-6203-LIC-NAO-CUSTOM`), Fator R 30% ≥ 28% → Anexo III, afirmação **confirmada** |
| T03 | "Vendo SaaS padronizado a R$ 99/mês e meu contador disse que posso usar o 6201-5/01" | Afirmação **contradita** pela regra `R-6201-SAAS`, com sugestão de 6311-9/00 / 6319-4/00 consultados no IBGE |
| T04 | CNAE real fora da base (ex.: 4711-3/02, supermercados) | IBGE encontra a descrição; a base responde `nao_encontrado`, o resultado é **sem evidência suficiente** e nada é inventado |
| T05 | "Posso usar o CNAE de desenvolvimento?" + variante com código malformado `62015` | Pedido de esclarecimento / `entrada_invalida` vinda do código |
| T06 | `IBGE_BASE_URL` apontando para host inválido (6a); `data/regras_cnae.json` ausente (6b) | 6a: IBGE `indisponivel`, ressalva explícita, conclusão só pela base. 6b: nenhum veredito, erro declarado |
| T07 | Script altera uma regra da base (backup → edição → nova sessão → restauração) | Respostas antes e depois coerentes com a mudança; os dois valores registrados |
| T08 | Jornada do T03 pela tela do app web | Ação → chamada à API → resultado com selo e evidências na tela (capturas + log do backend) |

## 12. Expansões previstas (fora da v1)

1. Cadastro fictício de empresas e a ferramenta `consultar_empresa` ("auditar a empresa X").
2. Frontend em React, consumindo o mesmo backend.
3. Cache local do IBGE com script de sincronização, marcando claramente a origem "cache".
4. Ampliação para todos os CNAEs, possivelmente com uma base gerada a partir do Anexo VI da Resolução CGSN 140/2018.
5. Deploy público.

## 13. Registro de decisões

| Decisão | Motivo |
| --- | --- |
| IBGE ao vivo **sem** fallback para cache | O T06 exige falha declarada. Um fallback automático mascararia a indisponibilidade |
| Veredito (`status_afirmacao`) calculado em código | Exigência do professor de validar em código. Elimina alucinação de veredito |
| Enum fechado de modelos de negócio + rótulos em linguagem simples | Regra determinística; o T05 fica natural; o leigo não precisa conhecer o jargão |
| Resposta em markdown + tool calls da API (sem `output_schema`) | Combinar `output_schema` com tool calling no Gemini é instável. As evidências vêm dos retornos reais |
| App web separado do AgentOS | Fronteira "projeto → API" nítida; facilita a migração para React |
| Ferramentas expostas ao agente como JSON (`como_json`) | O Agno converte `dict` com `str()`; JSON deixa o retorno legível para o modelo e para a pós-validação, e as funções originais seguem devolvendo `dict` nos testes |
| Linguagem simples, sem "parecer" | Evita que o usuário confunda a ferramenta com consultoria |

### 13.1. Erros encontrados nos rascunhos (gerados por IA) e corrigidos
- O script de sincronização esperava uma lista. A API do IBGE devolve um objeto e, para código inexistente, `[]` com HTTP 200, não 404.
- `6202-3/00` estava descrito como "consultoria" e `6203-1/00` como "customizável". As descrições corretas estão na seção 7.3.
- `6201`/`6202`/`6203` estavam como "Anexo V sujeito a Fator R". Pela LC 123, eles estão no §5º-D (Anexo III) e só passam ao V pelo §5º-M.
- A base não tinha o `6203-1/00`, embora o rascunho o indicasse como o CNAE correto para SaaS. Além disso, a nota oficial do CONCLA remete o SaaS ao `6319-4/00`, não ao `6203-1/00` (seção 7.3).
- O `6311-9/00` estava como "Anexo III sem Fator R" e o `7319-0/02` como "Anexo III", sem fundamento. Os dois têm leituras divergentes e a base agora os marca como indeterminados.
- A especificação inicial citava o "Anexo VI da Resolução CGSN 140/2018" como tabela CNAE → anexo. Esse anexo lista CNAEs impeditivos, e a fonte correta é o art. 18 da LC 123/2006.
- O vocabulário de modelos de negócio era inconsistente (`saas_puro`, `saas_padronizado`, `saas_massificado`…).
