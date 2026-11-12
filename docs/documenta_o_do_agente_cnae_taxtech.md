# TaxTech CNAE Audit Agent — Especificação e Arquitetura do Agente

**Disciplina:** Sistemas Inteligentes Aplicados — CESMAC  
**Projeto:** Auditor Inteligente de Enquadramento Tributário e CNAE para Startups de Software  
**Framework Agente:** Agno  
**Serviço de API:** AgentOS  

---

## 1. Visão Geral do Projeto

O **TaxTech CNAE Audit Agent** é um agente inteligente projetado para auditar o enquadramento fiscal e a escolha de códigos CNAE (Classificação Nacional de Atividades Econômicas) para empresas de tecnologia, com foco em startups de Software as a Service (SaaS).

Um dos maiores riscos operacionais e tributários enfrentados por founders de tecnologia é o uso inadequado de CNAEs de desenvolvimento sob encomenda (como o `6201-5/01`) para comercializar software padronizado via assinatura (SaaS). Essa incompatibilidade gera autuações fiscais por desenquadramento do Simples Nacional, cobrança retroativa de ISS/IRPJ e multas elevadas pela Receita Federal e Fazendas Municipais.

Este agente consulta uma base persistida de regras fiscais (`cnae_regras.json`), aciona ferramentas autorais para validar a compatibilidade entre o modelo de negócio declarado pelo usuário e o enquadramento regulatório, e emite um parecer fundamentado com referências auditáveis e evidências explícitas.

---

## 2. Fluxo da Arquitetura e Integração

O agente opera totalmente integrado à infraestrutura do projeto através do AgentOS via requisições HTTP REST.

```text
[ Usuário na Interface Web (Frontend) ]
                  │
                  ▼ (POST /agents/cnae-audit-agent/runs)
         [ API do AgentOS ]
                  │
                  ▼
         [ Agente Agno (Python) ]
         │       │
         │       ├──► Tool 1 (Autoral): consultar_cnae(codigo_cnae)
         │       │          └─► [ Arquivo Local: data/cnae_regras.json ]
         │       │
         │       └──► Tool 2 (Autoral): validar_compatibilidade_cnae(codigo_cnae, modelo_negocio, permite_customizacao)
         │                  └─► [ Motor de Regras Determinístico em Python ]
                  │
                  ▼ (Resposta Estruturada com Evidências e Referências)
[ Usuário recebe Parecer com Status: CONFIRMADO / CONTRADITO / INDETERMINADO ]
```

---

## 3. Especificação do Agente Agno

### 3.1. Identificador do Agente
* **ID no AgentOS:** `cnae-audit-agent`
* **Modelo LLM:** Configurado com suporte nativo a chamadas de função (ex: OpenAI `gpt-4o-mini` ou Groq `llama-3.3-70b-versatile`).

### 3.2. Instruções do Sistema (System Prompt)
```text
Você é um Auditor Tributário Especializado em Empresas de Tecnologia e Startups (TaxTech Agent).
Seu objetivo é verificar se a escolha de CNAE informada ou pretendida pelo usuário é adequada ao modelo de negócio da empresa (SaaS padronizado, software sob encomenda, suporte, hospedagem, etc.).

REGRAS DE ATUAÇÃO E SEGURANÇA:
1. NUNCA invente dados, códigos CNAE ou alíquotas. Toda informação fiscal deve vir obrigatoriamente das ferramentas.
2. Em QUALQUER análise de afirmação do usuário, você DEVE acionar as ferramentas 'consultar_cnae' e 'validar_compatibilidade_cnae'.
3. Se o usuário fizer uma afirmação sobre enquadramento (ex: "Posso usar o CNAE X para meu SaaS"), você deve confrontá-la diretamente contra a base de dados.
4. Sua resposta FINAL deve sempre conter a estrutura rígida de evidências:
   - Resultado da Consulta/Validação;
   - Status da Afirmação: [CONFIRMADO], [CONTRADITO] ou [SEM EVIDÊNCIA SUFICIENTE];
   - Resumo das Regras Aplicadas;
   - Referência Auditável (Arquivo local, chave/ID do registro consultado).
5. Se uma ferramenta retornar erro ou dados ausentes, declare explicitamente a limitação do sistema. Não tente adivinhar.
```

### 3.3. Configurações de Limites e Resiliência
* **Max Tool Calls:** 4 chamadas por execução.
* **Timeout por Integração:** 5.0 segundos.
* **Tratamento de Falhas:** Caso o arquivo JSON esteja inacessível ou o código CNAE não exista, o agente reporta status `INDETERMINADO` e orienta a verificação da base.

---

## 4. Especificação das Ferramentas (Tools)

### 4.1. Ferramenta 1: `consultar_cnae`
* **Autoria:** Autoral (Alunos).
* **Finalidade:** Busca os detalhes regulatórios e tributários de um código CNAE específico na base persistida.
* **Entrada:** `codigo_cnae` (string, ex: `"6201-5/01"` ou `"6203-1/00"`).
* **Saída:** Objeto JSON contendo denominação, descrição oficial, modelos permitidos, modelos vedados, anexo do Simples Nacional e nível de risco para SaaS.
* **Fonte:** `data/cnae_regras.json`.
* **Tratamento de Falhas:** Retorna formato estruturado com `status: "nao_encontrado"` caso a chave não exista, impedindo alucinação do modelo.

### 4.2. Ferramenta 2: `validar_compatibilidade_cnae`
* **Autoria:** Autoral (Alunos).
* **Finalidade:** Aplica a regra determinística de enquadramento fiscal confrontando o CNAE com o modelo de negócio e nível de customização do software.
* **Entrada:** 
  * `codigo_cnae` (string);
  * `modelo_negocio` (string, ex: `"saas_padronizado"`, `"sob_encomenda"`, `"suporte"`);
  * `permite_customizacao` (boolean).
* **Saída:** Objeto JSON com `compativel` (boolean), `nivel_risco_fiscal` (string: `"BAIXO"`, `"MEDIO"`, `"CRITICO"`), `motivo_tecnico` (string) e `tributacao_sugerida` (string).
* **Regra Aplicada:** Se `modelo_negocio == "saas_padronizado"` e `codigo_cnae == "6201-5/01"`, o retorno é obrigatoriamente `compativel: false` com risco `"CRITICO"`, pois SaaS não customizável exige enquadramento em `6203-1/00` ou `6311-9/00`.

---

## 5. Estratégia de Validação e Evidências (Requisito 2.4)

Quando o usuário submete uma afirmação (ex: *"Vou lançar um SaaS multi-tenant e meu contador disse que posso usar o CNAE 6201-5/01 no Simples Nacional"*), o agente deve obrigatoriamente estruturar a resposta da seguinte forma:

1. **Resultado da Validação:** Declaração nítida de inadequação fiscal.
2. **Status:** `[CONTRADITO]`
3. **Dados e Regras Utilizadas:** 
   - CNAE Consultado: `6201-5/01` (Desenvolvimento sob encomenda).
   - Conflito: O CNAE `6201-5/01` veda expressamente a comercialização de software de prateleira/SaaS sem cessão de código fonte ou sem customização exclusiva.
   - CNAE Correto Indicado: `6203-1/00` (Edição/Licenciamento de software não-customizável).
4. **Referência Auditável:** `data/cnae_regras.json` -> Registro `"6201-5/01"` e Registro `"6203-1/00"`.

---

## 6. Roteiro dos 8 Casos de Teste (Evidências para Seção 5 da Atividade)

| Caso | Cenário Testado | Entrada (Mensagem do Usuário) | Resultado Esperado | Ferramenta Utilizada | Status Esperado |
| --- | --- | --- | --- | --- | --- |
| **T01** | Consulta simples (Tool 1) | "Quais são as regras e tributação do CNAE 6203-1/00?" | Detalhes do CNAE de software não-customizável e anexo do Simples | `consultar_cnae` | PASSOU |
| **T02** | Validação técnica (Tool 2) | "Quero saber se o CNAE 6311-9/00 é compatível com um SaaS de infraestrutura cloud." | Confirmação de compatibilidade com risco BAIXO | `validar_compatibilidade_cnae` | PASSOU |
| **T03** | Afirmação contraditória do usuário | "Vou vender um SaaS padronizado por R$ 99/mês usando o CNAE 6201-5/01." | Identificar contradição, apontar risco crítico de autuação fiscal e citar a referência do JSON | Ambas as ferramentas | PASSOU |
| **T04** | Informação ausente na fonte | "O CNAE 9999-9/99 serve para meu SaaS?" | Declarar que o CNAE não consta na base de dados, sem inventar regras | `consultar_cnae` | PASSOU |
| **T05** | Entrada inválida / ambígua | "Posso usar o CNAE de desenvolvimento?" | Solicitar esclarecimento ou código numérico exato do CNAE | Nenhuma / Validação de entrada | PASSOU |
| **T06** | Indisponibilidade da fonte | *(Simulada renomeando data/cnae_regras.json)* "Verifique o CNAE 6201-5/01" | Retorno de erro controlado sem inventar resposta | `consultar_cnae` (com tratamento de exceção) | PASSOU |
| **T07** | Alteração reativa da fonte | *(Muda-se anexo do Simples no JSON e repete-se a consulta T01)* | Exibir os novos dados alterados na nova sessão | `consultar_cnae` | PASSOU |
| **T08** | Jornada completa via Frontend | Interação real na tela do projeto disparando requisição HTTP para a API | Apresentação do parecer fiscal com evidências na interface do usuário | Ambas (via AgentOS HTTP API) | PASSOU |

---

## 7. Instruções de Execução da API AgentOS

### 7.1. Inicialização do Serviço AgentOS
```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Iniciar o servidor de agentes na porta 7777
python app.py
```

### 7.2. Exemplo de Chamada HTTP REST (curl)
```bash
curl --fail-with-body -sS \
  http://localhost:7777/agents/cnae-audit-agent/runs \
  --data-urlencode 'message=Meu contador quer colocar o CNAE 6201-5/01 no meu SaaS de gestão financeira. Isso está correto? Confirme na base e apresente as evidências.' \
  --data-urlencode 'stream=false'
```