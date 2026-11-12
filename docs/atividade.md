# Atividade — Agente com ferramentas e validação de informações integrado ao projeto

**Disciplina:** Sistemas Inteligentes Aplicados — CESMAC  
**Modalidade:** individual ou em equipes de até **5 integrantes**, preferencialmente as mesmas do projeto.  

## 1. Desafio

Implementar um agente em **Python com Agno**, disponibilizá-lo como uma **API HTTP usando AgentOS** e integrá-lo a uma funcionalidade do projeto que vocês estão desenvolvendo.

O agente deverá utilizar **pelo menos duas ferramentas**, sendo **pelo menos uma criada pelos próprios alunos**, e acessar informações externas ao modelo para consultar dados e verificar afirmações ou solicitações do usuário. As respostas deverão apresentar evidências que permitam conferir sua correção.

Escolham uma necessidade real do projeto: verificar a situação de uma solicitação, conferir uma regra, consultar disponibilidade, validar um prazo, analisar um cadastro ou outra tarefa coerente com o produto. A atividade deve resultar em uma funcionalidade utilizável no projeto.

Ao concluir, vocês deverão conseguir explicar o caminho completo:

```text
Usuário → funcionalidade do projeto → API do AgentOS → agente Agno
                                                        ↓
                                                   ferramentas
                                                        ↓
                                               fontes externas
                                                        ↓
Usuário ← resultado no projeto ← resposta com validação e evidências
```

## 2. Requisitos obrigatórios

### 2.1. Agente Agno e API AgentOS

- Implementar ao menos um agente Agno, com objetivo, instruções e limites de atuação definidos.
- Configurar um modelo com suporte a chamadas de ferramentas e documentar o provedor e o identificador utilizados.
- Registrar o agente no AgentOS e permitir sua execução por uma requisição HTTP.
- Documentar como iniciar o serviço e apresentar ao menos um exemplo de chamada e da resposta recebida.
- Definir limites de chamadas de ferramentas e tempo de espera nas integrações, com tratamento de falhas.

O [Agno é usado para construir o agente e o AgentOS para disponibilizá-lo como serviço](https://docs.agno.com/agent-os/introduction). Executar apenas `print_response()` no terminal não atende ao requisito de API.

### 2.2. Pelo menos duas ferramentas

O agente deverá ter acesso a **duas ou mais operações distintas e úteis para a funcionalidade escolhida**. Pelo menos uma deverá ser implementada pelos alunos e conter lógica própria de consulta, cálculo, validação ou aplicação de uma regra do projeto.

A outra ferramenta pode ser criada pela equipe ou aproveitar uma integração existente do Agno, desde que seja configurada, utilizada e explicada. Uma função apenas renomeada ou copiada sem adaptação relevante não comprova a criação da ferramenta autoral.

Para cada ferramenta, documentem:

| Item | O que apresentar |
| --- | --- |
| Nome e finalidade | O que faz e em quais situações o agente deve chamá-la |
| Autoria | Se foi criada pelos alunos ou qual integração foi reutilizada |
| Entrada | Parâmetros, tipos e validações |
| Saída | Formato do resultado e significado dos campos |
| Fonte ou regra | Quais dados consulta ou qual procedimento executa |
| Falhas | Como trata entrada inválida, ausência de dados ou indisponibilidade |

As ferramentas devem estar registradas no agente e ser efetivamente acionadas por ele durante as execuções demonstradas. Chamá-las diretamente em um script separado não comprova seu uso pelo agente. A entrega deve incluir evidência de execução de **cada uma das duas ferramentas**.

Para esta atividade, a contagem considera operações expostas ao agente: um toolkit pode disponibilizar duas operações distintas. Uma busca em uma base de conhecimento também pode contar, se estiver disponível como ferramenta e houver evidência de sua execução. Duas funções que fazem a mesma coisa apenas com nomes diferentes não atendem ao objetivo.

Na implementação autoral, usem nomes claros, parâmetros tipados, docstrings e validação no código. Consultem a [documentação de funções Python como ferramentas](https://docs.agno.com/tools/creating-tools/python-functions).

### 2.3. Informações externas e verificáveis

Utilizem **ao menos uma fonte de dados persistida, externa ao prompt e ao conhecimento prévio do modelo**, relacionada ao domínio do projeto. Exemplos:

- Banco de dados, como SQLite ou PostgreSQL.
- Arquivos JSON ou CSV.
- Planilhas Excel.
- Documentos Word, PDF, Markdown ou texto.
- Dados de um serviço externo, acompanhados de um meio de reproduzir a consulta na avaliação.

**Basta escolher um dos formatos.** A fonte pode ser local e conter dados fictícios preparados pela equipe; “externa” não significa obrigatoriamente disponível na internet.

Os dados devem ser lidos pela aplicação ou recuperados de uma base de conhecimento alimentada por essa fonte. Guardar todas as respostas no prompt, retornar sempre um texto fixo ou usar apenas a memória da conversa não atende a este requisito. O banco que armazena somente sessões do AgentOS também não substitui uma fonte de informações do domínio.

Preparem dados suficientes para os casos de teste. Documentem sua origem, estrutura, versão ou data de referência e como carregá-los. O professor deve conseguir inspecionar a fonte e conferir os resultados. Se houver indexação, conversão de documentos ou cache, expliquem como atualizar os dados utilizados pelo agente.

### 2.4. Validação de informações e evidências

O agente deverá consultar a fonte para responder às perguntas do domínio e, em pelo menos um cenário, **confrontar uma informação fornecida pelo usuário com os dados disponíveis**. Apenas repetir a afirmação do usuário não é uma validação.

Exemplo: o usuário afirma que uma solicitação está aprovada. O agente consulta o registro, identifica que ela está pendente e explica a divergência com a referência correspondente.

A resposta deve apresentar, em texto ou em estrutura de dados:

1. O resultado da consulta ou verificação.
2. Se a informação foi confirmada, contradita ou se não há evidência suficiente para concluir.
3. Os dados ou trechos relevantes usados na conclusão.
4. Uma referência que permita localizar a evidência na fonte.

Exemplos de referências verificáveis:

| Fonte | Referência esperada |
| --- | --- |
| Banco de dados | Tabela e identificador do registro |
| JSON | Arquivo e chave ou identificador do objeto |
| CSV | Arquivo e identificador do registro |
| Excel | Arquivo, aba e célula, intervalo ou identificador do registro |
| Word, PDF ou texto | Arquivo, seção ou página, conforme disponível, e trecho utilizado |
| Serviço externo | Endpoint ou URL consultada, identificador e data/hora da consulta |

Quando um resultado vier de um cálculo ou de uma regra, indiquem também os dados de entrada e a regra aplicada. A validação determinística, como comparar datas, calcular valores ou conferir campos obrigatórios, deve ser implementada em código quando couber.

**Ausência de registro não significa automaticamente que uma afirmação é falsa.** O comportamento deve respeitar o significado dos dados. Se faltar informação, houver ambiguidade ou a fonte estiver indisponível, o agente deve declarar a limitação ou pedir esclarecimento, sem inventar valores, registros ou referências.

### 2.5. Integração com o projeto

Implementem uma jornada em que o próprio projeto envie uma requisição à API do AgentOS e utilize sua resposta. Por exemplo: uma tela para verificar uma informação, um assistente contextual ou uma etapa de validação em um fluxo já existente.

A integração deve:

- Estar relacionada a uma necessidade do projeto e ser acessível em sua interface ou fluxo principal.
- Chamar a API durante o uso da funcionalidade e apresentar o resultado e suas evidências ao usuário.
- Informar o estado de processamento e tratar erro ou indisponibilidade do serviço.
- Manter credenciais em variáveis de ambiente no servidor, fora do código e do navegador.

Testes com `curl`, Swagger ou a interface do AgentOS ajudam a verificar o serviço, mas **não substituem a integração com o projeto**. Documentem onde está o código que faz essa chamada e como reproduzir a jornada completa.

Se a atividade for individual ou tiver equipe diferente da equipe do projeto, identifiquem a funcionalidade entregue e a contribuição de cada participante. O vínculo com o projeto continua obrigatório.

## 3. Exemplos de recorte

Os exemplos abaixo são sugestões. Adaptem a solução ao domínio do projeto de vocês.

| Tipo de projeto | Funcionalidade do agente | Possíveis ferramentas | Fonte externa |
| --- | --- | --- | --- |
| Gestão de solicitações | Conferir situação e requisitos de um pedido | `consultar_solicitacao` e `validar_requisitos` | Banco de solicitações e regras em JSON |
| Catálogo ou estoque | Verificar disponibilidade e calcular se o estoque atende ao pedido | `consultar_produto` e `verificar_quantidade` | CSV ou banco de produtos |
| Plataforma acadêmica | Conferir um prazo alegado e explicar a regra aplicável | `consultar_calendario` e `buscar_regulamento` | JSON do calendário e regulamento em PDF |
| Gestão de eventos | Verificar vagas e elegibilidade para inscrição | `consultar_vagas` e `validar_inscricao` | Banco ou planilha de eventos e regras |

Em qualquer escolha, pelo menos uma ferramenta deverá ser autoral e as duas deverão ter uso demonstrado. Uma mesma fonte pode atender às duas ferramentas.

## 4. Roteiro de desenvolvimento

1. **Definam o recorte:** descrevam o usuário, o problema, a funcionalidade do projeto e os resultados esperados. Atualizem a especificação dessa funcionalidade.
2. **Preparem a fonte:** organizem os dados e estabeleçam como localizar e atualizar cada informação utilizada.
3. **Implementem as ferramentas:** verifiquem suas entradas, saídas e falhas antes de conectá-las ao agente.
4. **Configurem o agente e o AgentOS:** orientem quando consultar cada ferramenta, como usar as evidências e como lidar com incerteza. Testem a API.
5. **Integrem e avaliem:** conectem o projeto à API, executem os casos da próxima seção e registrem os resultados e limitações.

Vocês podem aproveitar a estrutura dos [exemplos da Aula 05](../output/aula-05/codigo/README.md), especialmente o [agente com ferramentas](../output/aula-05/codigo/02_construindo_um_agente.py) e os [exemplos de chamadas HTTP](../output/aula-05/codigo/exemplos_curl.md). A entrega deve adaptar esses conceitos ao projeto de vocês.

### Exemplo de chamada HTTP

Com o serviço em execução, adaptem o identificador do agente e a mensagem ao projeto:

```bash
curl --fail-with-body -sS \
  http://localhost:7777/agents/agente-do-projeto/runs \
  --data-urlencode 'message=A solicitação SOL-001 está aprovada? Confira na fonte e apresente a evidência.' \
  --data-urlencode 'stream=false'
```

O endpoint de execução recebe campos de formulário. Com `stream=false`, a API devolve uma resposta JSON; o resultado do agente fica em `content`. Confiram os contratos e a autenticação da versão utilizada em `/docs` e na [documentação da API do AgentOS](https://docs.agno.com/agent-os/using-the-api). Incluam na entrega um comando equivalente que funcione com o agente de vocês.

## 5. Casos de teste e evidências

Executem **pelo menos oito casos**, cobrindo os cenários abaixo. Os casos do agente devem passar pela API; o último deve partir da funcionalidade integrada no projeto.

| Caso | Cenário obrigatório | O que verificar |
| --- | --- | --- |
| T01 | Consulta que utilize a primeira ferramenta | Chamada real, parâmetros adequados, resultado correto e fonte |
| T02 | Consulta que utilize a segunda ferramenta | Chamada real, parâmetros adequados, resultado correto e fonte |
| T03 | Afirmação do usuário que contradiz um dado da fonte | Divergência identificada e correção sustentada pela evidência |
| T04 | Informação ausente na fonte | Limitação declarada, sem resposta ou referência inventada |
| T05 | Entrada inválida, incompleta ou ambígua | Validação ou pedido de esclarecimento adequado |
| T06 | Fonte ou ferramenta indisponível | Falha controlada, sem apresentar a consulta como bem-sucedida |
| T07 | Alteração de um dado na fonte | Resposta anterior e posterior coerentes com a mudança |
| T08 | Jornada completa no projeto | Ação do usuário, chamada à API e resultado com evidência na aplicação |

Incluam em T01 ou T02 uma informação conhecida que deva ser confirmada. Para T07, usem um dado de teste, registrem seu valor antes e depois e executem a mesma consulta em uma nova sessão. Atualizem índice ou cache, se necessário, conforme o procedimento documentado.

Para cada caso, registrem: entrada, resultado esperado, resultado obtido, fonte e versão utilizadas, ferramentas executadas, situação (**passou/falhou**) e link ou caminho da evidência. O resultado esperado deve ser definido pela inspeção dos dados e regras, não pela própria resposta do modelo.

As evidências podem ser respostas HTTP salvas, logs, traces ou capturas acompanhadas dos dados relevantes. Elas devem permitir relacionar a entrada à chamada da ferramenta, ao seu retorno e à resposta final. **O agente escrever “consultei a base” não comprova a consulta.** Não é necessário registrar raciocínio interno do modelo.

Registrem as falhas encontradas e as limitações ainda existentes. Se fizerem uma correção, executem novamente os casos afetados e apresentem o resultado final.

## 6. Entrega

Entreguem o link do repositório com a versão avaliada identificada por **commit ou tag**, contendo:

1. **Código do agente, das ferramentas, da API e da integração com o projeto.**
2. **Dados de demonstração**, ou script de criação/carga e instruções para obter as fontes necessárias à reprodução.
3. **Dependências e configuração:** versões fixadas ou arquivo de lock, versão do Python e `.env.example` apenas com nomes de variáveis e valores de exemplo.
4. **README de execução:** instalação, configuração, preparação dos dados, inicialização do agente e do projeto, chamada HTTP funcional e passo a passo da jornada integrada.
5. **Documentação da solução:** objetivo, especificação da funcionalidade, fluxo da arquitetura, descrição das ferramentas, fontes e estratégia de validação.
6. **Relatório dos oito casos de teste**, com resultados e evidências.
7. **Identificação dos participantes e contribuições**, além do registro de uso de IA no desenvolvimento, conforme os acordos do projeto.

Esses itens podem ser organizados na estrutura já usada pelo projeto, sem duplicar documentos. O README deve apontar onde encontrar cada um. Informem a URL do projeto e do serviço quando publicados, ou os comandos de execução local para a avaliação desta atividade. Isso não altera os acordos de publicação do [projeto integrador](../output/Guia_do_Projeto_Integrador.md).

Usem dados públicos ou fictícios e não incluam credenciais nem dados pessoais reais nos arquivos ou nas evidências. Se a solução executar operações de escrita, expliquem seus efeitos e utilizem dados de demonstração com confirmação do usuário antes de ações que alterem registros.

## 7. Demonstração e avaliação

Na demonstração, apresentem a funcionalidade dentro do projeto, comprovem o uso das duas ferramentas e mostrem uma validação com fonte e uma falha tratada. Todos os integrantes devem conseguir explicar sua contribuição, a ferramenta autoral e o caminho dos dados até a resposta.

### Rubrica da atividade

| Critério | Pontos | Evidência esperada |
| --- | ---: | --- |
| Agente Agno e API AgentOS | 15 | Agente executado por HTTP, instruções coerentes e limites configurados |
| Ferramentas | 20 | Duas operações úteis executadas pelo agente, uma autoral, com contratos e tratamento de entradas |
| Dados externos, validação e evidências | 25 | Fonte inspecionável, conclusões conferíveis e tratamento de ausência ou contradição |
| Integração com o projeto | 20 | Jornada funcional que consome a API e apresenta resultado, fontes e erros |
| Testes, documentação e reprodução | 10 | Oito cenários registrados e instruções suficientes para executar a entrega |
| Compreensão e contribuição individual | 10 | Explicação do funcionamento, das escolhas e da participação no trabalho |
| **Total** | **100** | Conversão para escala de 0 a 10: dividir o total por 10 |

Os cinco primeiros critérios avaliam a entrega; o último é atribuído a cada aluno. Na modalidade individual, o mesmo aluno responde por todos os itens. A pontuação considera o atendimento demonstrado de cada critério. A relação desta atividade com a nota da disciplina será informada pelo professor.

### Checklist antes da entrega

- [ ] O agente foi implementado em Agno e está disponível por API no AgentOS.
- [ ] Existem pelo menos duas ferramentas distintas, e uma foi criada pelos alunos.
- [ ] Há evidência de que o agente executou cada ferramenta.
- [ ] O agente consulta uma fonte persistida externa ao prompt.
- [ ] A solução valida uma informação do usuário e apresenta evidência localizável.
- [ ] Ausência de dados e falhas de consulta são tratadas sem inventar respostas.
- [ ] Uma funcionalidade do projeto consome a API e mostra o resultado ao usuário.
- [ ] Os oito casos foram executados e documentados, incluindo a atualização de dados.
- [ ] A versão entregue pode ser reproduzida a partir do README.
- [ ] Participantes, contribuições e uso de IA estão registrados, sem expor segredos.

## 8. Referências de apoio

- [Agno — Visão geral de ferramentas](https://docs.agno.com/tools/overview).
- [Agno — Funções Python como ferramentas](https://docs.agno.com/tools/creating-tools/python-functions).
- [AgentOS — Introdução](https://docs.agno.com/agent-os/introduction).
- [AgentOS — Primeiro serviço](https://docs.agno.com/agent-os/run-your-os).
- [AgentOS — Uso da API](https://docs.agno.com/agent-os/using-the-api).

Documentação consultada em **05/11/2026**. Registrem as versões efetivamente usadas e confiram a compatibilidade dos exemplos com elas. RAG, banco vetorial, MCP e múltiplos agentes são extensões possíveis; o núcleo obrigatório desta atividade é o agente Agno com AgentOS, duas ferramentas, dados verificáveis e integração ao projeto.
