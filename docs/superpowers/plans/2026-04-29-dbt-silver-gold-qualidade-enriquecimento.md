# dbt Silver/Gold — Qualidade e Enriquecimento Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar 8 melhorias de qualidade e enriquecimento nas camadas Silver e Gold do pipeline dbt, corrigindo contratos, tipos, regras de negócio e enriquecendo dimensões e marts.

**Architecture:** Duas fases independentes por camada — Fase 1 valida completamente a Silver antes de tocar a Gold. Cada task produz um commit atômico e verificável via `dbt parse` + `dbt run` + `dbt test`.

**Tech Stack:** dbt (PostgreSQL/Supabase), uv workspace, Jinja2. Prefixo de todos os comandos dbt: `uv run --package transform dbt --project-dir transform --profiles-dir transform`

---

## Mapa de Arquivos

### Fase 1 — Silver

| Arquivo | Tasks |
|---------|-------|
| `transform/models/silver/_silver_models.yml` | 1, 5 |
| `transform/models/silver/silver_vendas.sql` | 2, 3, 4, 5 |
| `transform/models/silver/silver_clientes.sql` | 5 |
| `transform/models/silver/silver_produtos.sql` | 3, 5 |
| `transform/models/silver/silver_preco_competidores.sql` | 4, 5 |
| `transform/dbt_project.yml` | 3 |

### Fase 2 — Gold

| Arquivo | Tasks |
|---------|-------|
| `transform/models/gold/dimensional/gold_dim_datas.sql` | 7 |
| `transform/models/gold/marts/customer_success/gold_customer_success_clientes_segmentacao.sql` | 8 |
| `transform/models/gold/marts/pricing/gold_pricing_precos_competitividade.sql` | 9 |
| `transform/models/gold/_gold_models.yml` | 9 |
| `transform/dbt_project.yml` | 8 |

---

## Fase 1 — Silver

### Task 1: Corrigir accepted_values de canal_venda

**Files:**
- Modify: `transform/models/silver/_silver_models.yml`

- [ ] **Step 1: Localizar o bloco de canal_venda no YAML**

Em `transform/models/silver/_silver_models.yml`, modelo `silver_vendas`, coluna `canal_venda` (próximo à linha 88):

```yaml
      - name: canal_venda
        description: "Canal de venda padronizado."
        tests:
          - not_null
          - accepted_values:
              values: ['ecommerce', 'loja_fisica']
```

- [ ] **Step 2: Adicionar 'NAO_INFORMADO' aos valores aceitos**

```yaml
      - name: canal_venda
        description: "Canal de venda padronizado."
        tests:
          - not_null
          - accepted_values:
              values: ['ecommerce', 'loja_fisica', 'NAO_INFORMADO']
```

- [ ] **Step 3: Verificar sintaxe**

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```
Esperado: `Done.`

- [ ] **Step 4: Rodar testes do modelo**

```bash
uv run --package transform dbt test --project-dir transform --profiles-dir transform -s silver_vendas
```
Esperado: todos os testes passam.

- [ ] **Step 5: Commit**

```bash
git add transform/models/silver/_silver_models.yml
git commit -m "fix(silver): add NAO_INFORMADO to canal_venda accepted_values

O SQL produz 'NAO_INFORMADO' via COALESCE quando canal_venda e nulo.
O contrato YAML nao incluia esse valor, causando falha de teste para
vendas sem canal identificado. NAO_INFORMADO e um estado valido de
negocio, nao dado corrompido."
```

---

### Task 2: Converter hora_venda de string para integer

**Files:**
- Modify: `transform/models/silver/silver_vendas.sql`

- [ ] **Step 1: Localizar a linha de hora_venda**

Em `transform/models/silver/silver_vendas.sql`, no SELECT final, linha 51:

```sql
    TO_CHAR(data_venda, 'HH24:MI') AS hora_venda
```

- [ ] **Step 2: Substituir por EXTRACT(HOUR)**

```sql
    EXTRACT(HOUR FROM data_venda)::integer AS hora_venda
```

Contexto completo das linhas finais do SELECT após a mudança:

```sql
    DATE(data_venda) AS data_da_venda,
    EXTRACT(YEAR FROM data_venda) AS ano_venda,
    EXTRACT(MONTH FROM data_venda) AS mes_venda,
    EXTRACT(DAY FROM data_venda) AS dia_venda,
    EXTRACT(DOW FROM data_venda) AS dia_semana,
    EXTRACT(HOUR FROM data_venda)::integer AS hora_venda
FROM vendas_validas
WHERE ordem = 1
```

- [ ] **Step 3: Verificar sintaxe**

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```
Esperado: `Done.`

- [ ] **Step 4: Materializar**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s silver_vendas --full-refresh
```
Esperado: `1 of 1 OK created sql table model silver.silver_vendas`

- [ ] **Step 5: Verificar tipo e range**

```sql
SELECT DISTINCT hora_venda FROM silver.silver_vendas ORDER BY 1;
-- Esperado: inteiros entre 0 e 23 (sem strings como '14:30')
```

- [ ] **Step 6: Rodar testes**

```bash
uv run --package transform dbt test --project-dir transform --profiles-dir transform -s silver_vendas
```
Esperado: todos os testes passam.

- [ ] **Step 7: Commit**

```bash
git add transform/models/silver/silver_vendas.sql
git commit -m "fix(silver): convert hora_venda from string to integer (hour of day)

TO_CHAR produzia string 'HH24:MI' sem suporte a aritmetica nem sort
numerico correto. GROUP BY hora_venda no mart criava ate 1440 grupos
por dia. EXTRACT(HOUR)::integer agrupa por hora cheia (0-23), maximo
24 linhas por dia. Breaking change para consumers do mart de vendas."
```

---

### Task 3: Mover thresholds de faixa_preco para vars

**Files:**
- Modify: `transform/dbt_project.yml`
- Modify: `transform/models/silver/silver_vendas.sql` *(assume Task 2 já aplicada)*
- Modify: `transform/models/silver/silver_produtos.sql`

- [ ] **Step 1: Adicionar vars em dbt_project.yml**

Localizar a seção `vars:` (linhas 61-64). Substituir:

```yaml
vars:
  segmentacao_vip_threshold: 10000    # Receita minima para cliente VIP
  segmentacao_top_tier_threshold: 5000 # Receita minima para TOP_TIER
```

Por:

```yaml
vars:
  segmentacao_vip_threshold: 10000
  segmentacao_top_tier_threshold: 5000
  faixa_venda_barato_max: 100
  faixa_venda_medio_max: 500
  faixa_produto_premium_min: 1000
  faixa_produto_medio_min: 500
```

- [ ] **Step 2: Atualizar CASE em silver_vendas.sql**

Localizar o CASE de faixa_preco (linhas 41-45):

```sql
    CASE
        WHEN preco_unitario < 100 THEN 'barato'
        WHEN preco_unitario <= 500 THEN 'medio'
        ELSE 'caro'
    END AS faixa_preco,
```

Substituir por:

```sql
    CASE
        WHEN preco_unitario < {{ var('faixa_venda_barato_max', 100) }} THEN 'barato'
        WHEN preco_unitario <= {{ var('faixa_venda_medio_max', 500) }} THEN 'medio'
        ELSE 'caro'
    END AS faixa_preco,
```

- [ ] **Step 3: Atualizar CASE em silver_produtos.sql**

Localizar o CASE de faixa_preco na CTE `produtos_cadastrados` (linhas 31-37):

```sql
        CASE
            WHEN preco_atual IS NULL THEN 'NAO_INFORMADO'
            WHEN preco_atual > 1000 THEN 'PREMIUM'
            WHEN preco_atual > 500 THEN 'MEDIO'
            ELSE 'BASICO'
        END AS faixa_preco,
```

Substituir por:

```sql
        CASE
            WHEN preco_atual IS NULL                                         THEN 'NAO_INFORMADO'
            WHEN preco_atual > {{ var('faixa_produto_premium_min', 1000) }} THEN 'PREMIUM'
            WHEN preco_atual > {{ var('faixa_produto_medio_min', 500) }}    THEN 'MEDIO'
            ELSE 'BASICO'
        END AS faixa_preco,
```

- [ ] **Step 4: Verificar sintaxe**

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```
Esperado: `Done.`

- [ ] **Step 5: Materializar e verificar comportamento idêntico**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s silver_vendas silver_produtos --full-refresh
```
Esperado: `2 of 2 OK`

```bash
uv run --package transform dbt test --project-dir transform --profiles-dir transform -s silver_vendas silver_produtos
```
Esperado: todos os testes passam (distribuição de faixa_preco idêntica com defaults).

- [ ] **Step 6: Commit**

```bash
git add transform/dbt_project.yml transform/models/silver/silver_vendas.sql transform/models/silver/silver_produtos.sql
git commit -m "refactor(silver): move faixa_preco thresholds to dbt vars

Valores de corte para classificacao de preco estavam hardcoded no SQL.
Configurados agora via vars no dbt_project.yml com defaults identicos
aos valores anteriores — sem mudanca de comportamento no run padrao.
Permite ajuste de regra de negocio sem editar SQL."
```

---

### Task 4: Aplicar regra preco > 0

**Files:**
- Modify: `transform/models/silver/silver_vendas.sql` *(assume Tasks 2 e 3 já aplicadas)*
- Modify: `transform/models/silver/silver_preco_competidores.sql`

- [ ] **Step 1: Atualizar filtro em silver_vendas.sql**

No bloco WHERE da CTE `vendas_validas` (linhas 24-30), alterar a última condição:

```sql
-- antes
      AND preco_unitario >= 0
-- depois
      AND preco_unitario > 0
```

O bloco WHERE completo após a mudança:

```sql
    WHERE id_venda IS NOT NULL
      AND id_cliente IS NOT NULL
      AND id_produto IS NOT NULL
      AND data_venda IS NOT NULL
      AND quantidade > 0
      AND preco_unitario > 0
```

- [ ] **Step 2: Atualizar filtro em silver_preco_competidores.sql**

No bloco WHERE da CTE `precos_validos` (linhas 28-34), alterar a última condição:

```sql
-- antes
      AND preco_concorrente >= 0
-- depois
      AND preco_concorrente > 0
```

O bloco WHERE completo após a mudança:

```sql
    WHERE id_produto IS NOT NULL
      AND nome_concorrente <> 'NAO_INFORMADO'
      AND data_da_coleta IS NOT NULL
      AND preco_concorrente > 0
```

- [ ] **Step 3: Verificar sintaxe**

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```
Esperado: `Done.`

- [ ] **Step 4: Materializar**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s silver_vendas silver_preco_competidores --full-refresh
```
Esperado: `2 of 2 OK`

- [ ] **Step 5: Verificar que preco zero foi excluído**

```sql
SELECT COUNT(*) FROM silver.silver_vendas WHERE preco_unitario = 0;
-- Esperado: 0

SELECT COUNT(*) FROM silver.silver_preco_competidores WHERE preco_concorrente = 0;
-- Esperado: 0
```

- [ ] **Step 6: Rodar testes**

```bash
uv run --package transform dbt test --project-dir transform --profiles-dir transform -s silver_vendas silver_preco_competidores
```
Esperado: todos os testes passam.

- [ ] **Step 7: Commit**

```bash
git add transform/models/silver/silver_vendas.sql transform/models/silver/silver_preco_competidores.sql
git commit -m "fix(silver): enforce preco > 0 em vendas e preco_competidores

Preco zero e invalido neste dominio — nao existem produtos gratuitos.
A regra anterior (>= 0) permitia registros com preco zero que
contaminavam calculos de receita e competitividade. Se promocoes
gratuitas forem introduzidas no futuro, rever explicitamente."
```

---

### Task 5: Adicionar coluna de auditoria silver_processado_em

**Files:**
- Modify: `transform/models/silver/silver_vendas.sql` *(assume Tasks 2, 3 e 4 já aplicadas)*
- Modify: `transform/models/silver/silver_clientes.sql`
- Modify: `transform/models/silver/silver_produtos.sql`
- Modify: `transform/models/silver/silver_preco_competidores.sql`
- Modify: `transform/models/silver/_silver_models.yml`

- [ ] **Step 1: Adicionar coluna em silver_vendas.sql**

No SELECT final, adicionar `current_timestamp AS silver_processado_em` como última coluna antes do `FROM`:

```sql
    EXTRACT(HOUR FROM data_venda)::integer AS hora_venda,
    current_timestamp AS silver_processado_em
FROM vendas_validas
WHERE ordem = 1
```

- [ ] **Step 2: Adicionar coluna em silver_clientes.sql**

O SELECT final está nas linhas 22-29. Adicionar após `data_cadastro`:

```sql
SELECT
    id_cliente,
    nome_cliente,
    estado,
    pais,
    data_cadastro,
    current_timestamp AS silver_processado_em
FROM clientes_deduplicados
WHERE ordem = 1
```

- [ ] **Step 3: Adicionar coluna em silver_produtos.sql**

O SELECT final usa UNION ALL entre `produtos_cadastrados` e `produtos_inferidos`. Adicionar a coluna em ambos os lados:

```sql
SELECT
    id_produto,
    nome_produto,
    categoria,
    marca,
    preco_atual,
    data_criacao,
    faixa_preco,
    status_cadastro,
    current_timestamp AS silver_processado_em
FROM produtos_cadastrados

UNION ALL

SELECT
    id_produto,
    nome_produto,
    categoria,
    marca,
    preco_atual,
    data_criacao,
    faixa_preco,
    status_cadastro,
    current_timestamp AS silver_processado_em
FROM produtos_inferidos
```

- [ ] **Step 4: Adicionar coluna em silver_preco_competidores.sql**

No SELECT final (linhas 36-44), adicionar após `data_da_coleta`:

```sql
SELECT
    preco_competidor_key,
    id_produto,
    nome_concorrente,
    preco_concorrente,
    data_coleta,
    data_da_coleta,
    current_timestamp AS silver_processado_em
FROM precos_validos
WHERE ordem = 1
```

- [ ] **Step 5: Documentar a coluna em _silver_models.yml**

Adicionar a entrada abaixo em cada um dos 4 modelos (`silver_vendas`, `silver_clientes`, `silver_produtos`, `silver_preco_competidores`). Para `silver_vendas`, inserir após o bloco de `receita_total`. Para os demais, inserir após a última coluna existente:

```yaml
      - name: silver_processado_em
        description: "Timestamp de quando o dbt materializou esta tabela (auditoria de pipeline)."
```

- [ ] **Step 6: Verificar sintaxe**

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```
Esperado: `Done.`

- [ ] **Step 7: Materializar todos os modelos Silver**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s tag:silver --full-refresh
```
Esperado: `4 of 4 OK`

- [ ] **Step 8: Verificar que a coluna existe em todos os modelos**

```sql
SELECT silver_processado_em FROM silver.silver_vendas LIMIT 1;
SELECT silver_processado_em FROM silver.silver_clientes LIMIT 1;
SELECT silver_processado_em FROM silver.silver_produtos LIMIT 1;
SELECT silver_processado_em FROM silver.silver_preco_competidores LIMIT 1;
-- Esperado: timestamp atual em todas as queries
```

- [ ] **Step 9: Commit**

```bash
git add transform/models/silver/
git commit -m "feat(silver): add silver_processado_em audit column to all silver tables

Registra o timestamp em que o dbt materializou cada tabela Silver.
Permite detectar pipelines parados via MAX(silver_processado_em) e
rastrear qual run produziu cada versao dos dados."
```

---

### Task 6: Validar Fase 1 — Silver completa

**Files:** nenhum (validação)

- [ ] **Step 1: Rodar todos os modelos Silver**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s tag:silver --full-refresh
```
Esperado: `4 of 4 OK created sql table model`

- [ ] **Step 2: Rodar todos os testes Silver**

```bash
uv run --package transform dbt test --project-dir transform --profiles-dir transform -s tag:silver
```
Esperado: zero warnings, zero errors. Se algum teste falhar, resolver antes de avançar para Fase 2.

---

## Fase 2 — Gold

### Task 7: Enriquecer gold_dim_datas com atributos de calendário

**Files:**
- Modify: `transform/models/gold/dimensional/gold_dim_datas.sql`

- [ ] **Step 1: Substituir o conteúdo completo do arquivo**

```sql
WITH datas_unificadas AS (
    SELECT
        v.data_da_venda AS data
    FROM {{ ref('silver_vendas') }} v

    UNION

    SELECT
        pc.data_da_coleta AS data
    FROM {{ ref('silver_preco_competidores') }} pc
),

datas_validas AS (
    SELECT DISTINCT
        data
    FROM datas_unificadas
    WHERE data IS NOT NULL
)

SELECT
    data,
    EXTRACT(YEAR FROM data::timestamp)                      AS ano,
    EXTRACT(MONTH FROM data::timestamp)                     AS mes,
    EXTRACT(DAY FROM data::timestamp)                       AS dia,
    EXTRACT(DOW FROM data::timestamp)                       AS dia_semana,
    CASE EXTRACT(DOW FROM data::timestamp)
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda'
        WHEN 2 THEN 'Terca'
        WHEN 3 THEN 'Quarta'
        WHEN 4 THEN 'Quinta'
        WHEN 5 THEN 'Sexta'
        WHEN 6 THEN 'Sabado'
    END                                                     AS dia_semana_nome,
    EXTRACT(QUARTER FROM data::timestamp)::integer          AS trimestre,
    TO_CHAR(data::timestamp, 'TMMonth')                     AS nome_mes,
    EXTRACT(WEEK FROM data::timestamp)::integer             AS numero_semana,
    EXTRACT(DOW FROM data::timestamp) IN (0, 6)             AS is_fim_de_semana,
    data = date_trunc('month', data::timestamp)::date       AS is_primeiro_dia_mes
FROM datas_validas
```

Nota: `ORDER BY data` removido — desnecessário em materialização TABLE e não garante ordem para consumers.

- [ ] **Step 2: Verificar sintaxe**

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```
Esperado: `Done.`

- [ ] **Step 3: Materializar**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s gold_dim_datas --full-refresh
```
Esperado: `1 of 1 OK`

- [ ] **Step 4: Verificar novos atributos**

```sql
SELECT data, trimestre, nome_mes, numero_semana, is_fim_de_semana, is_primeiro_dia_mes
FROM public_gold.gold_dim_datas
ORDER BY data
LIMIT 10;
-- Esperado: trimestre 1-4, nome_mes em texto, is_fim_de_semana = true para sab/dom,
--           is_primeiro_dia_mes = true apenas no dia 1 de cada mes
```

- [ ] **Step 5: Rodar testes**

```bash
uv run --package transform dbt test --project-dir transform --profiles-dir transform -s gold_dim_datas
```
Esperado: testes `unique` e `not_null` em `data` passam.

- [ ] **Step 6: Commit**

```bash
git add transform/models/gold/dimensional/gold_dim_datas.sql
git commit -m "feat(gold): enrich gold_dim_datas with calendar attributes

Adiciona trimestre, nome_mes, numero_semana, is_fim_de_semana e
is_primeiro_dia_mes. Colunas derivadas puras de 'data', sem quebra de
contratos existentes. Remove ORDER BY no SELECT final — nao garante
ordem em TABLE e adiciona custo desnecessario na materializacao."
```

---

### Task 8: Adicionar var data_referencia_cs ao mart de Customer Success

**Files:**
- Modify: `transform/dbt_project.yml`
- Modify: `transform/models/gold/marts/customer_success/gold_customer_success_clientes_segmentacao.sql`

- [ ] **Step 1: Adicionar var em dbt_project.yml**

Na seção `vars:`, adicionar após `faixa_produto_medio_min`:

```yaml
vars:
  segmentacao_vip_threshold: 10000
  segmentacao_top_tier_threshold: 5000
  faixa_venda_barato_max: 100
  faixa_venda_medio_max: 500
  faixa_produto_premium_min: 1000
  faixa_produto_medio_min: 500
  data_referencia_cs: null
```

- [ ] **Step 2: Adicionar filtro Jinja condicional na CTE receita_por_cliente**

Localizar o `FROM {{ ref('gold_fct_vendas') }} f` seguido do `LEFT JOIN`. Adicionar o bloco Jinja entre o FROM e o LEFT JOIN:

```sql
WITH receita_por_cliente AS (
    SELECT
        f.id_cliente,
        c.nome_cliente,
        c.estado,
        SUM(f.receita_total) AS receita_total,
        COUNT(DISTINCT f.id_venda) AS total_compras,
        AVG(f.receita_total) AS ticket_medio,
        MIN(f.data_venda) AS primeira_compra,
        MAX(f.data_venda) AS ultima_compra
    FROM {{ ref('gold_fct_vendas') }} f
    LEFT JOIN {{ ref('gold_dim_clientes') }} c
        ON f.id_cliente = c.id_cliente
    {% if var('data_referencia_cs', none) is not none %}
    WHERE f.data_venda <= '{{ var("data_referencia_cs") }}'::date
    {% endif %}
    GROUP BY f.id_cliente, c.nome_cliente, c.estado
)
```

- [ ] **Step 3: Verificar sintaxe**

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```
Esperado: `Done.`

- [ ] **Step 4: Materializar sem var (comportamento all-time — deve ser idêntico ao anterior)**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s gold_customer_success_clientes_segmentacao --full-refresh
```
Esperado: `1 of 1 OK`

- [ ] **Step 5: Verificar filtro com var de data**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s gold_customer_success_clientes_segmentacao --full-refresh --vars '{data_referencia_cs: "2024-06-30"}'
```
Esperado: `1 of 1 OK`

```sql
SELECT MAX(ultima_compra) FROM public_gold_cs.gold_customer_success_clientes_segmentacao;
-- Esperado: data <= '2024-06-30'
```

- [ ] **Step 6: Restaurar estado all-time**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s gold_customer_success_clientes_segmentacao --full-refresh
```

- [ ] **Step 7: Commit**

```bash
git add transform/dbt_project.yml transform/models/gold/marts/customer_success/gold_customer_success_clientes_segmentacao.sql
git commit -m "feat(gold): add data_referencia_cs var to CS segmentation mart

Mart de segmentacao agregava vendas de todos os tempos sem possibilidade
de analise historica pontual. Nova var data_referencia_cs (default null
= all-time) permite calcular segmentacao em qualquer data passada sem
alterar o modelo."
```

---

### Task 9: Corrigir mart de Pricing — flag sem_dados e classificacao NULL-safe

**Files:**
- Modify: `transform/models/gold/marts/pricing/gold_pricing_precos_competitividade.sql`
- Modify: `transform/models/gold/_gold_models.yml`

- [ ] **Step 1: Substituir o conteúdo completo do arquivo pricing**

```sql
WITH precos_por_produto AS (
    SELECT
        p.id_produto,
        p.nome_produto,
        p.categoria,
        p.marca,
        p.preco_atual AS nosso_preco,
        AVG(fp.preco_concorrente) AS preco_medio_concorrentes,
        MIN(fp.preco_concorrente) AS preco_minimo_concorrentes,
        MAX(fp.preco_concorrente) AS preco_maximo_concorrentes,
        COUNT(DISTINCT fp.concorrente_key) AS total_concorrentes
    FROM {{ ref('gold_dim_produtos') }} p
    LEFT JOIN {{ ref('gold_fct_precos_competidores') }} fp
        ON p.id_produto = fp.id_produto
    LEFT JOIN {{ ref('gold_dim_concorrentes') }} c
        ON fp.concorrente_key = c.concorrente_key
    GROUP BY p.id_produto, p.nome_produto, p.categoria, p.marca, p.preco_atual
),

vendas_por_produto AS (
    SELECT
        f.id_produto,
        SUM(f.receita_total) AS receita_total,
        SUM(f.quantidade) AS quantidade_total
    FROM {{ ref('gold_fct_vendas') }} f
    GROUP BY f.id_produto
)

SELECT
    pp.id_produto AS produto_id,
    pp.nome_produto,
    pp.categoria,
    pp.marca,
    pp.nosso_preco,
    pp.preco_medio_concorrentes,
    pp.preco_minimo_concorrentes,
    pp.preco_maximo_concorrentes,
    pp.total_concorrentes,
    pp.preco_medio_concorrentes IS NULL                                              AS sem_dados_concorrente,
    CASE
        WHEN pp.preco_medio_concorrentes = 0 THEN NULL
        ELSE ((pp.nosso_preco - pp.preco_medio_concorrentes) / pp.preco_medio_concorrentes) * 100
    END AS diferenca_percentual_vs_media,
    CASE
        WHEN pp.preco_minimo_concorrentes = 0 THEN NULL
        ELSE ((pp.nosso_preco - pp.preco_minimo_concorrentes) / pp.preco_minimo_concorrentes) * 100
    END AS diferenca_percentual_vs_minimo,
    CASE
        WHEN pp.nosso_preco IS NULL
          OR pp.preco_medio_concorrentes IS NULL THEN 'SEM_DADOS'
        WHEN pp.nosso_preco > pp.preco_maximo_concorrentes THEN 'MAIS_CARO_QUE_TODOS'
        WHEN pp.nosso_preco < pp.preco_minimo_concorrentes THEN 'MAIS_BARATO_QUE_TODOS'
        WHEN pp.nosso_preco > pp.preco_medio_concorrentes  THEN 'ACIMA_DA_MEDIA'
        WHEN pp.nosso_preco < pp.preco_medio_concorrentes  THEN 'ABAIXO_DA_MEDIA'
        ELSE 'NA_MEDIA'
    END AS classificacao_preco,
    COALESCE(vp.receita_total, 0) AS receita_total,
    COALESCE(vp.quantidade_total, 0) AS quantidade_total
FROM precos_por_produto pp
LEFT JOIN vendas_por_produto vp
    ON pp.id_produto = vp.id_produto
ORDER BY diferenca_percentual_vs_media DESC NULLS LAST
```

- [ ] **Step 2: Atualizar _gold_models.yml com accepted_values e novas colunas**

Localizar o modelo `gold_pricing_precos_competitividade` em `transform/models/gold/_gold_models.yml`. Substituir o bloco completo do modelo:

```yaml
  - name: gold_pricing_precos_competitividade
    description: "Data mart Gold de competitividade de precos para Pricing."
    columns:
      - name: produto_id
        description: "Identificador unico do produto no mart."
        tests:
          - unique
          - not_null
      - name: sem_dados_concorrente
        description: "True quando o produto nao possui dados de concorrentes para comparacao."
      - name: classificacao_preco
        description: "Posicionamento do preco proprio em relacao aos concorrentes."
        tests:
          - accepted_values:
              values: ['MAIS_CARO_QUE_TODOS', 'MAIS_BARATO_QUE_TODOS', 'ACIMA_DA_MEDIA', 'ABAIXO_DA_MEDIA', 'NA_MEDIA', 'SEM_DADOS']
```

- [ ] **Step 3: Verificar sintaxe**

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```
Esperado: `Done.`

- [ ] **Step 4: Materializar**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s gold_pricing_precos_competitividade --full-refresh
```
Esperado: `1 of 1 OK`

- [ ] **Step 5: Verificar que produtos sem concorrentes aparecem e classificacao está correta**

```sql
SELECT COUNT(*) FROM public_gold_pricing.gold_pricing_precos_competitividade
WHERE sem_dados_concorrente = true;
-- Esperado: > 0 (produtos INFERIDO e produtos sem dados de preco competidor)

SELECT COUNT(*) FROM public_gold_pricing.gold_pricing_precos_competitividade
WHERE classificacao_preco = 'NA_MEDIA' AND nosso_preco IS NULL;
-- Esperado: 0 (produtos INFERIDO agora retornam 'SEM_DADOS')

SELECT COUNT(*) FROM public_gold_pricing.gold_pricing_precos_competitividade
WHERE classificacao_preco = 'SEM_DADOS';
-- Esperado: igual ao COUNT de sem_dados_concorrente = true
```

- [ ] **Step 6: Rodar testes**

```bash
uv run --package transform dbt test --project-dir transform --profiles-dir transform -s gold_pricing_precos_competitividade
```
Esperado: todos os testes passam, incluindo o novo `accepted_values` de `classificacao_preco`.

- [ ] **Step 7: Commit**

```bash
git add transform/models/gold/marts/pricing/gold_pricing_precos_competitividade.sql transform/models/gold/_gold_models.yml
git commit -m "fix(gold): expose products without competitor data in pricing mart

- Remove WHERE IS NOT NULL que excluia silenciosamente produtos sem
  dados de concorrente (incluindo todos os INFERIDO).
- Adiciona flag sem_dados_concorrente (boolean) para filtro explicito.
- Corrige classificacao_preco: produtos com nosso_preco ou
  preco_medio_concorrentes nulos retornavam 'NA_MEDIA' incorretamente,
  agora retornam 'SEM_DADOS'."
```

---

### Task 10: Validar Fase 2 — Gold completa

**Files:** nenhum (validação)

- [ ] **Step 1: Rodar todos os modelos Gold**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s tag:gold --full-refresh
```
Esperado: todos os modelos Gold materializam sem erro.

- [ ] **Step 2: Rodar todos os testes Gold**

```bash
uv run --package transform dbt test --project-dir transform --profiles-dir transform -s tag:gold
```
Esperado: zero warnings, zero errors.

- [ ] **Step 3: Validação end-to-end do pipeline completo**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform --full-refresh
uv run --package transform dbt test --project-dir transform --profiles-dir transform
```
Esperado: pipeline completo (Bronze → Silver → Gold) sem erros.
