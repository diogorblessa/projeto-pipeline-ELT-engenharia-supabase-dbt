# PRD - Case 1: Dashboard Streamlit

## Contexto

Dashboard para três diretores de um e-commerce consumirem os Data Marts Gold do
PostgreSQL/Supabase. Cada diretor tem uma página dedicada e deve conseguir abrir o app,
selecionar filtros e ver números claros sem consultar SQL.

**Referência técnica:** `.llm/database.md`

## Arquitetura

```text
Supabase PostgreSQL
  public_gold_sales.gold_sales_vendas_temporais
  public_gold_cs.gold_customer_success_clientes_segmentacao
  public_gold_pricing.gold_pricing_precos_competitividade
        |
        v
Streamlit App (.llm/case-01-dashboard/app.py)
  views/vendas.py
  views/clientes.py
  views/pricing.py
```

O `docker-compose.yml` atual não publica o dashboard. Ele continua focado em `extract` e `dbt`.
O dashboard roda localmente via Streamlit.

## Conexão com o banco

- Variável obrigatória: `POSTGRES_URL`.
- Fonte padrão: `.env` da raiz do projeto, carregado por `app.py`.
- `.llm/case-01-dashboard/.env.example` existe apenas como placeholder local, sem segredos.
- A conexão usa SQLAlchemy e `pandas.read_sql`.
- Se `POSTGRES_URL` estiver ausente ou inválida, o app mostra erro amigável.

Exemplo sem credenciais reais:

```env
POSTGRES_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/postgres
```

## Requisitos gerais

- Layout wide.
- Valores monetários em formato brasileiro com `R$`.
- Textos em português do Brasil com acentuação correta.
- Cores com contraste suficiente no fundo claro.
- Rótulos numéricos visíveis nos gráficos principais.
- Sem cache agressivo, pois os marts mudam após cada `dbt run`.
- Não alterar regras de negócio nem schemas dbt para atender ao dashboard.
- Validar colunas obrigatórias antes de calcular KPIs ou renderizar gráficos.
- Mostrar mensagens amigáveis para conexão inválida, colunas ausentes e filtros sem dados.

## Página 1 - Vendas

**Diretor:** Comercial

**Tabela fonte:** `public_gold_sales.gold_sales_vendas_temporais`

**Contrato do mart:**

- `dia_da_semana` é o nome atual da coluna de dia da semana.
- O dashboard aceita também `dia_semana_nome` para compatibilidade.
- `mes_venda` pode chegar como decimal no pandas e deve ser convertido para inteiro.

**Filtros:** Ano, Mês e Dia da Semana.

**KPIs:**

| KPI | Cálculo | Formato |
|---|---|---|
| Receita Total | `SUM(receita_total)` | R$ XXX.XXX,XX |
| Total de Vendas | `SUM(total_vendas)` | X.XXX |
| Ticket Médio | Receita Total / Total de Vendas | R$ XXX,XX |
| Clientes Únicos | soma do máximo diário de `total_clientes_unicos` | XXX |

**Gráficos:**

- Receita Diária: linha com área preenchida e rótulos monetários compactos.
- Receita por Dia da Semana: barras ordenadas de Segunda a Domingo.
- Volume de Vendas por Hora: barras com rótulos de quantidade.

## Página 2 - Clientes

**Diretora:** Customer Success

**Tabela fonte:** `public_gold_cs.gold_customer_success_clientes_segmentacao`

**Filtros:** Segmento, Estado e Top N Clientes.

**KPIs:**

| KPI | Cálculo | Formato |
|---|---|---|
| Total de Clientes | `COUNT(*)` | XXX |
| Clientes VIP | `COUNT(*) WHERE segmento_cliente = 'VIP'` | XX |
| Receita VIP | `SUM(receita_total) WHERE segmento_cliente = 'VIP'` | R$ XXX.XXX,XX |
| Ticket Médio Geral | `AVG(ticket_medio)` | R$ XXX,XX |

**Gráficos:**

- Clientes por Segmento: barra horizontal com total e percentual.
- Receita por Segmento: barras com rótulos monetários.
- Top 10 Clientes por Receita: barras horizontais.
- Receita por Estado: barras horizontais ordenadas por receita, com contexto de clientes no hover.

**Tabela detalhada:** deve exibir nomes de colunas legíveis e valores monetários em R$.

## Página 3 - Pricing

**Diretor:** Pricing

**Tabela fonte:** `public_gold_pricing.gold_pricing_precos_competitividade`

**Contrato do mart:**

- `classificacao_preco` aceita `MAIS_CARO_QUE_TODOS`, `ACIMA_DA_MEDIA`, `NA_MEDIA`,
  `ABAIXO_DA_MEDIA`, `MAIS_BARATO_QUE_TODOS` e `SEM_DADOS`.
- Registros sem percentual de competitividade não devem entrar em médias percentuais.

**Filtros:** Categoria, Marca e Classificação.

**KPIs:**

| KPI | Cálculo | Formato |
|---|---|---|
| Produtos Monitorados | `COUNT(*)` | XXX |
| Mais Caros que Todos | `COUNT(*) WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS'` | XX |
| Mais Baratos que Todos | `COUNT(*) WHERE classificacao_preco = 'MAIS_BARATO_QUE_TODOS'` | XX |
| Acima da Média | `COUNT(*) WHERE classificacao_preco = 'ACIMA_DA_MEDIA'` | XX |
| Diferença Média vs Mercado | `AVG(diferenca_percentual_vs_media)` ignorando nulos | +X.X% |
| Receita Total | `SUM(receita_total)` | R$ XXX.XXX,XX |
| Receita em Risco | `SUM(receita_total)` para produtos `MAIS_CARO_QUE_TODOS` | R$ XXX.XXX,XX |
| % Receita em Risco | Receita em Risco / Receita Total | X.X% |

**Gráficos:**

- Posicionamento vs Concorrência: barra horizontal por classificação.
- Competitividade por Categoria: barras com verde para negativo e laranja/vermelho para positivo.
- Competitividade x Volume por Classificação: bolhas agregadas por classificação.

**Tabela de alertas:** produtos `MAIS_CARO_QUE_TODOS`, com preços em R$ e percentual formatado.

**Narrativa executiva:** resumo textual da seleção filtrada com produtos monitorados,
diferença média vs mercado, receita em risco, percentual da receita filtrada e categoria
de maior exposição.

## Como testar

```bash
uv sync --all-packages
uv run pytest
uv run ruff check
python -m streamlit run .llm/case-01-dashboard/app.py
```

Se o ambiente não tiver `uv` no PATH, use os executáveis equivalentes da `.venv`.
