# PRD - Camada Analitica dbt | Jornada de Dados

## Contexto

Projeto dbt para criar uma camada analitica sobre um banco PostgreSQL de e-commerce.
Arquitetura Medalhao com Bronze, Silver conformada, Gold dimensional e Gold marts finais.
Banco: PostgreSQL (Supabase). Dialeto SQL: PostgreSQL.

---

## Tabelas Fonte (Raw)

As 4 tabelas fonte estao no schema `public` do PostgreSQL. Sao referenciadas via `{{ source('raw', 'nome_tabela') }}`.

### raw.vendas

Transacoes de venda realizadas.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_venda | int | PK - ID unico da venda |
| data_venda | timestamp | Data e hora da venda |
| id_cliente | int | FK -> clientes.id_cliente |
| id_produto | int | FK -> produtos.id_produto |
| canal_venda | varchar | Canal de venda (ex: ecommerce, loja_fisica) |
| quantidade | int | Quantidade de itens vendidos |
| preco_unitario | numeric | Preco unitario praticado na venda |

### raw.clientes

Cadastro de clientes.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_cliente | int | PK - ID unico do cliente |
| nome_cliente | varchar | Nome completo do cliente |
| estado | varchar | Estado (UF) do cliente |
| pais | varchar | Pais do cliente |
| data_cadastro | timestamp | Data de cadastro |

### raw.produtos

Catalogo de produtos.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_produto | int | PK - ID unico do produto |
| nome_produto | varchar | Nome do produto |
| categoria | varchar | Categoria do produto |
| marca | varchar | Marca do produto |
| preco_atual | numeric | Preco atual de venda |
| data_criacao | timestamp | Data de criacao do produto |

### raw.preco_competidores

Precos coletados de concorrentes para os mesmos produtos.

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| id_produto | int | FK -> produtos.id_produto |
| nome_concorrente | varchar | Nome do concorrente |
| preco_concorrente | numeric | Preco praticado pelo concorrente |
| data_coleta | timestamp | Data e hora da coleta do preco |

---

## Arquitetura

```text
models/
  _sources.yml
  bronze/          -> 4 models (view), copia fiel das fontes
  silver/          -> 4 models (table), dados limpos e conformados
  gold/
    dimensional/   -> dimensoes e fatos reutilizaveis
    marts/         -> data marts finais por area
```

### Configuracao dbt_project.yml

```yaml
models:
  ecommerce:
    bronze:
      +materialized: view
      +schema: bronze
    silver:
      +materialized: table
      +schema: silver
    gold:
      +materialized: table
      dimensional:
        +schema: gold
      marts:
        sales:
          +schema: gold_sales
        customer_success:
          +schema: gold_cs
        pricing:
          +schema: gold_pricing

vars:
  segmentacao_vip_threshold: 10000
  segmentacao_top_tier_threshold: 5000
```
---

## Exemplo completo: ETL de Vendas

Os 3 modelos abaixo mostram o fluxo completo para a tabela de vendas. Use como referencia para criar os demais.

### bronze_vendas.sql

```sql
SELECT
    id_venda,
    data_venda,
    id_cliente,
    id_produto,
    canal_venda,
    quantidade,
    preco_unitario
FROM {{ source('raw', 'vendas') }}
```

### silver_vendas.sql

```sql
SELECT
    v.id_venda,
    v.id_cliente,
    v.id_produto,
    v.quantidade,
    v.preco_unitario AS preco_venda,
    v.data_venda,
    v.canal_venda,
    v.quantidade * v.preco_unitario AS receita_total,
    DATE(v.data_venda::timestamp) AS data_venda_date,
    EXTRACT(YEAR FROM v.data_venda::timestamp) AS ano_venda,
    EXTRACT(MONTH FROM v.data_venda::timestamp) AS mes_venda,
    EXTRACT(DAY FROM v.data_venda::timestamp) AS dia_venda,
    EXTRACT(DOW FROM v.data_venda::timestamp) AS dia_semana,
    EXTRACT(HOUR FROM v.data_venda::timestamp) AS hora_venda
FROM {{ ref('bronze_vendas') }} v
```

### gold_sales_vendas_temporais.sql (gold/marts/sales/)

```sql
SELECT
    f.data_venda,
    d.ano AS ano_venda,
    d.mes AS mes_venda,
    d.dia AS dia_venda,
    d.dia_semana_nome AS dia_da_semana,
    f.hora_venda,
    SUM(f.receita_total) AS receita_total,
    SUM(f.quantidade) AS quantidade_total,
    COUNT(DISTINCT f.id_venda) AS total_vendas,
    COUNT(DISTINCT f.id_cliente) AS total_clientes_unicos,
    AVG(f.receita_total) AS ticket_medio
FROM {{ ref('gold_fct_vendas') }} f
LEFT JOIN {{ ref('gold_dim_datas') }} d
    ON f.data_venda = d.data
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY data_venda DESC, f.hora_venda
```

---

## Modelos restantes a criar

### Camada Bronze

**Objetivo:** Copia exata das tabelas raw. Sem transformacao. Serve como contrato do dado.
**Materializacao:** view
**Regra:** SELECT explicito de todas as colunas da fonte. Sem WHERE, sem CAST, sem transformacao.
**Referencia:** Usar `{{ source('raw', 'nome_tabela') }}`

#### bronze_clientes.sql
- Fonte: `{{ source('raw', 'clientes') }}`
- Colunas: id_cliente, nome_cliente, estado, pais, data_cadastro

#### bronze_produtos.sql
- Fonte: `{{ source('raw', 'produtos') }}`
- Colunas: id_produto, nome_produto, categoria, marca, preco_atual, data_criacao

#### bronze_preco_competidores.sql
- Fonte: `{{ source('raw', 'preco_competidores') }}`
- Colunas: id_produto, nome_concorrente, preco_concorrente, data_coleta

---

## Camada Silver

**Objetivo:** transformar Bronze em dados limpos, tipados, deduplicados e conformados para consumo pela Gold.
**Materializacao:** table

**Regras gerais:**
- Cada entidade Silver deve ter grao claro e chave unica testada.
- Deduplicar por chave natural: `id_cliente`, `id_produto`, `id_venda` e `id_produto + concorrente + data_da_coleta`.
- Padronizar textos com `trim`, caixa consistente e marcador `NAO_INFORMADO` para atributos descritivos ausentes.
- Corrigir tipos em Silver: ids como texto, datas como `timestamp`/`date`, precos como `numeric(10,2)` e quantidades como inteiro.
- Filtrar linhas com chaves, datas ou medidas criticas invalidas.
- Preservar fatos validos: se vendas ou precos referenciam produtos ausentes no catalogo, criar produto inferido em `silver_produtos` com `status_cadastro = 'INFERIDO'`.
- Declarar testes de qualidade em `models/silver/_silver_models.yml`.

### Modelos Silver

#### silver_clientes.sql
- Fonte: `{{ ref('bronze_clientes') }}`
- Grao: 1 linha por `id_cliente`
- Tratamentos: trim, UF em maiusculo, pais capitalizado, deduplicacao por cadastro mais recente.

#### silver_produtos.sql
- Fontes: `{{ ref('bronze_produtos') }}`, `{{ ref('bronze_vendas') }}` e `{{ ref('bronze_preco_competidores') }}`
- Grao: 1 linha por `id_produto`
- Tratamentos: trim, categoria/marca em maiusculo, `faixa_preco`, `status_cadastro` (`CADASTRADO` ou `INFERIDO`) e produtos inferidos para manter integridade referencial.

#### silver_vendas.sql
- Fonte: `{{ ref('bronze_vendas') }}`
- Grao: 1 linha por `id_venda`
- Tratamentos: tipos, canal padronizado, deduplicacao, filtro de chaves/datas/medidas invalidas, `receita_total` e dimensoes temporais.

#### silver_preco_competidores.sql
- Fonte: `{{ ref('bronze_preco_competidores') }}`
- Grao: 1 linha por `id_produto + nome_concorrente + data_da_coleta`
- Tratamentos: tipos, concorrente padronizado, chave tecnica `preco_competidor_key`, deduplicacao e filtro de medidas invalidas.

---

## Camada Gold

**Objetivo:** modelar dados conformados em dimensoes, fatos e marts finais para analise.
**Materializacao:** table

### Gold dimensional

- `gold_dim_clientes`: dimensao de clientes baseada em `silver_clientes`.
- `gold_dim_produtos`: dimensao de produtos baseada em `silver_produtos`, incluindo `status_cadastro`.
- `gold_dim_datas`: dimensao de datas unificada para vendas e coletas de preco.
- `gold_dim_concorrentes`: dimensao de concorrentes com chave tecnica deterministica.
- `gold_fct_vendas`: fato principal, uma linha por `id_venda`.
- `gold_fct_precos_competidores`: fato auxiliar de pricing por produto, concorrente e data.

### Gold marts finais

#### gold_sales_vendas_temporais.sql
- Pasta: `models/gold/marts/sales/`
- Fontes: `{{ ref('gold_fct_vendas') }}` e `{{ ref('gold_dim_datas') }}`
- Pergunta de negocio: desempenho temporal de vendas.

#### gold_customer_success_clientes_segmentacao.sql
- Pasta: `models/gold/marts/customer_success/`
- Fontes: `{{ ref('gold_fct_vendas') }}` e `{{ ref('gold_dim_clientes') }}`
- Pergunta de negocio: melhores clientes por receita e comportamento de compra.
- Usa `segmentacao_vip_threshold` e `segmentacao_top_tier_threshold`.

#### gold_pricing_precos_competitividade.sql
- Pasta: `models/gold/marts/pricing/`
- Fontes: `{{ ref('gold_dim_produtos') }}`, `{{ ref('gold_fct_precos_competidores') }}`, `{{ ref('gold_dim_concorrentes') }}` e `{{ ref('gold_fct_vendas') }}`
- Pergunta de negocio: competitividade de precos contra concorrentes.
- Usa `COALESCE` para vendas agregadas ausentes e mantem a classificacao de preco por regra de negocio.

### Testes

- Contratos Silver: `models/silver/_silver_models.yml`.
- Contratos Gold: `models/gold/_gold_models.yml`.
- Testes principais: `unique`, `not_null`, `accepted_values` e `relationships`.
---

## Arquivo _sources.yml

Criar em `models/_sources.yml`. Definir as 4 tabelas fonte com source name `raw`, schema `public`, e documentar todas as colunas de cada tabela conforme descrito na secao "Tabelas Fonte".

---

## Resumo de Entrega

| Camada | Modelos | Materializacao | Regra principal |
|--------|---------|----------------|-----------------|
| Bronze | 4 | view | SELECT explicito da fonte, sem transformacao |
| Silver | 4 | table | Dados limpos, tipados, deduplicados e conformados |
| Gold | 9 | table | Dimensoes, fatos e marts finais para analise |

**Total: 17 modelos SQL + 2 arquivos de contratos de modelos + 1 _sources.yml + 1 dbt_project.yml**

