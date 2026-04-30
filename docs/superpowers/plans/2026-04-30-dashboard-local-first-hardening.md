# Dashboard Local-First Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir a execução completa do dashboard local do Case 01 e evoluir a UX com filtros laterais por domínio, abas superiores, contratos de colunas, formatação em R$ e textos acentuados em PT-BR.

**Architecture:** O dashboard continua em `.llm/case-01-dashboard`, rodando localmente via Streamlit e usando `POSTGRES_URL` do `.env` da raiz. `utils.py` concentra contratos, normalização, filtros, formatação e estilos; `app.py` monta layout, abas e filtros; cada view consome dados já validados e renderiza KPIs/gráficos sem hardcodes espalhados. O Docker não publica o dashboard, mas os Dockerfiles existentes precisam continuar compatíveis com o workspace `uv`.

**Tech Stack:** Python 3.11, Streamlit, pandas, Plotly, SQLAlchemy, python-dotenv, uv, pytest, ruff, dbt-postgres, Docker Compose existente.

---

## File Map

| File | Responsibility |
|---|---|
| `.llm/case-01-dashboard/utils.py` | Constants, labels, currency/percent formatters, column contracts, validation, filter helpers, chart styling |
| `.llm/case-01-dashboard/tests/test_utils.py` | Unit coverage for new contracts, filtering helpers, labels, formatting and text hygiene |
| `.llm/case-01-dashboard/app.py` | Local Streamlit entrypoint, root `.env` load, global CSS, sidebar filters, top tabs |
| `.llm/case-01-dashboard/views/vendas.py` | Sales page using year/month/day filters, safe contract validation and visible R$ labels |
| `.llm/case-01-dashboard/views/clientes.py` | Customer Success page using segment/state/top-N filters and readable tables |
| `.llm/case-01-dashboard/views/pricing.py` | Pricing page using category/brand/classification filters, executive KPIs and alert table |
| `.llm/case-01-dashboard/PRD-dashboard.md` | Case contract aligned to local-first execution and new filters |
| `.llm/case-01-dashboard/feature.md` | Implementation summary aligned to the delivered UI |
| `.llm/case-01-dashboard/.env.example` | Local template for `POSTGRES_URL`, with no secrets |
| `.llm/case-01-dashboard/pyproject.toml` | Dashboard package metadata for the root uv workspace |
| `pyproject.toml` | Root workspace membership, pytest paths and pythonpath |
| `uv.lock` | Locked dependencies after adding dashboard package |
| `extract_load/Dockerfile` | Existing extract image build, kept compatible with uv workspace |
| `transform/Dockerfile` | Existing dbt image build, kept compatible with uv workspace |
| `.dockerignore` | Docker context rules aligned with `.gitignore` and uv workspace needs |

## Task 1: Strengthen Dashboard Utilities and Contracts

**Files:**
- Modify: `.llm/case-01-dashboard/utils.py`
- Modify: `.llm/case-01-dashboard/tests/test_utils.py`

- [ ] **Step 1: Add failing tests for column contracts and filter helpers**

Add these tests to `.llm/case-01-dashboard/tests/test_utils.py`:

```python
import pytest

from utils import (
    FILTER_ALL,
    MissingColumnsError,
    build_filter_options,
    filter_equals,
    filter_in,
    validate_columns,
)


class TestColumnContracts:
    def test_validate_columns_accepts_present_columns(self):
        df = pd.DataFrame({"a": [1], "b": [2]})

        validate_columns(df, {"a", "b"}, "public_gold.test")

    def test_validate_columns_raises_clear_error_for_missing_columns(self):
        df = pd.DataFrame({"a": [1]})

        with pytest.raises(MissingColumnsError) as exc:
            validate_columns(df, {"a", "b", "c"}, "public_gold.test")

        assert "public_gold.test" in str(exc.value)
        assert "b" in str(exc.value)
        assert "c" in str(exc.value)


class TestFilterHelpers:
    def test_build_filter_options_keeps_all_label_and_sorted_values(self):
        values = pd.Series(["Moda", None, "Casa", "Moda"])

        assert build_filter_options(values) == [FILTER_ALL, "Casa", "Moda"]

    def test_filter_equals_keeps_all_rows_when_all_selected(self):
        df = pd.DataFrame({"categoria": ["Casa", "Moda"]})

        result = filter_equals(df, "categoria", FILTER_ALL)

        assert result.equals(df)

    def test_filter_equals_filters_single_value(self):
        df = pd.DataFrame({"categoria": ["Casa", "Moda"]})

        result = filter_equals(df, "categoria", "Moda")

        assert result["categoria"].tolist() == ["Moda"]

    def test_filter_in_returns_empty_when_no_values_selected(self):
        df = pd.DataFrame({"categoria": ["Casa", "Moda"]})

        result = filter_in(df, "categoria", [])

        assert result.empty

    def test_filter_in_filters_selected_values(self):
        df = pd.DataFrame({"categoria": ["Casa", "Moda", "Games"]})

        result = filter_in(df, "categoria", ["Casa", "Games"])

        assert result["categoria"].tolist() == ["Casa", "Games"]
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```bash
uv run pytest .llm/case-01-dashboard/tests/test_utils.py -q
```

Expected: FAIL with import errors for `FILTER_ALL`, `MissingColumnsError`, `build_filter_options`, `filter_equals`, `filter_in` and `validate_columns`.

- [ ] **Step 3: Implement contracts and helpers in `utils.py`**

Add these definitions near the constants in `.llm/case-01-dashboard/utils.py`:

```python
FILTER_ALL = "Todos"

SALES_TABLE = "public_gold_sales.gold_sales_vendas_temporais"
CUSTOMERS_TABLE = "public_gold_cs.gold_customer_success_clientes_segmentacao"
PRICING_TABLE = "public_gold_pricing.gold_pricing_precos_competitividade"

SALES_REQUIRED_COLUMNS = {
    "data_venda",
    "ano_venda",
    "mes_venda",
    "hora_venda",
    "receita_total",
    "total_vendas",
    "total_clientes_unicos",
}
SALES_WEEKDAY_ALIASES = {"dia_da_semana", "dia_semana_nome"}

CUSTOMERS_REQUIRED_COLUMNS = {
    "cliente_id",
    "nome_cliente",
    "estado",
    "receita_total",
    "total_compras",
    "ticket_medio",
    "primeira_compra",
    "ultima_compra",
    "segmento_cliente",
    "ranking_receita",
}

PRICING_REQUIRED_COLUMNS = {
    "produto_id",
    "nome_produto",
    "categoria",
    "marca",
    "nosso_preco",
    "preco_medio_concorrentes",
    "preco_maximo_concorrentes",
    "diferenca_percentual_vs_media",
    "classificacao_preco",
    "receita_total",
    "quantidade_total",
}


class MissingColumnsError(ValueError):
    def __init__(self, table_name: str, missing: set[str]):
        missing_list = ", ".join(sorted(missing))
        super().__init__(
            f"A tabela {table_name} não contém as colunas esperadas: {missing_list}."
        )


def validate_columns(df: pd.DataFrame, required: set[str], table_name: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise MissingColumnsError(table_name, missing)


def validate_sales_columns(df: pd.DataFrame) -> None:
    validate_columns(df, SALES_REQUIRED_COLUMNS, SALES_TABLE)
    if SALES_WEEKDAY_ALIASES.isdisjoint(df.columns):
        raise MissingColumnsError(SALES_TABLE, {"dia_da_semana ou dia_semana_nome"})


def build_filter_options(values: pd.Series) -> list[str]:
    clean = values.dropna().astype(str).sort_values().unique().tolist()
    return [FILTER_ALL, *clean]


def filter_equals(df: pd.DataFrame, column: str, selected: str) -> pd.DataFrame:
    if selected == FILTER_ALL:
        return df
    return df[df[column].astype(str) == selected]


def filter_in(df: pd.DataFrame, column: str, selected: list[str]) -> pd.DataFrame:
    if not selected:
        return df.iloc[0:0]
    return df[df[column].astype(str).isin(selected)]
```

- [ ] **Step 4: Run the focused tests and confirm they pass**

Run:

```bash
uv run pytest .llm/case-01-dashboard/tests/test_utils.py -q
```

Expected: PASS for the new tests and existing utility tests.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/utils.py .llm/case-01-dashboard/tests/test_utils.py
git commit -m "fix(dashboard): valida contratos de colunas e filtros" \
-m "- Centraliza contratos mínimos dos marts usados pelo dashboard.
- Adiciona helpers defensivos para filtros e mensagens de colunas ausentes.
- Cobre validação e filtros com testes unitários."
```

## Task 2: Refactor App Layout to Sidebar Filters and Top Tabs

**Files:**
- Modify: `.llm/case-01-dashboard/app.py`

- [ ] **Step 1: Replace sidebar navigation with sidebar shell plus top tabs**

In `.llm/case-01-dashboard/app.py`, replace `sidebar_nav()` and `main()` with:

```python
def render_sidebar_shell() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <p class="sidebar-eyebrow">E-commerce Analytics</p>
                <h1>Relatório Analítico</h1>
                <p>Visão estratégica de vendas, clientes e pricing.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main():
    inject_css()
    render_sidebar_shell()

    vendas_tab, clientes_tab, pricing_tab = st.tabs(["Vendas", "Clientes", "Pricing"])

    with vendas_tab:
        from views.vendas import render as render_vendas

        render_vendas()

    with clientes_tab:
        from views.clientes import render as render_clientes

        render_clientes()

    with pricing_tab:
        from views.pricing import render as render_pricing

        render_pricing()
```

- [ ] **Step 2: Update CSS for readable sidebar and tabs**

Extend the CSS string inside `inject_css()` with:

```css
.sidebar-brand {
    border-bottom: 2px solid #7C3AED;
    margin-bottom: 1.25rem;
    padding-bottom: 1rem;
}
.sidebar-brand .sidebar-eyebrow {
    color: #6D28D9 !important;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0;
    margin-bottom: 0.25rem;
    text-transform: uppercase;
}
.sidebar-brand h1 {
    color: #111827 !important;
    font-size: 1.15rem;
    font-weight: 800;
    margin: 0;
}
.sidebar-brand p {
    color: #475569 !important;
    font-size: 0.8rem;
    margin-top: 0.35rem;
}
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #E2E8F0;
}
[data-testid="stSidebar"] * {
    color: #111827 !important;
}
[data-testid="stSidebar"] label {
    color: #475569 !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
}
[data-baseweb="tab-list"] {
    gap: 1rem;
}
[data-baseweb="tab"] {
    font-weight: 700;
}
```

Keep `.block-container` and chart/card color rules already present, but remove old sidebar navy rules that force all sidebar text to white.

- [ ] **Step 3: Run syntax smoke test**

Run:

```bash
uv run python -m py_compile .llm/case-01-dashboard/app.py
```

Expected: command exits 0 with no syntax errors. Do not import `app` directly because it calls `main()`.

- [ ] **Step 4: Commit**

```bash
git add .llm/case-01-dashboard/app.py
git commit -m "visual(dashboard): reorganiza navegação em abas e filtros laterais" \
-m "- Remove navegação por rádio da sidebar e usa abas superiores.
- Transforma a sidebar em área de identidade e filtros por domínio.
- Ajusta CSS para contraste e acentuação visível nos textos."
```

## Task 3: Implement Sales Filters and Safe Rendering

**Files:**
- Modify: `.llm/case-01-dashboard/views/vendas.py`
- Modify: `.llm/case-01-dashboard/tests/test_utils.py`

- [ ] **Step 1: Add a utility test for sales column validation**

Add to `TestNormalizeSalesColumns` in `.llm/case-01-dashboard/tests/test_utils.py`:

```python
def test_validate_sales_columns_accepts_dia_da_semana_alias(self):
    from utils import validate_sales_columns

    df = pd.DataFrame(
        {
            "data_venda": ["2026-01-01"],
            "ano_venda": [2026],
            "mes_venda": [1],
            "dia_da_semana": ["Quinta"],
            "hora_venda": [10],
            "receita_total": [100.0],
            "total_vendas": [1],
            "total_clientes_unicos": [1],
        }
    )

    validate_sales_columns(df)
```

- [ ] **Step 2: Run focused tests**

Run:

```bash
uv run pytest .llm/case-01-dashboard/tests/test_utils.py::TestNormalizeSalesColumns -q
```

Expected: PASS if Task 1 implemented `validate_sales_columns`; otherwise FAIL before implementation.

- [ ] **Step 3: Update imports in `views/vendas.py`**

Use these imports:

```python
from utils import (
    DAY_ORDER,
    FILTER_ALL,
    MissingColumnsError,
    apply_chart_style,
    build_filter_options,
    filter_equals,
    fmt_brl,
    fmt_brl_compact,
    fmt_int,
    kpi_card,
    month_filter_options,
    normalize_sales_columns,
    validate_sales_columns,
)
```

- [ ] **Step 4: Add sidebar filters for Vendas**

After loading and normalizing the dataframe, validate it and create filters:

```python
df = normalize_sales_columns(get_data(QUERY))
validate_sales_columns(df)
```

Replace the current month-only sidebar block with:

```python
with st.sidebar:
    st.markdown("#### Filtros - Vendas")
    ano_options = build_filter_options(df["ano_venda"])
    ano_sel = st.selectbox("Ano", ano_options, key="vendas_ano")

    mes_options = [FILTER_ALL, *[str(mes) for mes in month_filter_options(df["mes_venda"])]]
    mes_sel = st.selectbox("Mês", mes_options, key="vendas_mes")

    dia_options = [FILTER_ALL, *DAY_ORDER]
    dia_sel = st.selectbox("Dia da Semana", dia_options, key="vendas_dia_semana")
```

Apply filters:

```python
df_f = filter_equals(df, "ano_venda", ano_sel)
if mes_sel != FILTER_ALL:
    df_f = df_f[df_f["mes_venda"] == int(mes_sel)]
df_f = filter_equals(df_f, "dia_semana_nome", dia_sel)
```

- [ ] **Step 5: Catch column errors separately**

Use this error structure in `render()`:

```python
try:
    df = normalize_sales_columns(get_data(QUERY))
    validate_sales_columns(df)
except MissingColumnsError as e:
    st.error(str(e))
    return
except Exception:
    st.error("Não foi possível conectar ao banco de dados.")
    return
```

- [ ] **Step 6: Run tests and ruff**

Run:

```bash
uv run pytest .llm/case-01-dashboard/tests/test_utils.py -q
uv run ruff check .llm/case-01-dashboard/views/vendas.py .llm/case-01-dashboard/utils.py
```

Expected: tests pass; ruff reports `All checks passed!`.

- [ ] **Step 7: Commit**

```bash
git add .llm/case-01-dashboard/views/vendas.py .llm/case-01-dashboard/tests/test_utils.py
git commit -m "fix(dashboard): aplica filtros seguros na página de vendas" \
-m "- Adiciona filtros de ano, mês e dia da semana na sidebar.
- Valida aliases de dia da semana antes de renderizar gráficos.
- Mostra mensagens em português para contrato inválido ou conexão indisponível."
```

## Task 4: Implement Customer Filters, Top N and Readable Tables

**Files:**
- Modify: `.llm/case-01-dashboard/views/clientes.py`
- Modify: `.llm/case-01-dashboard/tests/test_utils.py`

- [ ] **Step 1: Add customer contract test**

Add to `.llm/case-01-dashboard/tests/test_utils.py`:

```python
class TestCustomerContracts:
    def test_customer_required_columns_are_validated(self):
        from utils import CUSTOMERS_REQUIRED_COLUMNS, CUSTOMERS_TABLE, validate_columns

        df = pd.DataFrame({column: [1] for column in CUSTOMERS_REQUIRED_COLUMNS})

        validate_columns(df, CUSTOMERS_REQUIRED_COLUMNS, CUSTOMERS_TABLE)
```

- [ ] **Step 2: Update imports in `views/clientes.py`**

Use:

```python
from utils import (
    CUSTOMERS_REQUIRED_COLUMNS,
    CUSTOMERS_TABLE,
    FILTER_ALL,
    SEGMENT_COLORS,
    SEGMENT_LABELS,
    MissingColumnsError,
    apply_chart_style,
    build_filter_options,
    filter_equals,
    fmt_brl,
    fmt_brl_compact,
    fmt_int,
    fmt_pct,
    kpi_card,
    validate_columns,
)
```

- [ ] **Step 3: Validate data and replace filters**

Use this load block:

```python
try:
    df = get_data(QUERY)
    validate_columns(df, CUSTOMERS_REQUIRED_COLUMNS, CUSTOMERS_TABLE)
except MissingColumnsError as e:
    st.error(str(e))
    return
except Exception:
    st.error("Não foi possível conectar ao banco de dados.")
    return
```

Replace current segment-only filter with:

```python
with st.sidebar:
    st.markdown("#### Filtros - Clientes")
    seg_sel = st.selectbox(
        "Segmento",
        [FILTER_ALL, "VIP", "TOP_TIER", "REGULAR"],
        key="clientes_segmento",
    )
    estado_sel = st.selectbox(
        "Estado",
        build_filter_options(df["estado"]),
        key="clientes_estado",
    )
    top_n = st.selectbox("Top N Clientes", [5, 10, 15, 20], index=1, key="clientes_top_n")

df_f = filter_equals(df, "segmento_cliente", seg_sel)
df_f = filter_equals(df_f, "estado", estado_sel)
```

- [ ] **Step 4: Compute KPIs and charts from filtered data**

Replace KPI references from `df` to `df_f`:

```python
total = len(df_f)
vip_count = int((df_f["segmento_cliente"] == "VIP").sum())
vip_rev = float(df_f.loc[df_f["segmento_cliente"] == "VIP", "receita_total"].sum())
ticket_medio = float(df_f["ticket_medio"].mean())
```

For top clients:

```python
df_top = df_f.nsmallest(int(top_n), "ranking_receita").sort_values(
    "ranking_receita", ascending=False
)
```

For the table:

```python
st.dataframe(_format_customer_table(df_f), use_container_width=True, hide_index=True)
```

- [ ] **Step 5: Handle empty filtered data**

Add after `df_f` filters:

```python
if df_f.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    return
```

- [ ] **Step 6: Run focused validation**

Run:

```bash
uv run pytest .llm/case-01-dashboard/tests/test_utils.py -q
uv run ruff check .llm/case-01-dashboard/views/clientes.py
```

Expected: tests pass; ruff reports `All checks passed!`.

- [ ] **Step 7: Commit**

```bash
git add .llm/case-01-dashboard/views/clientes.py .llm/case-01-dashboard/tests/test_utils.py
git commit -m "visual(dashboard): melhora filtros e ranking de clientes" \
-m "- Adiciona filtros de segmento, estado e Top N Clientes.
- Usa dados filtrados em KPIs, gráficos e tabela detalhada.
- Mantém nomes e valores monetários legíveis em português."
```

## Task 5: Expand Pricing Filters, KPIs and Executive Narrative

**Files:**
- Modify: `.llm/case-01-dashboard/views/pricing.py`
- Modify: `.llm/case-01-dashboard/tests/test_utils.py`

- [ ] **Step 1: Add pricing contract test**

Add to `.llm/case-01-dashboard/tests/test_utils.py`:

```python
class TestPricingContracts:
    def test_pricing_required_columns_are_validated(self):
        from utils import PRICING_REQUIRED_COLUMNS, PRICING_TABLE, validate_columns

        df = pd.DataFrame({column: [1] for column in PRICING_REQUIRED_COLUMNS})

        validate_columns(df, PRICING_REQUIRED_COLUMNS, PRICING_TABLE)
```

- [ ] **Step 2: Update imports in `views/pricing.py`**

Use:

```python
from utils import (
    CLASS_COLORS,
    PRICING_REQUIRED_COLUMNS,
    PRICING_TABLE,
    MissingColumnsError,
    apply_chart_style,
    classification_label,
    filter_in,
    fmt_brl,
    fmt_brl_compact,
    fmt_int,
    fmt_pct,
    kpi_card,
    validate_columns,
)
```

- [ ] **Step 3: Validate data and add Pricing filters**

Use this load block:

```python
try:
    df = get_data(QUERY)
    validate_columns(df, PRICING_REQUIRED_COLUMNS, PRICING_TABLE)
except MissingColumnsError as e:
    st.error(str(e))
    return
except Exception:
    st.error("Não foi possível conectar ao banco de dados.")
    return
```

Replace the current category-only filter with:

```python
with st.sidebar:
    st.markdown("#### Filtros - Pricing")
    categorias = df["categoria"].dropna().astype(str).sort_values().unique().tolist()
    marcas = df["marca"].dropna().astype(str).sort_values().unique().tolist()
    classificacoes = (
        df["classificacao_preco"].dropna().astype(str).sort_values().unique().tolist()
    )

    cats_sel = st.multiselect("Categoria", categorias, default=categorias, key="pricing_categorias")
    marcas_sel = st.multiselect("Marca", marcas, default=marcas, key="pricing_marcas")
    class_sel = st.multiselect(
        "Classificação",
        classificacoes,
        default=classificacoes,
        format_func=classification_label,
        key="pricing_classificacoes",
    )

df_f = filter_in(df, "categoria", cats_sel)
df_f = filter_in(df_f, "marca", marcas_sel)
df_f = filter_in(df_f, "classificacao_preco", class_sel)
```

- [ ] **Step 4: Add expanded KPIs**

Compute:

```python
total_prod = len(df_f)
mais_caros = int((df_f["classificacao_preco"] == "MAIS_CARO_QUE_TODOS").sum())
mais_baratos = int((df_f["classificacao_preco"] == "MAIS_BARATO_QUE_TODOS").sum())
acima_media = int((df_f["classificacao_preco"] == "ACIMA_DA_MEDIA").sum())
dif_media = float(df_f["diferenca_percentual_vs_media"].dropna().mean())
receita_total = float(df_f["receita_total"].sum())
receita_risco = float(
    df_f.loc[df_f["classificacao_preco"] == "MAIS_CARO_QUE_TODOS", "receita_total"].sum()
)
perc_receita_risco = (receita_risco / receita_total * 100) if receita_total else 0.0
```

Render two KPI rows:

```python
kpi_rows = [
    [
        ("Produtos Monitorados", fmt_int(total_prod)),
        ("Mais Caros que Todos", fmt_int(mais_caros)),
        ("Mais Baratos que Todos", fmt_int(mais_baratos)),
        ("Acima da Média", fmt_int(acima_media)),
    ],
    [
        ("Dif. Média vs Mercado", fmt_pct(dif_media)),
        ("Receita Total", fmt_brl(receita_total)),
        ("Receita em Risco", fmt_brl(receita_risco)),
        ("% Receita em Risco", fmt_pct(perc_receita_risco)),
    ],
]

for row in kpi_rows:
    cols = st.columns(4)
    for col, (label, value) in zip(cols, row, strict=True):
        col.markdown(kpi_card(label, value, THEME_COLOR), unsafe_allow_html=True)
```

- [ ] **Step 5: Add executive narrative**

Add after KPIs:

```python
categoria_maior_risco = "Sem categoria"
if not df_f.empty:
    risco_por_categoria = (
        df_f[df_f["classificacao_preco"] == "MAIS_CARO_QUE_TODOS"]
        .groupby("categoria", as_index=False)["receita_total"]
        .sum()
        .sort_values("receita_total", ascending=False)
    )
    if not risco_por_categoria.empty:
        categoria_maior_risco = str(risco_por_categoria.iloc[0]["categoria"])

st.markdown(
    f"""
    <div class="insight-box">
        <h3>Como nossos preços se comparam ao mercado</h3>
        <p>
            Com <strong>{fmt_int(total_prod)}</strong> produtos monitorados, o catálogo está em média
            <strong>{fmt_pct(dif_media)}</strong> em relação à média de mercado.
            Existem <strong>{fmt_int(mais_caros)}</strong> produtos mais caros que todos os concorrentes,
            concentrando <strong>{fmt_brl(receita_risco)}</strong> em receita em risco
            (<strong>{fmt_pct(perc_receita_risco)}</strong> da receita filtrada).
        </p>
        <p>
            A categoria com maior exposição é <strong>{categoria_maior_risco}</strong>.
            A decisão de preço deve considerar margem, estoque e posicionamento antes de qualquer ajuste.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
```

Add CSS for `.insight-box` in `app.py` during Task 2 or this task:

```css
.insight-box {
    border-left: 4px solid #7C3AED;
    margin: 1.5rem 0 2rem;
    padding: 1rem 1.25rem;
    background: #FFFFFF;
}
.insight-box h3 {
    color: #111827 !important;
    font-size: 1.1rem;
    margin-bottom: 0.75rem;
}
.insight-box p {
    color: #334155 !important;
    font-size: 0.92rem;
    line-height: 1.7;
}
```

- [ ] **Step 6: Update Pricing chart choices**

Replace the classification donut with horizontal bars:

```python
df_class = df_f.groupby("classificacao_preco", as_index=False).agg(
    total_produtos=("produto_id", "count"),
    receita_total=("receita_total", "sum"),
)
df_class["percentual"] = df_class["total_produtos"] / df_class["total_produtos"].sum() * 100
df_class["classificacao_label"] = df_class["classificacao_preco"].map(classification_label)
df_class["texto"] = df_class.apply(
    lambda row: f"{fmt_int(row['total_produtos'])} ({fmt_pct(row['percentual'])})",
    axis=1,
)
fig1 = px.bar(
    df_class.sort_values("total_produtos"),
    x="total_produtos",
    y="classificacao_label",
    orientation="h",
    color="classificacao_preco",
    color_discrete_map=CLASS_COLORS,
    text="texto",
    labels={"classificacao_label": "Classificação", "total_produtos": "Total de produtos"},
)
```

Keep the category competitiveness and aggregate scatter, but ensure all text labels and hovers use `fmt_pct`, `fmt_int` and `fmt_brl_compact`.

- [ ] **Step 7: Run focused validation**

Run:

```bash
uv run pytest .llm/case-01-dashboard/tests/test_utils.py -q
uv run ruff check .llm/case-01-dashboard/views/pricing.py .llm/case-01-dashboard/app.py
```

Expected: tests pass; ruff reports `All checks passed!`.

- [ ] **Step 8: Commit**

```bash
git add .llm/case-01-dashboard/views/pricing.py .llm/case-01-dashboard/app.py .llm/case-01-dashboard/tests/test_utils.py
git commit -m "visual(dashboard): amplia análise executiva de pricing" \
-m "- Adiciona filtros de categoria, marca e classificação.
- Inclui KPIs de receita em risco e diferença média vs mercado.
- Troca visualizações frágeis por gráficos com rótulos mais legíveis."
```

## Task 6: Align Workspace, Docker Context and Ignore Rules

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `.llm/case-01-dashboard/pyproject.toml`
- Modify: `.llm/case-01-dashboard/.env.example`
- Modify: `extract_load/Dockerfile`
- Modify: `transform/Dockerfile`
- Modify: `.dockerignore`

- [ ] **Step 1: Ensure dashboard package is in root workspace**

Confirm `pyproject.toml` contains:

```toml
[tool.uv.workspace]
members = ["extract_load", "transform", ".llm/case-01-dashboard"]
```

Confirm pytest paths contain:

```toml
[tool.pytest.ini_options]
testpaths = ["extract_load/tests", ".llm/case-01-dashboard/tests"]
pythonpath = ["extract_load/src", ".llm/case-01-dashboard"]
addopts = "-ra --strict-markers"
```

- [ ] **Step 2: Ensure dashboard package metadata is minimal**

`.llm/case-01-dashboard/pyproject.toml` should contain:

```toml
[project]
name = "case-01-dashboard"
version = "0.1.0"
description = "Dashboard Streamlit para consumo dos marts Gold do e-commerce"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.0.0",
    "plotly>=5.18.0",
    "psycopg2-binary>=2.9.0",
    "python-dotenv>=1.0.0",
    "sqlalchemy>=2.0.0",
    "streamlit>=1.32.0",
]

[build-system]
requires = ["hatchling>=1.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
bypass-selection = true
```

- [ ] **Step 3: Keep local env example secret-free**

`.llm/case-01-dashboard/.env.example` should contain:

```env
# Case 01 - Dashboard Streamlit
# Copie para o .env da raiz do projeto ou mantenha a variável no ambiente.
# Nunca versionar credenciais reais.

POSTGRES_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/postgres
```

- [ ] **Step 4: Make Dockerfiles aware of workspace member metadata**

In both `extract_load/Dockerfile` and `transform/Dockerfile`, add this line after copying `transform/pyproject.toml`:

```dockerfile
COPY .llm/case-01-dashboard/pyproject.toml .llm/case-01-dashboard/
```

Do not copy the whole `.llm` dashboard into the image.

- [ ] **Step 5: Allow only dashboard package metadata through Docker context**

In `.dockerignore`, replace the broad `.llm` ignore with:

```dockerignore
.llm
!.llm/case-01-dashboard/
.llm/case-01-dashboard/*
!.llm/case-01-dashboard/pyproject.toml
```

Keep `.env`, `.env.*`, `.venv`, caches and dbt artifacts ignored.

- [ ] **Step 6: Refresh lockfile**

Run:

```bash
uv lock
uv lock --check
```

Expected: lock resolves successfully and `uv lock --check` exits 0.

- [ ] **Step 7: Run non-Docker validation**

Run:

```bash
uv run pytest
uv run ruff check
```

Expected: all tests pass and ruff reports `All checks passed!`.

- [ ] **Step 8: Try Docker build if Docker Desktop is available**

Run:

```bash
docker compose build extract
docker compose build dbt
```

Expected when Docker Desktop is running: both images build past `uv sync --frozen`.

Expected when Docker Desktop is unavailable: command fails with daemon connectivity error; record this as an environment limitation, not as a dashboard failure.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock .llm/case-01-dashboard/pyproject.toml .llm/case-01-dashboard/.env.example extract_load/Dockerfile transform/Dockerfile .dockerignore
git commit -m "build(dashboard): mantém workspace uv compatível com Docker" \
-m "- Inclui o dashboard no workspace uv e no lockfile.
- Copia apenas o pyproject do dashboard nos builds de extract e dbt.
- Mantém segredos, caches e artefatos fora do contexto Docker."
```

## Task 7: Update PRD and Feature Documentation with Accent Hygiene

**Files:**
- Modify: `.llm/case-01-dashboard/PRD-dashboard.md`
- Modify: `.llm/case-01-dashboard/feature.md`

- [ ] **Step 1: Update PRD execution and filters**

Ensure `.llm/case-01-dashboard/PRD-dashboard.md` states:

````markdown
## Como executar

```bash
uv sync --all-packages
uv run pytest
uv run ruff check
python -m streamlit run .llm/case-01-dashboard/app.py
```

O dashboard roda localmente e não é publicado pelo `docker-compose.yml`.
````

Ensure it lists filters:

```markdown
- Vendas: Ano, Mês e Dia da Semana.
- Clientes: Segmento, Estado e Top N Clientes.
- Pricing: Categoria, Marca e Classificação.
```

- [ ] **Step 2: Update feature summary**

Ensure `.llm/case-01-dashboard/feature.md` includes:

```markdown
## Visão geral

Dashboard Streamlit local para análise dos marts Gold de vendas, clientes e pricing.
A navegação usa abas superiores e os filtros ficam agrupados na sidebar por domínio.

## Garantias de execução

- Usa `POSTGRES_URL` do `.env` da raiz.
- Valida colunas obrigatórias antes de calcular KPIs e gráficos.
- Mostra mensagens amigáveis para conexão inválida, colunas ausentes e filtros sem dados.
- Mantém valores monetários em `R$` em cards, tabelas, hovers e rótulos.
```

- [ ] **Step 3: Scan docs and dashboard text for mojibake**

Run:

```powershell
Select-String -Path .llm\case-01-dashboard\*.md,.llm\case-01-dashboard\*.py,.llm\case-01-dashboard\views\*.py -Pattern "Ã","ï¿½"
```

Expected: no matches.

- [ ] **Step 4: Commit**

```bash
git add .llm/case-01-dashboard/PRD-dashboard.md .llm/case-01-dashboard/feature.md
git commit -m "docs(dashboard): atualiza contrato local e filtros do case 01" \
-m "- Documenta execução local do Streamlit e ausência de serviço Compose.
- Registra filtros novos e contratos defensivos de colunas.
- Revisa textos em português com acentuação correta."
```

## Task 8: End-to-End Validation and Manual Dashboard Smoke Test

**Files:**
- No required source changes

- [ ] **Step 1: Run complete unit and lint validation**

Run:

```bash
uv lock --check
uv run ruff check
uv run pytest
```

Expected:

```text
All checks passed!
35 passed
```

The exact test count may be higher if new tests were added.

- [ ] **Step 2: Validate dbt contracts**

Run:

```bash
uv run --env-file .env --package transform dbt parse --project-dir transform --profiles-dir transform
uv run --env-file .env --package transform dbt build --project-dir transform --profiles-dir transform
```

Expected:

```text
Completed successfully
PASS=81 WARN=0 ERROR=0 SKIP=0 TOTAL=81
```

- [ ] **Step 3: Smoke test dashboard imports and mart transformations**

Run:

```bash
uv run python -c "import sys; from dotenv import load_dotenv; load_dotenv('.env', override=True); sys.path.insert(0, '.llm/case-01-dashboard'); import db, utils, views.vendas, views.clientes, views.pricing; print('dashboard imports ok')"
```

Expected:

```text
dashboard imports ok
```

- [ ] **Step 4: Run Streamlit locally**

Run:

```bash
python -m streamlit run .llm/case-01-dashboard/app.py
```

Validate visually:

- top tabs show `Vendas`, `Clientes`, `Pricing`;
- sidebar shows `Filtros - Vendas`, `Filtros - Clientes`, `Filtros - Pricing`;
- labels use `Ano`, `Mês`, `Dia da Semana`, `Segmento`, `Estado`, `Categoria`, `Marca`, `Classificação`;
- all three pages load without `KeyError`;
- empty multiselect filters show a no-data warning;
- Pricing shows expanded KPIs and executive narrative;
- monetary values display `R$`;
- percent values display `%`;
- no UI text contains mojibake.

- [ ] **Step 5: Commit final validation notes only if files changed**

If no files changed, do not commit. If smoke test requires a documentation note, commit:

```bash
git add .llm/case-01-dashboard/feature.md
git commit -m "docs(dashboard): registra validação final do case 01" \
-m "- Resume comandos de validação executados localmente.
- Registra limitação de Docker Desktop quando aplicável.
- Mantém o dashboard documentado como execução local."
```

## Self-Review

- Spec coverage: covered local Streamlit execution, `POSTGRES_URL`, no `profiles.yml`, no dashboard Compose service, KeyError prevention, filters from the image, Pricing KPIs, R$ formatting, acentuação, security, uv workspace, Docker compatibility, docs and validation.
- Red-flag scan: no prohibited incomplete or vague implementation phrases remain.
- Type consistency: helper names introduced in Task 1 are used consistently in later tasks: `FILTER_ALL`, `MissingColumnsError`, `validate_columns`, `validate_sales_columns`, `build_filter_options`, `filter_equals`, `filter_in`.
