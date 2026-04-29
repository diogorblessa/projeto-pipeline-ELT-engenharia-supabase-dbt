# Design: Qualidade e Enriquecimento dbt — Silver e Gold

**Data:** 2026-04-29
**Abordagem:** Opção D — Qualidade + Enriquecimento Focalizado (Abordagem 2: duas fases por camada)
**Escopo:** 8 itens distribuídos em Fase 1 (Silver) e Fase 2 (Gold)

---

## Contexto

O pipeline ELT implementa a Arquitetura Medallion (Bronze → Silver → Gold). A Silver já possui tratamentos sólidos de tipagem, deduplicação e NULLIF. A Gold implementa um modelo estrela com dimensões e fatos. Esta spec documenta correções de bugs/riscos e enriquecimentos de alto impacto identificados na avaliação Kimball.

**O que esta spec não inclui (fora de escopo deliberado):**
- Surrogate keys inteiros — chaves naturais estáveis, overhead não justificado para fonte única
- SCD Type 2 — projeto sem requisito de histórico de dimensões
- `dim_canal_venda` — dimensão degenerada com apenas 2 valores e zero atributos extras; Kimball recomenda manter no fato
- Audit columns Nível 2 (Python) — Nível 1 (dbt) é suficiente para pipeline batch

---

## Fase 1 — Silver

### Item 1: Corrigir `accepted_values` de `canal_venda`

**Arquivo:** `transform/models/silver/_silver_models.yml`

**Problema:** o teste `accepted_values` para `canal_venda` lista apenas `['ecommerce', 'loja_fisica']`, mas o SQL produz `'NAO_INFORMADO'` via `COALESCE` quando o campo é nulo. O teste falha em produção para vendas sem canal identificado.

**Suposição:** `canal_venda = 'NAO_INFORMADO'` é um estado válido de negócio (venda sem canal identificado), não dado corrompido — por isso entra no contrato em vez de ser filtrado.

**Mudança:** adicionar `'NAO_INFORMADO'` à lista de valores aceitos.

```yaml
- accepted_values:
    values: ['ecommerce', 'loja_fisica', 'NAO_INFORMADO']
```

**Critério de sucesso:** `dbt test -s silver_vendas` passa sem warnings para `canal_venda`.

---

### Item 2: `hora_venda` string → inteiro (hora do dia)

**Arquivo:** `transform/models/silver/silver_vendas.sql`

**Problema:** `TO_CHAR(data_venda, 'HH24:MI')` produz uma string como `'14:30'`. String não permite aritmética nem sort numérico correto. No mart de vendas, o `GROUP BY hora_venda` sobre string cria até 1.440 grupos por dia (um por minuto), tornando agrupamento diário impraticável.

**Mudança:**
```sql
-- antes
TO_CHAR(data_venda, 'HH24:MI') AS hora_venda

-- depois
EXTRACT(HOUR FROM data_venda)::integer AS hora_venda
```

**Impacto downstream:**
- `gold_fct_vendas`: passthrough, sem mudança de SQL
- `gold_sales_vendas_temporais`: `GROUP BY hora_venda` passa a agrupar por hora cheia (0–23), máximo 24 linhas por dia

**Breaking change:** consumidores que esperam string `'HH24:MI'` precisam ser atualizados (dashboard case-01, agente case-02).

**Critério de sucesso:** `hora_venda` é `INTEGER`, valores entre 0–23; mart de vendas retorna ≤ 24 linhas por `data_venda`.

---

### Item 3: `faixa_preco` thresholds → `vars`

**Arquivos:** `transform/models/silver/silver_vendas.sql`, `transform/models/silver/silver_produtos.sql`, `transform/dbt_project.yml`

**Problema:** thresholds de classificação de preço estão hardcoded no SQL. Alterar a regra de negócio exige editar SQL em vez de configuração.

**Vars a adicionar em `dbt_project.yml`:**
```yaml
vars:
  # existentes
  segmentacao_vip_threshold: 10000
  segmentacao_top_tier_threshold: 5000
  # novos
  faixa_venda_barato_max: 100
  faixa_venda_medio_max: 500
  faixa_produto_premium_min: 1000
  faixa_produto_medio_min: 500
```

**Mudança em `silver_vendas.sql`:**
```sql
CASE
    WHEN preco_unitario < {{ var('faixa_venda_barato_max', 100) }}  THEN 'barato'
    WHEN preco_unitario <= {{ var('faixa_venda_medio_max', 500) }}  THEN 'medio'
    ELSE 'caro'
END AS faixa_preco
```

**Mudança em `silver_produtos.sql`:**
```sql
CASE
    WHEN preco_atual IS NULL                                              THEN 'NAO_INFORMADO'
    WHEN preco_atual > {{ var('faixa_produto_premium_min', 1000) }}       THEN 'PREMIUM'
    WHEN preco_atual > {{ var('faixa_produto_medio_min', 500) }}          THEN 'MEDIO'
    ELSE 'BASICO'
END AS faixa_preco
```

**Critério de sucesso:** run padrão produz resultado idêntico ao atual; `dbt run --vars '{faixa_venda_barato_max: 200}'` muda a distribuição de `faixa_preco`.

---

### Item 4: Regra de preço `> 0` (era `>= 0`)

**Arquivos:** `transform/models/silver/silver_vendas.sql`, `transform/models/silver/silver_preco_competidores.sql`

**Problema:** `preco_unitario >= 0` e `preco_concorrente >= 0` permitem preço zero, que é dado inválido neste domínio (não há produtos gratuitos).

**Suposição:** preço zero é inválido. Se existirem promoções gratuitas no futuro, a regra deve ser revisada explicitamente.

**Mudança:** substituir `>= 0` por `> 0` nos filtros `WHERE` de ambos os modelos.

**Critério de sucesso:** `SELECT COUNT(*) FROM silver.silver_vendas WHERE preco_unitario = 0` retorna 0.

---

### Item 8: Coluna de auditoria `silver_processado_em`

**Arquivos:** todos os 4 modelos Silver (`.sql` e `.yml`)

**Motivação:** permite detectar pipelines parados verificando `MAX(silver_processado_em)` e rastrear qual run do dbt produziu cada snapshot de dados.

**Mudança em cada modelo Silver — adicionar ao SELECT final:**
```sql
current_timestamp AS silver_processado_em
```

**Mudança nos YAMLs — adicionar entrada de coluna:**
```yaml
- name: silver_processado_em
  description: "Timestamp de quando o dbt materializou esta tabela (auditoria de pipeline)."
```

**Critério de sucesso:** coluna presente em todas as 4 tabelas Silver com valor de timestamp; `dbt test` passa.

---

## Fase 2 — Gold

### Item 5: Enriquecer `gold_dim_datas`

**Arquivo:** `transform/models/gold/dimensional/gold_dim_datas.sql`

**Problema:** a dimensão de datas tem apenas `data`, `ano`, `mes`, `dia`, `dia_semana`, `dia_semana_nome`. Faltam atributos de calendário usados em qualquer análise temporal básica.

**Colunas a adicionar:**
```sql
EXTRACT(QUARTER FROM data::timestamp)::integer          AS trimestre,
TO_CHAR(data::timestamp, 'TMMonth')                     AS nome_mes,
EXTRACT(WEEK FROM data::timestamp)::integer             AS numero_semana,
EXTRACT(DOW FROM data::timestamp) IN (0, 6)             AS is_fim_de_semana,
data = date_trunc('month', data)::date                  AS is_primeiro_dia_mes
```

**Remoção:** `ORDER BY data` no SELECT final — desnecessário em materialização TABLE e cria custo extra sem garantia de ordem para consumers.

**Critério de sucesso:** `SELECT trimestre, nome_mes, is_fim_de_semana FROM public_gold.gold_dim_datas LIMIT 5` retorna dados coerentes; testes `unique` e `not_null` em `data` passam.

---

### Item 6: `var('data_referencia_cs')` no mart de Customer Success

**Arquivo:** `transform/models/gold/marts/customer_success/gold_customer_success_clientes_segmentacao.sql`

**Problema:** o mart agrega vendas de todos os tempos. Não é possível calcular segmentação em uma data histórica específica sem alterar o modelo.

**Mudança:** adicionar filtro Jinja condicional na CTE `receita_por_cliente`:
```sql
FROM {{ ref('gold_fct_vendas') }} f
{% if var('data_referencia_cs', none) is not none %}
WHERE f.data_venda <= '{{ var("data_referencia_cs") }}'::date
{% endif %}
```

**Var a adicionar em `dbt_project.yml`:**
```yaml
data_referencia_cs: null   # null = all-time (comportamento atual mantido)
```

**Critério de sucesso:** run sem var produz resultado idêntico ao atual; `dbt run --vars '{data_referencia_cs: "2024-06-30"}'` retorna apenas vendas até essa data.

---

### Item 7: Flag `sem_dados_concorrente` no mart de Pricing

**Arquivo:** `transform/models/gold/marts/pricing/gold_pricing_precos_competitividade.sql`

**Problema 1:** `WHERE pp.preco_medio_concorrentes IS NOT NULL` exclui silenciosamente produtos sem dados de concorrente (incluindo todos os produtos INFERIDO). O time de Pricing não sabe que esses produtos existem.

**Problema 2:** `classificacao_preco` cai em `'NA_MEDIA'` para produtos com `nosso_preco IS NULL` (INFERIDO) — valor incorreto e enganoso.

**Mudanças:**

Remover o `WHERE pp.preco_medio_concorrentes IS NOT NULL`.

Adicionar coluna booleana:
```sql
pp.preco_medio_concorrentes IS NULL AS sem_dados_concorrente,
```

Corrigir `classificacao_preco` adicionando guarda de NULL:
```sql
CASE
    WHEN pp.nosso_preco IS NULL
      OR pp.preco_medio_concorrentes IS NULL THEN 'SEM_DADOS'
    WHEN pp.nosso_preco > pp.preco_maximo_concorrentes  THEN 'MAIS_CARO_QUE_TODOS'
    WHEN pp.nosso_preco < pp.preco_minimo_concorrentes  THEN 'MAIS_BARATO_QUE_TODOS'
    WHEN pp.nosso_preco > pp.preco_medio_concorrentes   THEN 'ACIMA_DA_MEDIA'
    WHEN pp.nosso_preco < pp.preco_medio_concorrentes   THEN 'ABAIXO_DA_MEDIA'
    ELSE 'NA_MEDIA'
END AS classificacao_preco
```

Atualizar `accepted_values` no YAML para incluir `'SEM_DADOS'`.

**Critério de sucesso:** `SELECT COUNT(*) FROM public_gold_pricing.gold_pricing_precos_competitividade WHERE sem_dados_concorrente = true` retorna > 0; nenhum produto com `nosso_preco IS NULL` aparece com `classificacao_preco = 'NA_MEDIA'`.

---

## Critério de Sucesso Global

```bash
# Fase 1
dbt run -s tag:silver --full-refresh
dbt test -s tag:silver
# → todos os testes passam

# Fase 2
dbt run -s tag:gold --full-refresh
dbt test -s tag:gold
# → todos os testes passam
```

**Atenção antes da Fase 1:** o Item 2 (`hora_venda` string → integer) é uma breaking change. Os consumidores do mart de vendas (dashboard case-01 e agente case-02) precisam ser atualizados para lidar com `hora_venda` como `INTEGER` antes ou junto da Fase 1.

---

## Resumo de Arquivos Modificados

| Fase | Arquivo | Itens |
|------|---------|-------|
| 1 | `transform/dbt_project.yml` | 3 |
| 1 | `transform/models/silver/silver_vendas.sql` | 2, 3, 4, 8 |
| 1 | `transform/models/silver/silver_clientes.sql` | 8 |
| 1 | `transform/models/silver/silver_produtos.sql` | 3, 8 |
| 1 | `transform/models/silver/silver_preco_competidores.sql` | 4, 8 |
| 1 | `transform/models/silver/_silver_models.yml` | 1, 8 |
| 2 | `transform/models/gold/dimensional/gold_dim_datas.sql` | 5 |
| 2 | `transform/models/gold/marts/customer_success/gold_customer_success_clientes_segmentacao.sql` | 6 |
| 2 | `transform/models/gold/marts/pricing/gold_pricing_precos_competitividade.sql` | 7 |
| 2 | `transform/models/gold/_gold_models.yml` | 7 (accepted_values) |
