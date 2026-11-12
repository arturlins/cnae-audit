# Ferramentas do agente

As duas ferramentas são **autorais**: funções Python registradas no agente Agno `verificador-cnae`. O Agno usa a docstring e as anotações de tipo como descrição e esquema para o modelo. Nenhuma das duas lança exceção para o agente: o resultado é sempre um `dict` com `status`.

Testes: `uv run pytest tests/test_ibge.py tests/test_enquadramento.py`.

## 1. `consultar_cnae_ibge` — `agente/ferramentas/ibge.py`

| Item | Descrição |
| --- | --- |
| **Nome e finalidade** | Busca a descrição **oficial** de uma subclasse CNAE na API do IBGE. O agente deve chamá-la para todo CNAE citado pelo usuário ou sugerido por `validar_enquadramento`, para mostrar o que a subclasse compreende |
| **Autoria** | Autoral. Usa `httpx` para HTTP. Lógica própria: normalização e validação do código, interpretação do formato real da API (inclusive o `[]` para código inexistente), classificação de falhas, resumo das observações e montagem da evidência |
| **Entrada** | `codigo_cnae: str`, com 7 dígitos em qualquer formato usual (`6201-5/01`, `6201501`, `62.01-5-01`). Só aceita dígitos e os separadores `. - /` e espaço. Precisa ter exatamente 7 dígitos |
| **Saída** | `status: "ok"` traz `codigo` (`NNNN-N/NN`), `descricao`, `hierarquia` (seção/divisão/grupo/classe), `observacoes` (até 3, resumidas) e `evidencia {fonte, url, consultado_em (ISO UTC)}` |
| **Fonte ou regra** | `GET {IBGE_BASE_URL}/subclasses/{7 dígitos}` (padrão `https://servicodados.ibge.gov.br/api/v2/cnae`), sem cache |
| **Falhas** | Formato inválido: `entrada_invalida`, sem chamar a API. Resposta `[]`: `nao_encontrado`. Timeout (`IBGE_TIMEOUT_S`, padrão 5 s), erro de rede, HTTP ≠ 200, corpo que não é JSON ou JSON com `id` diferente do pedido: `indisponivel`. Todos os casos de falha vêm com `mensagem` e **sem dados**, e a evidência mostra a URL tentada |

## 2. `validar_enquadramento` — `agente/ferramentas/enquadramento.py`

| Item | Descrição |
| --- | --- |
| **Nome e finalidade** | Motor de regras determinístico. Verifica se o CNAE combina com o modelo de negócio, apura o anexo do Simples Nacional (com Fator R) e confronta o que o usuário ouviu. O agente deve chamá-la depois de `consultar_cnae_ibge` sempre que houver um modelo de negócio identificado |
| **Autoria** | Autoral |
| **Entrada** | `codigo_cnae: str` (mesma validação acima). `modelo_negocio: str`, que precisa estar no enum de `modelos_negocio` da base (14 valores). `folha_12m: float \| None` (≥ 0) e `receita_bruta_12m: float \| None` (> 0), que devem vir juntos. `afirmacao_compativel: bool \| None`. `anexo_afirmado: str \| None` (`I`–`V`, aceita `"Anexo III"` ou `"3"`) |
| **Saída** | `status`, `codigo`, `denominacao`, `modelo_negocio {valor, rotulo}`, `compatibilidade` (`compativel` / `incompativel` / `indeterminado`), `regra_aplicada`, `motivo`, `cnaes_sugeridos[]`, `tributacao {anexo_resultante, situacao, confianca, sujeito_fator_r, nota, calculo_fator_r{folha_12m, receita_bruta_12m, razao, razao_percentual, limiar, regra, anexo_resultante}}`, `status_afirmacao` (`confirmada` / `contradita` / `sem_evidencia_suficiente`), `comparacao[] {campo, afirmado, apurado, resultado}`, `fundamento_legal[] {id, norma, dispositivo, trecho, url}`, `evidencia {arquivo, chave, chave_tributacao, versao, data_referencia}` e `aviso` |
| **Fonte ou regra** | `data/regras_cnae.json`, relido a cada chamada. Regras: (1) compatibilidade pela regra do par CNAE/modelo, e sem regra o resultado é `indeterminado`; (2) Fator R `folha_12m / receita_bruta_12m` comparado com 28% (LC 123/2006, art. 18, §§ 5º-J e 5º-M, folha conforme § 24), com o anexo do CNAE para cada faixa; (3) `status_afirmacao`: `contradita` se algum campo afirmado diverge, `confirmada` se todos conferem, `sem_evidencia_suficiente` nos demais casos; (4) sugestões: CNAEs da base com regra `compativel` para o mesmo modelo |
| **Falhas** | CNAE malformado, modelo fora do enum (devolve `valores_validos` com rótulos), número negativo, não numérico ou só um dos dois valores, receita zero, anexo inválido ou afirmação não booleana: `entrada_invalida` com `campo`. CNAE fora da base: `nao_encontrado`, com `compatibilidade: indeterminado`, porque ausência não é incompatibilidade. Base ausente, JSON inválido ou estrutura sem as chaves obrigatórias: `erro_fonte`, **sem veredito**. CNAE com tributação em zona cinzenta: `anexo_resultante: null` e nota, sem inventar anexo |

## 3. Por que o veredito é calculado em código

O `status_afirmacao` (que vira o selo "confere / não confere" na tela) e o anexo são calculados pela ferramenta. As instruções do agente proíbem alterar esses valores, e o app web mostra o selo a partir do retorno da ferramenta, não do texto do modelo. Assim, a conclusão pode ser conferida: os dados de entrada, a regra aplicada e a referência na base aparecem no retorno.
