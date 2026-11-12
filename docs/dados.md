# Fontes de dados

> Material de referência. Os dados são simplificados para fins didáticos e não substituem a consulta a um contador ou advogado.

O agente usa duas fontes externas ao modelo e ao prompt:

| Fonte | Tipo | Ferramenta | Referência devolvida |
| --- | --- | --- | --- |
| `data/regras_cnae.json` | Arquivo JSON persistido no repositório | `validar_enquadramento` | arquivo + chave (`cnaes.<código>.regras[id=<regra>]`) + versão + data de referência |
| API CNAE do IBGE | Serviço externo público, sem autenticação | `consultar_cnae_ibge` | URL consultada + data/hora UTC |

## 1. Base de regras `data/regras_cnae.json`

- **Versão:** `1.0.0`. **Data de referência:** 2026-11-11.
- **Origem:** elaborada para este projeto a partir de três fontes:
  - descrições e notas oficiais "compreende / não compreende" da CNAE 2.3 (IBGE/CONCLA), obtidas pela API do IBGE;
  - texto vigente da Lei Complementar nº 123/2006, art. 18 ([Planalto](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm));
  - análise do autor sobre a compatibilidade entre CNAE e modelo de negócio.
- **Natureza dos dados:** a base legal é verídica. As conclusões de compatibilidade são uma simplificação didática, e os valores usados nos testes (folha, receita, afirmações) são fictícios. Não há dados pessoais.

### 1.1. Estrutura

| Chave | Conteúdo |
| --- | --- |
| `versao`, `data_referencia`, `aviso`, `descricao` | Metadados. O `aviso` é repassado em toda resposta da ferramenta |
| `fontes_legais.<id>` | `norma`, `dispositivo`, `trecho` (literal ou paráfrase indicada), `url` |
| `modelos_negocio.<valor>` | `rotulo` em linguagem simples (é o mesmo texto que aparece no formulário) |
| `cnaes.<NNNN-N/NN>.denominacao` | Denominação oficial |
| `cnaes.<código>.tributacao` | `sujeito_fator_r` (`true` / `false` / `null` = indeterminado), `anexo` (quando fixo), `anexo_fator_r_alto` / `anexo_fator_r_baixo` (quando há Fator R), `confianca` (`alta` / `media` / `indeterminada`), `fundamentos` (ids de `fontes_legais`), `nota` |
| `cnaes.<código>.regras[]` | `id` único, `modelo_negocio`, `resultado` (`compativel` / `incompativel` / `indeterminado`), `motivo` em linguagem simples |

**Semântica:**
- Combinação de CNAE e modelo sem regra resulta em `indeterminado`, porque ausência de regra não significa incompatibilidade.
- CNAE fora da base resulta em `nao_encontrado`.
- Os CNAEs sugeridos são calculados a partir das regras `compativel` do mesmo modelo de negócio.

### 1.2. Conteúdo

Os 12 CNAEs, os anexos e o nível de confiança de cada um estão em [`solucao.md` §7.3](solucao.md#73-recorte-de-cnaes-e-base-legal). São 14 modelos de negócio e 46 regras.

**Fora do recorte:**
- `5811-5/00` (edição de livros): o anexo depende de a atividade ser tratada como industrialização ou serviço, e isso não pôde ser fundamentado com segurança.
- `5819-1/00`: trata de cadastros e listas, não de e-books.

O modelo `ebook_publicacao_digital` fica coberto apenas pela regra `R-6319-EBOOK`, que é incompatível porque a nota oficial do CONCLA exclui a edição de livros do 6319-4/00.

### 1.3. Como atualizar

1. Edite `data/regras_cnae.json`. Ao mudar regras ou fundamentos, aumente `versao` e atualize `data_referencia`.
2. Rode `uv run pytest tests/test_base_regras.py`. Os testes de integridade conferem:
   - formato dos códigos;
   - ids únicos;
   - no máximo uma regra por par CNAE/modelo;
   - enum válido;
   - fundamentos existentes;
   - coerência entre Fator R e anexo.
3. Não há índice nem cache. A ferramenta relê o arquivo a cada chamada, então a mudança vale na próxima execução do agente, sem reiniciar o AgentOS (é isso que o T07 demonstra).

Para usar outra base, por exemplo em testes, defina `REGRAS_PATH`.

## 2. API CNAE do IBGE

- **Endpoint:** `GET {IBGE_BASE_URL}/subclasses/{7 dígitos}`. Padrão: `IBGE_BASE_URL=https://servicodados.ibge.gov.br/api/v2/cnae`.
- **Timeout:** `IBGE_TIMEOUT_S`, padrão 5 s. Não há cache: toda consulta vai à API.
- **Comportamento verificado em 2026-11-11:**
  - código existente: HTTP 200 com objeto (`id`, `descricao`, hierarquia em `classe`, `observacoes`, `atividades`);
  - código inexistente: HTTP 200 com `[]`.
- **Reprodução manual:** `curl https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/6201501`.
- **Simular indisponibilidade (T06):** inicie o AgentOS com `IBGE_BASE_URL=http://ibge-indisponivel.invalid`.
