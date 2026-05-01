# Feature - Case 01: Dashboard Streamlit | E-commerce Analytics

Documento de escopo do dashboard Streamlit que consome os Data Marts Gold do Supabase.
Baseado em: `PRD-dashboard.md` e `.llm/database.md`.

## Visão geral

| Item | Detalhe |
|---|---|
| App | `.llm/case-01-dashboard/app.py` |
| Stack | Python 3.11+, Streamlit, SQLAlchemy, psycopg2-binary, pandas, plotly, python-dotenv |
| Banco | PostgreSQL (Supabase) |
| Variável obrigatória | `POSTGRES_URL` |
| Fonte de ambiente | `.env` da raiz do projeto |
| Schemas Gold | `public_gold_sales`, `public_gold_cs`, `public_gold_pricing` |
| Usuários | Diretor Comercial, Diretora de Customer Success, Diretor de Pricing |

Dashboard Streamlit local para consulta dos marts Gold, com navegação superior entre
Vendas, Clientes e Pricing. Os filtros ficam na sidebar e são agrupados pelo domínio
selecionado.

O dashboard não é buildado pelo `docker-compose.yml` atual. O Docker do projeto cobre `extract`
e `dbt`; o dashboard roda localmente via Streamlit.

## Arquivos do dashboard

| Arquivo | Descrição |
|---|---|
| `app.py` | Entry point Streamlit, CSS global, sidebar e roteamento |
| `views/` | Renderização das páginas `vendas`, `clientes` e `pricing` |
| `db.py` | Engine SQLAlchemy a partir de `POSTGRES_URL` |
| `utils.py` | Paleta, formatação brasileira, normalização de colunas e estilos Plotly |
| `pyproject.toml` | Dependências do case para `uv sync --all-packages` |
| `.env.example` | Placeholder local da variável `POSTGRES_URL`, sem segredos |

## Garantias de execução

- Usa `POSTGRES_URL` do `.env` da raiz do projeto.
- Valida colunas obrigatórias antes de calcular KPIs ou renderizar gráficos.
- Mostra mensagens amigáveis para conexão inválida, colunas ausentes e filtros sem dados.
- Mantém valores monetários em `R$` em cards, tabelas, hovers e labels.
- Executa localmente via Streamlit e não é servido pelo `docker-compose.yml`.

## F-01 - Infraestrutura

- `st.set_page_config(layout="wide")`
- `load_dotenv(...)` carrega o `.env` da raiz do projeto.
- `get_data(query: str) -> pandas.DataFrame` lê via SQLAlchemy.
- Erros de conexão aparecem com `st.error`, sem traceback do Streamlit para o usuário final.
- A navegação superior usa `st.radio(..., horizontal=True)` e importa apenas a página selecionada.
- O case 01 está no `uv workspace`; seus testes entram no `uv run pytest` da raiz.

## F-02 - Página Vendas

**Tabela:** `public_gold_sales.gold_sales_vendas_temporais`

**Contrato relevante:**

- O mart atual entrega `dia_da_semana`; o dashboard normaliza para `dia_semana_nome`.
- `mes_venda` pode chegar ao pandas como decimal; o dashboard converte para inteiro antes do filtro.
- Dias `Terca` e `Sabado` são exibidos como `Terça` e `Sábado`.

**Filtros:** Ano, Mês e Dia da Semana na sidebar, com opção `Todos`.

**KPIs:** Receita Total, Total de Vendas, Ticket Médio e Clientes Únicos.

**Gráficos:**

- Receita Diária: linha com área preenchida e rótulos em R$.
- Receita por Dia da Semana: barras ordenadas de Segunda a Domingo, com rótulos em R$.
- Volume de Vendas por Hora: barras com rótulos de quantidade.

## F-03 - Página Clientes

**Tabela:** `public_gold_cs.gold_customer_success_clientes_segmentacao`

**Filtros:** Segmento, Estado e Top N Clientes na sidebar.

**KPIs:** Receita Total, Total de Clientes, Clientes VIP e Ticket Médio.

**Gráficos:**

- Clientes por Segmento: barra horizontal com total e percentual.
- Receita por Segmento: barras com rótulos em R$.
- Top N Clientes por Receita: barras horizontais com rótulos em R$ conforme o filtro selecionado.
- Receita por Estado: barras horizontais com rótulos em R$ e contexto de clientes no hover.

**Tabela detalhada:** exibe nomes de colunas legíveis e valores monetários em R$.

## F-04 - Página Pricing

**Tabela:** `public_gold_pricing.gold_pricing_precos_competitividade`

**Filtros:** Categoria, Marca e Classificação na sidebar.

**Contrato relevante:**

- `classificacao_preco` pode conter `SEM_DADOS`.
- Médias e cruzamentos de competitividade ignoram percentuais nulos.
- A tabela de alertas segue limitada a `MAIS_CARO_QUE_TODOS`.

**KPIs:** Produtos Monitorados, Mais Caros que Todos, Mais Baratos que Todos, Acima da
Média, Diferença Média vs Mercado, Receita Total, Receita em Risco e % Receita em Risco.

**Narrativa executiva:** leitura textual da seleção filtrada com produtos monitorados,
diferença média vs mercado, receita em risco, percentual da receita filtrada e categoria
de maior exposição.

**Gráficos:**

- Posicionamento vs Concorrência: barra horizontal por classificação, com total e percentual.
- Competitividade por Categoria: barras com cor condicional e rótulos percentuais.
- Competitividade x Volume por Classificação: bolhas agregadas por classificação, com volume visível.

## Como testar

```bash
uv sync --all-packages
uv run pytest
uv run ruff check
python -m streamlit run .llm/case-01-dashboard/app.py
```

Se `uv` não estiver disponível no PATH, use a `.venv` local equivalente para rodar `pytest`,
`ruff` e `streamlit`.
