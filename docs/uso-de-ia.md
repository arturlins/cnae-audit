# Registro de uso de IA no desenvolvimento

A atividade pede o registro do uso de IA no desenvolvimento. Este arquivo separa duas coisas:

1. **IA como componente do produto:** o modelo Gemini que roda dentro do agente (`docs/solucao.md` §6).
2. **IA como ferramenta de desenvolvimento:** assistentes usados para escrever código e documentação. É o assunto deste arquivo.

## 1. Ferramentas usadas

| Ferramenta | Uso |
| --- | --- |
| Assistente de codificação com LLM (Claude Code), dirigido pelo `AGENTS.md` | Rascunhos de código, testes, scripts e documentação, sempre a partir de instruções do autor e revisados por ele antes do commit |
| Assistentes de chat (LLM) | Rascunhos iniciais da especificação e da base de regras, que continham erros (seção 3) |

Os commits são do autor do repositório. O `AGENTS.md` proíbe coautoria de IA nos commits, para não poluir o histórico nem o `git blame`. A responsabilidade pelo conteúdo é do autor.

## 2. O que ficou com o autor

- **Recorte e decisões de produto:** público leigo, recorte tecnologia/SaaS/infoprodutos, "não é consultoria", enum fechado de modelos de negócio (`docs/solucao.md` §13).
- **Conferência da base legal:** cada `fundamento_legal` de `data/regras_cnae.json` foi conferido no texto da LC 123/2006 (Planalto), e cada descrição de CNAE na API do IBGE, em 11/11/2026. A IA não é fonte de nenhum dado do domínio.
- **Resultado esperado dos casos de teste:** definido pela inspeção da base e da API do IBGE, não pela resposta do modelo (`docs/testes.md`).
- **Revisão** de todo código gerado, com testes automatizados (`uv run pytest`) e lint (`uv run ruff check .`) antes de cada commit.

## 3. Erros da IA encontrados e corrigidos

Os rascunhos gerados por IA tinham erros de domínio. A lista completa está em `docs/solucao.md` §13.1. Os principais:

- Formato da API do IBGE assumido errado: esperava uma lista e 404, mas a API devolve um objeto e `[]` com HTTP 200 para código inexistente.
- Descrições de CNAE trocadas (6202-3/00 como "consultoria", 6203-1/00 como "customizável").
- Anexos sem fundamento: 6201/6202/6203 como "Anexo V sujeito a Fator R", quando pelo art. 18 da LC 123 estão no Anexo III (§5º-D) e só vão ao V pelo §5º-M.
- Citação do "Anexo VI da Resolução CGSN 140/2018" como tabela CNAE → anexo. Esse anexo lista CNAEs impeditivos.
- Vocabulário inconsistente para os modelos de negócio.

Durante a execução dos casos com o modelo real (`docs/testes.md` §3), o próprio agente citou códigos CNAE de exemplo que não vieram de ferramenta. A pós-validação em código (`web/verificacao.py`) bloqueou a resposta, e a instrução foi corrigida. Isso mostra por que o veredito e as checagens ficam em código, não no prompt.

## 4. Salvaguardas contra erro de IA no produto

- O veredito (`status_afirmacao`), a compatibilidade e o Fator R são calculados em Python (`agente/ferramentas/enquadramento.py`). O modelo só explica.
- O app web confere a resposta em código antes de exibi-la (`docs/solucao.md` §9.3): ferramentas executadas, seções obrigatórias, CNAEs citados com origem em ferramenta e selo vindo da ferramenta.
- Nenhum dado pessoal real e nenhuma credencial estão no repositório nem nas evidências (a chave é lida do `.env`, ignorado pelo git, e o script de casos remove a chave dos arquivos gravados).
