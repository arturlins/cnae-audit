# AGENTS.md — Arquitetura do Sistema de Agentes e Ferramentas

## 1. Visão Geral da Arquitetura

O sistema é construído sobre a plataforma **Agno** e implementa um **Agente Auditor Especialista em Classificação Econômica (CNAE) e Enquadramento Regulatório/Tributário**.

O objetivo do agente é realizar auditoria cadastral e fiscal automatizada para a abertura e alteração de empresas no Brasil, com foco em ecossistemas de Tecnologia, Startups e Serviços Intelectuais, mantendo suporte arquitetural expansível para qualquer setor econômico (Comércio, Serviços, Indústria).

```
 ┌─────────────────────────────────────────────────────────┐
 │                   Usuário / Front-end                   │
 └────────────────────────────┬────────────────────────────┘
                              │ Requisicao HTTP
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │                Agente Auditor (Agno Framework)          │
 └──────────────┬───────────────────────────┬──────────────┘
                │                           │
  1. Dados Cadastrais            2. Regras Fiscais
                │                           │
                ▼                           ▼
 ┌─────────────────────────────┐ ┌─────────────────────────┐
 │  API Oficial IBGE (REST)    │ │ regras_tributarias.json │
 │ (https://servicodados...)   │ │ (Simples, Fator R,      │
 └──────────────┬──────────────┘ │ Risk Engine)            │
                │                └─────────────────────────┘
        (Fallback Offline)
                ▼
 ┌─────────────────────────────┐
 │    cnae_ibge.json (Cache)   │
 └─────────────────────────────┘
```

---

## 2. Abordagem Híbrida de Dados e Resiliência

Para atender com máxima segurança aos critérios da avaliação técnica e garantir altíssima disponibilidade em ambiente de produção, a arquitetura adota uma abordagem híbrida de dados:

1. **Consulta Externa em Tempo Real (IBGE API):** 
   - A ferramenta `consultar_cnae_ibge` realiza requisições HTTP REST diretas à API de Subclasses do IBGE.
   - Retorna a descrição oficial, as atividades inclusas/excluídas, a URL de origem consultada, a subclasse (identificador) e a data/hora da consulta (timestamp ISO UTC).

2. **Cache de Contingência Local (`data/cnae_ibge.json`):**
   - Caso a API externa enfrente timeout, indisponibilidade ou falha de rede (Cenário do Teste **T06**), a ferramenta alterna automaticamente para o snapshot local salvo no projeto, mantendo a operabilidade do sistema sem degradação ou alucinação.

3. **Engine Determinística Tributária (`data/regras_tributarias.json`):**
   - Armazena as regras do Simples Nacional, elegibilidade ao Fator R, cruzamento de naturezas de operação e matriz de riscos de glosa fiscal.
   - Permite alteração dinâmica direta para validação do Teste **T07**.

---

## 3. Automação de Ingestão de Dados (`scripts/sync_cnae_data.py`)

Para evitar atualizações manuais da base estática de contingência, o projeto possui um script dedicado de ingestão que consome os CNAEs cadastrados na API pública e recompõe o arquivo físico `data/cnae_ibge.json`.

### Código do Script:
```python
# scripts/sync_cnae_data.py
import json
import os
import requests

CNAES_ALVO = [
    "6201501",  # Desenvolvimento sob encomenda
    "6202300",  # Consultoria em TI
    "6203100",  # Licenciamento de software customizável
    "6204000",  # Consultoria em tecnologia da informação
    "6311900",  # Tratamento de dados, hospedagem e provedores (SaaS)
    "4751201",  # Comércio varejista especializado de informática
    "7319002",  # Promoção de vendas e marketing direto
]

def sincronizar_base_cnae():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(base_dir, "data", "cnae_ibge.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    dados_consolidados = {}
    print("Iniciando sincronização com a API oficial do IBGE...")

    for codigo in CNAES_ALVO:
        url = f"https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/{codigo}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            resultado = resp.json()
            
            if resultado and isinstance(resultado, list):
                item = resultado[0]
                dados_consolidados[codigo] = {
                    "id": item.get("id"),
                    "descricao": item.get("descricao"),
                    "atividades": item.get("atividades", []),
                    "observacoes": item.get("observacoes", [])
                }
                print(f"[OK] CNAE {codigo} sincronizado.")
        except Exception as e:
            print(f"[ERRO] Falha ao consultar {codigo}: {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dados_consolidados, f, ensure_ascii=False, indent=2)

    print(f"\nBase local atualizada com sucesso em: {output_path}")

if __name__ == "__main__":
    sincronizar_base_cnae()
```

---

## 4. Ferramentas Autorais em Python (`tools/cnae_tools.py`)

### 4.1. `consultar_cnae_ibge(codigo_cnae: str) -> dict`
- **Função:** Extrai os dados oficiais do IBGE para o código informado (higienizando a pontuação).
- **Tratamento de Erros:**
  - Código malformatado ($\neq 7$ dígitos): Retorna erro de validação.
  - Subclasse inexistente (404): Retorna `status: nao_encontrado`.
  - Timeout / Erro de Rede (5xx): Aciona o fallback transparente para o arquivo `data/cnae_ibge.json` com indicação visual de cache.

### 4.2. `validar_compatibilidade_fiscal(codigo_cnae: str, modelo_negocio: str, folha_pagamento_percentual: float = 0.0) -> dict`
- **Função:** Avalia a aderência entre a atividade descrita e o modelo de negócios operado pela empresa.
- **Lógica Determinística:**
  - Verifica lista de incompatibilidades diretas (ex.: SaaS massificado utilizando CNAE de serviço sob encomenda `6201-5/01`).
  - Calcula a regra do **Fator R**: Se folha de pagamento / faturamento bruto $\ge 28\%$, transita do Anexo V (15,5%) para o Anexo III (6%).
  - Emite alertas de risco de glosa tributária e desenquadramento fiscal.

---

## 5. Mapeamento dos Casos de Teste da Avaliação (T01 a T08)

Abaixo está o guia exato de cobertura para os testes obrigatórios descritos na especificação:

| Caso de Teste | Descrição do Teste | Comportamento Esperado do Agente | Ferramenta Utilizada |
| :--- | :--- | :--- | :--- |
| **T01** | Consulta com dado presente | Retorna descrição e atividades oficiais do CNAE informado com dados da API/IBGE. | `consultar_cnae_ibge` |
| **T02** | Consulta com regra tributária válida | Identifica o anexo do Simples Nacional correto e regras aplicáveis ao CNAE. | `validar_compatibilidade_fiscal` |
| **T03** | Contradição declarada pelo usuário | O usuário afirma que pode usar CNAE de encomenda para SaaS de prateleira. O agente refuta com base em evidências. | Ambas as ferramentas |
| **T04** | Consulta com dado ausente | Consulta código inexistente (`9999-9/99`). O agente declara que o dado não foi encontrado sem inventar informações. | `consultar_cnae_ibge` |
| **T05** | Entrada inválida / malformatada | Envio de código com menos de 7 dígitos ou caracteres inválidos. O agente aponta a inconsistência da entrada. | Validação em Python |
| **T06** | Indisponibilidade de serviço externo | Simulação de falha de conexão com a API do IBGE. O agente aciona o fallback local de contingência mantendo o serviço. | Tracing `try/except` |
| **T07** | Alteração dinâmica da fonte de dados | Alteração do anexo no `data/regras_tributarias.json` de Anexo III para Anexo V. A resposta do agente atualiza na sessão seguinte. | `validar_compatibilidade_fiscal` |
| **T08** | Jornada completa de ponta a ponta | Interação do usuário via interface HTTP/Front-end executando o fluxo completo de auditoria com exibição de evidências e timestamps. | Rota do AgentOS |