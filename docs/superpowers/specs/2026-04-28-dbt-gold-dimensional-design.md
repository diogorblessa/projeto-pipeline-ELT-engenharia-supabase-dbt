# Reestruturacao da camada Gold dbt - Design

**Data:** 2026-04-28
**Escopo:** camada de transformacao dbt em `transform/`, com foco em Gold dimensional, data marts finais, testes dbt e atualizacao das referencias documentais para os cases 01 e 02.

---

## 1. Contexto

O projeto implementa um pipeline ELT de e-commerce:

```text
Supabase Storage S3 -> extract_load -> PostgreSQL/Supabase public -> dbt transform
```

A etapa dbt ja usa arquitetura medalhao:

```text
bronze -> silver -> gold
```

Estado atual da camada Gold:

```text
transform/models/gold/
  sales/
    vendas_temporais.sql
  customer_success/
    clientes_segmentacao.sql
  pricing/
    precos_competitividade.sql
```

Esses tres modelos sao data marts agregados por pergunta de negocio. Eles atendem ao consumo inicial, mas ainda nao deixam explicita uma base dimensional reutilizavel para os proximos projetos (`case-01-dashboard` e `case-02-telegram`).

---

## 2. Objetivos

1. Reestruturar a camada Gold para separar modelos dimensionais reutilizaveis de data marts finais.
2. Criar uma modelagem estrela simples e bem definida na camada Gold.
3. Padronizar os nomes dos modelos Gold com prefixo `gold_*`, em linha com `bronze_*` e `silver_*`.
4. Renomear os data marts finais para nomes `gold_*`, sem aliases legados.
5. Atualizar todos os arquivos que mencionam os modelos Gold para manter congruencia antes dos cases 01 e 02.
6. Declarar chaves e relacionamentos via testes dbt, priorizando contratos de dados sobre constraints fisicas no PostgreSQL.

---

## 3. Nao objetivos

- Alterar a etapa Extract + Load.
- Criar ou implementar os cases 01 e 02 agora.
- Criar migrations relacionais para PK/FK fisicas no PostgreSQL.
- Introduzir snowflake modeling neste momento.
- Criar snapshots, seeds ou incremental models.
- Manter compatibilidade com os nomes antigos dos data marts Gold.

---

## 4. Decisoes consolidadas

| # | Decisao | Motivo |
|---|---|---|
| 1 | Usar a opcao B: Gold dimensional moderada | Melhora a arquitetura sem transformar o projeto em um warehouse complexo demais |
| 2 | Criar `gold/dimensional/` e `gold/marts/<setor>/` | Separa fatos/dimensoes reutilizaveis dos modelos finais de consumo |
| 3 | Renomear todos os modelos Gold para `gold_*` | Mantem consistencia com `bronze_*` e `silver_*` |
| 4 | Atualizar consumidores/docs para os novos nomes | Evita referencias quebradas nos proximos cases |
| 5 | Usar estrela, nao snowflake | O dataset e pequeno e os consumidores precisam de consultas simples |
| 6 | Declarar chaves por testes dbt | dbt valida contratos; constraints fisicas ficam fora de escopo |
| 7 | Incluir `gold_dim_concorrentes` | Deixa pricing mais correto: concorrente vira dimensao, nao texto solto na fato |
| 8 | Criar duas fatos: vendas e precos de concorrentes | Vendas e a fato central; precos concorrentes sao medicoes de pricing ao longo do tempo |

---

## 5. Arquitetura alvo

### 5.1 Estrutura de pastas

```text
transform/models/
  _sources.yml
  bronze/
    bronze_clientes.sql
    bronze_preco_competidores.sql
    bronze_produtos.sql
    bronze_vendas.sql
  silver/
    silver_clientes.sql
    silver_preco_competidores.sql
    silver_produtos.sql
    silver_vendas.sql
  gold/
    dimensional/
      gold_dim_clientes.sql
      gold_dim_produtos.sql
      gold_dim_datas.sql
      gold_dim_concorrentes.sql
      gold_fct_vendas.sql
      gold_fct_precos_competidores.sql
    marts/
      sales/
        gold_sales_vendas_temporais.sql
      customer_success/
        gold_customer_success_clientes_segmentacao.sql
      pricing/
        gold_pricing_precos_competitividade.sql
    _gold_models.yml
```

### 5.2 Schemas no PostgreSQL

O `dbt_project.yml` deve mapear os subdiretorios Gold para schemas analiticos claros:

```text
gold/dimensional/        -> public_gold
gold/marts/sales/        -> public_gold_sales
gold/marts/customer_success/ -> public_gold_cs
gold/marts/pricing/      -> public_gold_pricing
```

Tabelas finais esperadas:

```text
public_gold.gold_dim_clientes
public_gold.gold_dim_produtos
public_gold.gold_dim_datas
public_gold.gold_dim_concorrentes
public_gold.gold_fct_vendas
public_gold.gold_fct_precos_competidores

public_gold_sales.gold_sales_vendas_temporais
public_gold_cs.gold_customer_success_clientes_segmentacao
public_gold_pricing.gold_pricing_precos_competitividade
```

---

## 6. Modelagem dimensional

### 6.1 Estrela de vendas

```text
gold_dim_clientes
gold_dim_produtos
gold_dim_datas
        \       |       /
         \      |      /
          gold_fct_vendas
```

`gold_fct_vendas` e a fato principal do projeto.

Grao:

```text
1 linha por id_venda
```

Medidas:

```text
quantidade
preco_unitario
receita_total
```

Chaves:

```text
id_venda
id_cliente
id_produto
data_venda
```

### 6.2 Estrela de pricing

```text
gold_dim_produtos
gold_dim_concorrentes
gold_dim_datas
        \       |       /
         \      |      /
   gold_fct_precos_competidores
```

`gold_fct_precos_competidores` e uma fato auxiliar de pricing. Ela nao substitui vendas. Ela registra medicoes de preco observadas por produto, concorrente e data.

Grao:

```text
1 linha por id_produto + concorrente_key + data_da_coleta
```

Medidas:

```text
preco_concorrente
```

Chaves:

```text
preco_competidor_key
id_produto
concorrente_key
data_da_coleta
```

### 6.3 Por que nao snowflake

Snowflake separaria dimensoes em tabelas menores, por exemplo:

```text
gold_dim_produtos -> gold_dim_categorias -> gold_dim_marcas
```

Isso nao e necessario agora porque:

- existem poucas fontes e poucas entidades;
- categorias e marcas sao atributos simples de produto;
- os consumidores previstos sao dashboard e agente de relatorio;
- mais tabelas aumentariam joins e manutencao sem ganho claro.

Portanto, a escolha correta para este estagio e estrela simples na camada Gold.

---

## 7. Modelos Gold dimensionais

### 7.1 `gold_dim_clientes`

Fonte:

```text
silver_clientes
```

Grao:

```text
1 linha por id_cliente
```

Colunas principais:

```text
id_cliente
nome_cliente
estado
pais
data_cadastro
```

### 7.2 `gold_dim_produtos`

Fonte:

```text
silver_produtos
```

Grao:

```text
1 linha por id_produto
```

Colunas principais:

```text
id_produto
nome_produto
categoria
marca
preco_atual
faixa_preco
data_criacao
```

### 7.3 `gold_dim_datas`

Fonte:

```text
silver_vendas.data_da_venda
silver_preco_competidores.data_da_coleta
```

Grao:

```text
1 linha por data
```

Colunas principais:

```text
data
ano
mes
dia
dia_semana
dia_semana_nome
```

Observacao: a dimensao de datas deve unir as datas relevantes de vendas e de coletas de preco para atender as duas fatos.

### 7.4 `gold_dim_concorrentes`

Fonte:

```text
silver_preco_competidores
```

Grao:

```text
1 linha por concorrente
```

Colunas principais:

```text
concorrente_key
nome_concorrente
```

`concorrente_key` deve ser uma chave tecnica deterministica baseada no nome normalizado do concorrente. Exemplo conceitual:

```sql
md5(lower(trim(nome_concorrente)))
```

### 7.5 `gold_fct_vendas`

Fonte:

```text
silver_vendas
```

Grao:

```text
1 linha por id_venda
```

Colunas principais:

```text
id_venda
id_cliente
id_produto
data_venda
canal_venda
quantidade
preco_unitario
receita_total
hora_venda
```

`data_venda` deve se relacionar com `gold_dim_datas.data`.

### 7.6 `gold_fct_precos_competidores`

Fonte:

```text
silver_preco_competidores
```

Grao:

```text
1 linha por id_produto + concorrente_key + data_da_coleta
```

Colunas principais:

```text
preco_competidor_key
id_produto
concorrente_key
data_da_coleta
preco_concorrente
```

`preco_competidor_key` deve ser uma chave tecnica deterministica da combinacao:

```text
id_produto + concorrente_key + data_da_coleta
```

---

## 8. Data marts finais

### 8.1 `gold_sales_vendas_temporais`

Objetivo:

```text
Analise temporal de vendas para diretoria comercial.
```

Fontes:

```text
gold_fct_vendas
gold_dim_datas
```

Mantem a logica atual de vendas temporais, mas passa a consumir a fato e a dimensao de datas.

### 8.2 `gold_customer_success_clientes_segmentacao`

Objetivo:

```text
Segmentacao de clientes por receita e comportamento de compra.
```

Fontes:

```text
gold_fct_vendas
gold_dim_clientes
```

Mantem as regras de `VIP`, `TOP_TIER` e `REGULAR` via vars dbt:

```text
segmentacao_vip_threshold
segmentacao_top_tier_threshold
```

### 8.3 `gold_pricing_precos_competitividade`

Objetivo:

```text
Analise de competitividade de preco contra concorrentes.
```

Fontes:

```text
gold_fct_precos_competidores
gold_dim_produtos
gold_dim_concorrentes
gold_fct_vendas
```

O mart deve:

- calcular preco medio, minimo e maximo dos concorrentes por produto;
- contar concorrentes distintos;
- classificar o preco atual contra a concorrencia;
- enriquecer com receita e quantidade vendida por produto vindas de `gold_fct_vendas`.

---

## 9. Chaves, relacionamentos e testes dbt

### 9.1 Estrategia

As chaves devem ser declaradas como testes dbt em `transform/models/gold/_gold_models.yml`.

Nao criar PK/FK fisicas no PostgreSQL nesta etapa porque:

- dbt e responsavel por construir e validar modelos analiticos;
- constraints fisicas exigiriam gestao de migracoes fora do escopo;
- testes dbt ja dao feedback objetivo no pipeline com `dbt test`.

### 9.2 Testes esperados

Dimensoes:

```text
gold_dim_clientes.id_cliente: unique, not_null
gold_dim_produtos.id_produto: unique, not_null
gold_dim_datas.data: unique, not_null
gold_dim_concorrentes.concorrente_key: unique, not_null
```

Fato de vendas:

```text
gold_fct_vendas.id_venda: unique, not_null
gold_fct_vendas.id_cliente: relationships -> gold_dim_clientes.id_cliente
gold_fct_vendas.id_produto: relationships -> gold_dim_produtos.id_produto
gold_fct_vendas.data_venda: relationships -> gold_dim_datas.data
```

Fato de precos:

```text
gold_fct_precos_competidores.preco_competidor_key: unique, not_null
gold_fct_precos_competidores.id_produto: relationships -> gold_dim_produtos.id_produto
gold_fct_precos_competidores.concorrente_key: relationships -> gold_dim_concorrentes.concorrente_key
gold_fct_precos_competidores.data_da_coleta: relationships -> gold_dim_datas.data
```

Marts finais:

```text
gold_sales_vendas_temporais.data_venda: not_null
gold_customer_success_clientes_segmentacao.cliente_id: unique, not_null
gold_pricing_precos_competitividade.produto_id: unique, not_null
```

---

## 10. Atualizacoes documentais e referencias

Como os nomes antigos serao removidos, estes arquivos devem ser atualizados:

```text
README.md
CLAUDE.md
transform/PRD-dbt.md
.llm/database.md
.llm/case-01-dashboard/feature.md
.llm/case-01-dashboard/PRD-dashboard.md
.llm/case-02-telegram/PRD-agente-relatorios.md
docs/superpowers/plans/2026-04-28-reorganizacao-elt.md
docs/superpowers/specs/2026-04-28-reorganizacao-elt-design.md
```

Padrao antigo a substituir:

```text
public_gold_sales.vendas_temporais
public_gold_cs.clientes_segmentacao
public_gold_pricing.precos_competitividade
```

Padrao novo:

```text
public_gold_sales.gold_sales_vendas_temporais
public_gold_cs.gold_customer_success_clientes_segmentacao
public_gold_pricing.gold_pricing_precos_competitividade
```

Tambem atualizar descricoes de arquitetura para mencionar:

```text
public_gold.gold_dim_*
public_gold.gold_fct_*
```

---

## 11. Alteracoes esperadas no `dbt_project.yml`

Configurar a nova hierarquia Gold:

```yaml
models:
  ecommerce:
    gold:
      +materialized: table
      +tags: ["gold"]
      +meta:
        modeling_layer: gold
      dimensional:
        +schema: gold
        +tags: ["gold", "dimensional"]
      marts:
        +tags: ["gold", "mart"]
        sales:
          +schema: gold_sales
        customer_success:
          +schema: gold_cs
        pricing:
          +schema: gold_pricing
```

As tags especificas de KPI/metrics podem ficar nos marts finais. Os modelos dimensionais devem ser identificados por `dimensional`, `dimension` ou `fact` conforme o modelo.

---

## 12. Fluxo de dados alvo

```text
public raw tables
  -> bronze_* views
  -> silver_* tables
  -> public_gold.gold_dim_*
  -> public_gold.gold_fct_*
  -> public_gold_sales.gold_sales_vendas_temporais
  -> public_gold_cs.gold_customer_success_clientes_segmentacao
  -> public_gold_pricing.gold_pricing_precos_competitividade
```

Os cases 01 e 02 devem consumir apenas os marts finais, salvo necessidade explicita de analise exploratoria. A base dimensional fica disponivel para extensao e auditoria.

---

## 13. Riscos e mitigacoes

| Risco | Impacto | Mitigacao |
|---|---|---|
| Renomear os marts quebra referencias antigas | Alto | Atualizar docs e arquivos `.llm` na mesma mudanca |
| `gold_dim_datas` nao cobrir datas de pricing | Medio | Unir datas de vendas e coletas de preco |
| Chave tecnica de concorrente mudar por variacao de texto | Medio | Normalizar com `lower(trim(nome_concorrente))` |
| Duplicidade em preco por produto/concorrente/data | Medio | Validar `preco_competidor_key` como `unique + not_null` |
| Mais modelos aumentam complexidade | Medio | Manter estrela simples, sem snowflake e sem intermediate layer neste momento |
| Testes dbt falharem por dados raw inconsistentes | Medio | Tratar como feedback de qualidade; nao mascarar com filtros silenciosos |

---

## 14. Criterios de aceite

1. `dbt parse` executa sem erro.
2. `dbt run` cria os modelos Bronze, Silver, Gold dimensional e Gold marts.
3. `dbt test` valida chaves e relacionamentos definidos em `_gold_models.yml`.
4. Nao existem mais modelos Gold finais com os nomes antigos:
   - `vendas_temporais`
   - `clientes_segmentacao`
   - `precos_competitividade`
5. Os novos marts finais existem com nomes `gold_*`.
6. `README.md`, `CLAUDE.md`, `transform/PRD-dbt.md` e `.llm/*` mencionam os novos nomes.
7. Os proximos cases usam:
   - `public_gold_sales.gold_sales_vendas_temporais`
   - `public_gold_cs.gold_customer_success_clientes_segmentacao`
   - `public_gold_pricing.gold_pricing_precos_competitividade`

---

## 15. Proxima etapa

Apos aprovacao desta spec, a proxima etapa e criar um plano de implementacao detalhado com ordem segura:

1. Criar modelos dimensionais.
2. Mover e renomear data marts.
3. Atualizar `dbt_project.yml`.
4. Criar `_gold_models.yml` com testes.
5. Atualizar documentacao e referencias `.llm`.
6. Rodar validacoes dbt.

