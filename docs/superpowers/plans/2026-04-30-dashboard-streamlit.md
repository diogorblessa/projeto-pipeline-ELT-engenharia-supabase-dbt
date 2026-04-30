# E-commerce Analytics Dashboard — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um dashboard Streamlit modular com 3 páginas (Vendas, Clientes, Pricing) que consome os Gold Data Marts do PostgreSQL (Supabase), com paleta Okabe-Ito acessível para daltônicos e design corporativo profissional.

**Architecture:** `app.py` injeta o CSS global e faz o roteamento. `db.py` gerencia a conexão SQLAlchemy (dois estágios: env var ou profiles.yml). `utils.py` centraliza formatadores, `kpi_card()` e `apply_chart_style()` — sem importações circulares. Cada página em `pages/` expõe uma função `render()` chamada pelo roteador.

**Tech Stack:** Python 3.10+, Streamlit ≥1.32, SQLAlchemy ≥2.0, psycopg2-binary, pandas, plotly, python-dotenv, pyyaml, pytest

---

## Mapa de Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `case-01-dashboard/app.py` | Entry point: CSS, sidebar navy, roteamento lazy |
| `case-01-dashboard/db.py` | Engine SQLAlchemy + `get_data(query) → DataFrame` |
| `case-01-dashboard/utils.py` | Formatadores BR, `kpi_card()`, `apply_chart_style()`, constantes de paleta |
| `case-01-dashboard/pages/__init__.py` | Marca o diretório como pacote Python |
| `case-01-dashboard/pages/vendas.py` | Página Vendas: 4 KPIs + 3 gráficos |
| `case-01-dashboard/pages/clientes.py` | Página Clientes: 4 KPIs + 4 gráficos + tabela |
| `case-01-dashboard/pages/pricing.py` | Página Pricing: 4 KPIs + 3 gráficos + tabela de alertas |
| `case-01-dashboard/tests/__init__.py` | Marca o diretório de testes como pacote |
| `case-01-dashboard/tests/test_utils.py` | Testes unitários de formatadores e helpers |
| `case-01-dashboard/tests/test_db.py` | Testes da camada de conexão |
| `case-01-dashboard/requirements.txt` | Dependências Python |
| `case-01-dashboard/.env.example` | Template das variáveis de ambiente |

---

## Task 1: Scaffolding — requirements, .env.example e estrutura

**Files:**
- Create: `case-01-dashboard/requirements.txt`
- Create: `case-01-dashboard/.env.example`
- Create: `case-01-dashboard/pages/__init__.py`
- Create: `case-01-dashboard/tests/__init__.py`

- [ ] **Step 1: Criar requirements.txt**

`case-01-dashboard/requirements.txt`:
```
streamlit>=1.32.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
pandas>=2.0.0
plotly>=5.18.0
python-dotenv>=1.0.0
pyyaml>=6.0.0
pytest>=8.0.0
```

- [ ] **Step 2: Criar .env.example**

`case-01-dashboard/.env.example`:
```
# Supabase session pooler (porta 5432 — NÃO use a porta 6543)
POSTGRES_URL=postgresql://postgres:<password>@<host>.supabase.co:5432/postgres
```

- [ ] **Step 3: Criar marcadores de pacote**

```bash
mkdir -p case-01-dashboard/pages case-01-dashboard/tests
touch case-01-dashboard/pages/__init__.py case-01-dashboard/tests/__init__.py
```

- [ ] **Step 4: Instalar dependências**

```bash
cd case-01-dashboard
pip install -r requirements.txt
```

Saída esperada: todos os pacotes instalados sem erros.

- [ ] **Step 5: Commit**

```bash
git add case-01-dashboard/
git commit -m "feat(dashboard): scaffolding inicial — requirements e estrutura de diretórios"
```

---

## Task 2: utils.py — Formatadores e Helpers (TDD)

**Files:**
- Create: `case-01-dashboard/utils.py`
- Create: `case-01-dashboard/tests/test_utils.py`

- [ ] **Step 1: Escrever os testes (falharão)**

`case-01-dashboard/tests/test_utils.py`:
```python
import pytest
import plotly.graph_objects as go
from utils import fmt_brl, fmt_int, fmt_pct, apply_chart_style, kpi_card


class TestFmtBrl:
    def test_basic(self):
        assert fmt_brl(1234.56) == "R$ 1.234,56"

    def test_zero(self):
        assert fmt_brl(0) == "R$ 0,00"

    def test_large(self):
        assert fmt_brl(1_234_567.89) == "R$ 1.234.567,89"

    def test_cents_only(self):
        assert fmt_brl(0.50) == "R$ 0,50"


class TestFmtInt:
    def test_basic(self):
        assert fmt_int(1234) == "1.234"

    def test_small(self):
        assert fmt_int(42) == "42"

    def test_large(self):
        assert fmt_int(1_000_000) == "1.000.000"


class TestFmtPct:
    def test_positive(self):
        assert fmt_pct(1.5) == "+1.5%"

    def test_negative(self):
        assert fmt_pct(-2.3) == "-2.3%"

    def test_zero(self):
        assert fmt_pct(0.0) == "+0.0%"


class TestApplyChartStyle:
    def test_returns_same_figure(self):
        fig = go.Figure()
        result = apply_chart_style(fig, "Título")
        assert result is fig

    def test_fundo_transparente(self):
        fig = go.Figure()
        apply_chart_style(fig, "Título")
        assert fig.layout.plot_bgcolor == "rgba(0,0,0,0)"
        assert fig.layout.paper_bgcolor == "rgba(0,0,0,0)"


class TestKpiCard:
    def test_contem_valor(self):
        html = kpi_card("Receita Total", "R$ 1.234,56", "#0072B2")
        assert "R$ 1.234,56" in html

    def test_contem_label(self):
        html = kpi_card("Receita Total", "R$ 1.234,56", "#0072B2")
        assert "Receita Total" in html

    def test_contem_cor_tema(self):
        html = kpi_card("Label", "Value", "#009E73")
        assert "#009E73" in html
```

- [ ] **Step 2: Rodar os testes — verificar que falham**

```bash
cd case-01-dashboard
python -m pytest tests/test_utils.py -v
```

Saída esperada: `ImportError: No module named 'utils'`

- [ ] **Step 3: Implementar utils.py**

`case-01-dashboard/utils.py`:
```python
import plotly.graph_objects as go

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#56B4E9", "#CC79A7", "#F0E442"]

SEGMENT_COLORS = {"VIP": "#0072B2", "TOP_TIER": "#56B4E9", "REGULAR": "#CC79A7"}

CLASS_COLORS = {
    "MAIS_CARO_QUE_TODOS": "#D55E00",
    "ACIMA_DA_MEDIA": "#E69F00",
    "NA_MEDIA": "#CC79A7",
    "ABAIXO_DA_MEDIA": "#56B4E9",
    "MAIS_BARATO_QUE_TODOS": "#009E73",
}

DAY_ORDER = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def fmt_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_int(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def fmt_pct(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def kpi_card(label: str, value: str, theme_color: str) -> str:
    return f"""
    <div style="
        background:#FFFFFF;
        border-radius:12px;
        box-shadow:0 1px 3px rgba(0,0,0,0.08),0 4px 16px rgba(0,0,0,0.06);
        padding:20px 24px;
        border-left:4px solid {theme_color};
        margin-bottom:4px;
    ">
        <div style="font-size:13px;font-weight:500;color:#64748B;">{label}</div>
        <div style="font-size:32px;font-weight:700;color:#1A2332;margin-top:8px;">{value}</div>
    </div>
    """


def apply_chart_style(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(family="Plus Jakarta Sans", size=16, color="#1A2332")),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", color="#64748B"),
        xaxis=dict(gridcolor="#E2E8F0", linecolor="#E2E8F0", zerolinecolor="#E2E8F0"),
        yaxis=dict(gridcolor="#E2E8F0", linecolor="#E2E8F0", zerolinecolor="#E2E8F0"),
        margin=dict(l=0, r=0, t=48, b=0),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig
```

- [ ] **Step 4: Rodar os testes — verificar que passam**

```bash
cd case-01-dashboard
python -m pytest tests/test_utils.py -v
```

Saída esperada: 15 testes PASSED.

- [ ] **Step 5: Commit**

```bash
git add case-01-dashboard/utils.py case-01-dashboard/tests/test_utils.py
git commit -m "feat(dashboard): utils — formatadores BR, kpi_card e apply_chart_style (Okabe-Ito)"
```

---

## Task 3: db.py — Camada de Conexão (TDD)

**Files:**
- Create: `case-01-dashboard/db.py`
- Create: `case-01-dashboard/tests/test_db.py`

- [ ] **Step 1: Escrever os testes (falharão)**

`case-01-dashboard/tests/test_db.py`:
```python
import pytest
import yaml
import pandas as pd
from unittest.mock import patch, mock_open
from sqlalchemy import create_engine, text


class TestGetEngine:
    def test_usa_postgres_url_quando_definida(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_URL", "postgresql://u:p@host:5432/db")
        with patch("db.create_engine") as mock_engine:
            import db
            db.get_engine()
            mock_engine.assert_called_once_with("postgresql://u:p@host:5432/db")

    def test_fallback_para_profiles_yml(self, monkeypatch):
        monkeypatch.delenv("POSTGRES_URL", raising=False)
        profiles_yaml = yaml.dump({
            "ecommerce": {
                "outputs": {
                    "dev": {
                        "user": "myuser",
                        "password": "mypass",
                        "host": "myhost",
                        "port": 5432,
                        "dbname": "mydb",
                    }
                }
            }
        })
        with patch("builtins.open", mock_open(read_data=profiles_yaml)), \
             patch("db.create_engine") as mock_engine:
            import db
            db.get_engine()
            mock_engine.assert_called_once_with(
                "postgresql://myuser:mypass@myhost:5432/mydb"
            )


class TestGetData:
    def test_retorna_dataframe(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE t (id INTEGER, val TEXT)"))
            conn.execute(text("INSERT INTO t VALUES (1, 'a')"))
            conn.execute(text("INSERT INTO t VALUES (2, 'b')"))
            conn.commit()

        import db
        with patch.object(db, "get_engine", return_value=engine):
            result = db.get_data("SELECT * FROM t")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["id", "val"]

    def test_resultado_vazio_e_dataframe(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE empty_t (id INTEGER)"))
            conn.commit()

        import db
        with patch.object(db, "get_engine", return_value=engine):
            result = db.get_data("SELECT * FROM empty_t")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
```

- [ ] **Step 2: Rodar os testes — verificar que falham**

```bash
cd case-01-dashboard
python -m pytest tests/test_db.py -v
```

Saída esperada: `ImportError: No module named 'db'`

- [ ] **Step 3: Implementar db.py**

`case-01-dashboard/db.py`:
```python
import os
import yaml
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text


def get_engine():
    url = os.getenv("POSTGRES_URL")
    if url:
        return create_engine(url)
    profiles_path = Path.home() / ".dbt" / "profiles.yml"
    with open(profiles_path) as f:
        profiles = yaml.safe_load(f)
    dev = profiles["ecommerce"]["outputs"]["dev"]
    url = (
        f"postgresql://{dev['user']}:{dev['password']}"
        f"@{dev['host']}:{dev['port']}/{dev['dbname']}"
    )
    return create_engine(url)


def get_data(query: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)
```

- [ ] **Step 4: Rodar os testes — verificar que passam**

```bash
cd case-01-dashboard
python -m pytest tests/test_db.py -v
```

Saída esperada: 4 testes PASSED.

- [ ] **Step 5: Rodar toda a suite**

```bash
cd case-01-dashboard
python -m pytest tests/ -v
```

Saída esperada: 19 testes PASSED.

- [ ] **Step 6: Commit**

```bash
git add case-01-dashboard/db.py case-01-dashboard/tests/test_db.py
git commit -m "feat(dashboard): db — engine SQLAlchemy com fallback para profiles.yml"
```

---

## Task 4: app.py — CSS Global, Sidebar e Roteamento

**Files:**
- Create: `case-01-dashboard/app.py`

- [ ] **Step 1: Criar app.py**

`case-01-dashboard/app.py`:
```python
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="E-commerce Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }
        .stApp {
            background-color: #F0F4F8;
        }
        [data-testid="stSidebar"] {
            background-color: #1A2B4A !important;
        }
        [data-testid="stSidebar"] * {
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] .stRadio label {
            font-size: 15px !important;
            font-weight: 500 !important;
        }
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stMultiSelect label {
            font-size: 13px !important;
            color: #94A3B8 !important;
        }
        .block-container {
            padding-top: 2rem !important;
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_nav() -> str:
    with st.sidebar:
        st.markdown(
            "<h2 style='color:#FFFFFF;font-size:20px;font-weight:700;margin-bottom:0'>📊 E-commerce</h2>"
            "<p style='color:#94A3B8;font-size:13px;margin-top:2px;margin-bottom:0'>Analytics Dashboard</p>",
            unsafe_allow_html=True,
        )
        st.divider()
        page = st.radio(
            "Navegação",
            options=["📈 Vendas", "👥 Clientes", "💰 Pricing"],
            label_visibility="collapsed",
        )
        st.divider()
    return page


def main():
    inject_css()
    page = sidebar_nav()

    if page == "📈 Vendas":
        from pages.vendas import render
        render()
    elif page == "👥 Clientes":
        from pages.clientes import render
        render()
    elif page == "💰 Pricing":
        from pages.pricing import render
        render()


main()
```

- [ ] **Step 2: Verificar que o app sobe**

```bash
cd case-01-dashboard
python -m streamlit run app.py
```

Abrir http://localhost:8501. Verificar:
- Sidebar navy (#1A2B4A) com título "📊 E-commerce / Analytics Dashboard"
- 3 opções de navegação visíveis
- Ao clicar em qualquer página, aparece `ModuleNotFoundError` (pages ainda não existem — comportamento esperado)

Pressionar Ctrl+C para parar.

- [ ] **Step 3: Commit**

```bash
git add case-01-dashboard/app.py
git commit -m "feat(dashboard): app.py — CSS corporativo, sidebar navy e roteamento"
```

---

## Task 5: pages/vendas.py — Página do Diretor Comercial

**Files:**
- Create: `case-01-dashboard/pages/vendas.py`

- [ ] **Step 1: Criar pages/vendas.py**

`case-01-dashboard/pages/vendas.py`:
```python
import streamlit as st
import pandas as pd
import plotly.express as px
from db import get_data
from utils import fmt_brl, fmt_int, kpi_card, apply_chart_style, DAY_ORDER

THEME_COLOR = "#0072B2"
QUERY = "SELECT * FROM public_gold_sales.gold_sales_vendas_temporais"


def render():
    try:
        df = get_data(QUERY)
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        return

    # Filtro de mês na sidebar
    meses = sorted(df["mes_venda"].unique().tolist())
    with st.sidebar:
        mes_sel = st.selectbox("Mês", ["Todos"] + [str(m) for m in meses], key="vendas_mes")

    df_f = df if mes_sel == "Todos" else df[df["mes_venda"] == int(mes_sel)]

    # Header
    st.markdown(
        f"<h1 style='color:#1A2332;font-size:28px;font-weight:700;"
        f"border-bottom:3px solid {THEME_COLOR};padding-bottom:8px;margin-bottom:24px'>"
        f"📈 Vendas</h1>",
        unsafe_allow_html=True,
    )

    # KPIs
    receita = float(df_f["receita_total"].sum())
    total_vendas = int(df_f["total_vendas"].sum())
    ticket = receita / total_vendas if total_vendas > 0 else 0.0
    clientes = int(df_f.groupby("data_venda")["total_clientes_unicos"].max().sum())

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in [
        (c1, "Receita Total", fmt_brl(receita)),
        (c2, "Total de Vendas", fmt_int(total_vendas)),
        (c3, "Ticket Médio", fmt_brl(ticket)),
        (c4, "Clientes Únicos", fmt_int(clientes)),
    ]:
        col.markdown(kpi_card(label, value, THEME_COLOR), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Gráfico 1 — Receita Diária (full width)
    df_daily = df_f.groupby("data_venda")["receita_total"].sum().reset_index()
    df_daily["data_venda"] = pd.to_datetime(df_daily["data_venda"])
    fig1 = px.line(df_daily, x="data_venda", y="receita_total")
    fig1.update_traces(
        line_color=THEME_COLOR,
        fill="tozeroy",
        fillcolor="rgba(0,114,178,0.10)",
    )
    st.plotly_chart(
        apply_chart_style(fig1, "Receita Diária"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    # Gráficos 2 e 3 — lado a lado
    col_a, col_b = st.columns(2)

    df_dow = df_f.groupby("dia_semana_nome")["receita_total"].sum().reset_index()
    df_dow["dia_semana_nome"] = pd.Categorical(
        df_dow["dia_semana_nome"], categories=DAY_ORDER, ordered=True
    )
    fig2 = px.bar(
        df_dow.sort_values("dia_semana_nome"),
        x="dia_semana_nome",
        y="receita_total",
        color_discrete_sequence=["#E69F00"],
    )
    col_a.plotly_chart(
        apply_chart_style(fig2, "Receita por Dia da Semana"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    df_hora = df_f.groupby("hora_venda")["total_vendas"].sum().reset_index()
    fig3 = px.bar(
        df_hora, x="hora_venda", y="total_vendas",
        color_discrete_sequence=["#56B4E9"],
    )
    col_b.plotly_chart(
        apply_chart_style(fig3, "Volume de Vendas por Hora"),
        use_container_width=True,
        config={"displayModeBar": False},
    )
```

- [ ] **Step 2: Verificar que a página renderiza com dados reais**

Garantir que o `.env` tem a `POSTGRES_URL` configurada, depois:

```bash
cd case-01-dashboard
python -m streamlit run app.py
```

Navegar para "📈 Vendas". Verificar:
- 4 cards com sombra e borda esquerda azul (`#0072B2`)
- Gráfico de linha com área preenchida azul claro
- Gráfico de barras por dia da semana em âmbar (`#E69F00`) com ordem Segunda → Domingo
- Gráfico de barras por hora em azul céu (`#56B4E9`)
- Filtro de mês na sidebar atualiza todos os KPIs e gráficos

- [ ] **Step 3: Commit**

```bash
git add case-01-dashboard/pages/vendas.py
git commit -m "feat(dashboard): página Vendas — KPIs, receita diária, dia da semana e hora"
```

---

## Task 6: pages/clientes.py — Página da Diretora de Customer Success

**Files:**
- Create: `case-01-dashboard/pages/clientes.py`

- [ ] **Step 1: Criar pages/clientes.py**

`case-01-dashboard/pages/clientes.py`:
```python
import streamlit as st
import plotly.express as px
from db import get_data
from utils import fmt_brl, fmt_int, kpi_card, apply_chart_style, SEGMENT_COLORS

THEME_COLOR = "#009E73"
QUERY = "SELECT * FROM public_gold_cs.gold_customer_success_clientes_segmentacao"


def render():
    try:
        df = get_data(QUERY)
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        return

    # Filtro de segmento na sidebar — afeta apenas a tabela detalhada
    with st.sidebar:
        seg_sel = st.selectbox(
            "Segmento (tabela)",
            ["Todos", "VIP", "TOP_TIER", "REGULAR"],
            key="clientes_seg",
        )

    # Header
    st.markdown(
        f"<h1 style='color:#1A2332;font-size:28px;font-weight:700;"
        f"border-bottom:3px solid {THEME_COLOR};padding-bottom:8px;margin-bottom:24px'>"
        f"👥 Clientes</h1>",
        unsafe_allow_html=True,
    )

    # KPIs — sempre sobre o dataset completo
    total = len(df)
    vip_count = int((df["segmento_cliente"] == "VIP").sum())
    vip_rev = float(df.loc[df["segmento_cliente"] == "VIP", "receita_total"].sum())
    ticket_medio = float(df["ticket_medio"].mean())

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in [
        (c1, "Total Clientes", fmt_int(total)),
        (c2, "Clientes VIP", fmt_int(vip_count)),
        (c3, "Receita VIP", fmt_brl(vip_rev)),
        (c4, "Ticket Médio Geral", fmt_brl(ticket_medio)),
    ]:
        col.markdown(kpi_card(label, value, THEME_COLOR), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Linha 1: Donut segmento (1/3) | Barras receita por segmento (2/3)
    col_a, col_b = st.columns([1, 2])

    df_seg = df.groupby("segmento_cliente").size().reset_index(name="count")
    fig1 = px.pie(
        df_seg, values="count", names="segmento_cliente", hole=0.5,
        color="segmento_cliente", color_discrete_map=SEGMENT_COLORS,
    )
    col_a.plotly_chart(
        apply_chart_style(fig1, "Distribuição por Segmento"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    df_rev = df.groupby("segmento_cliente")["receita_total"].sum().reset_index()
    fig2 = px.bar(
        df_rev, x="segmento_cliente", y="receita_total",
        color="segmento_cliente", color_discrete_map=SEGMENT_COLORS,
    )
    fig2.update_layout(showlegend=False)
    col_b.plotly_chart(
        apply_chart_style(fig2, "Receita por Segmento"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    # Linha 2: Top 10 (1/2) | Clientes por Estado (1/2)
    col_c, col_d = st.columns(2)

    df_top10 = df.nsmallest(10, "ranking_receita").sort_values("receita_total")
    fig3 = px.bar(
        df_top10, x="receita_total", y="nome_cliente", orientation="h",
        color_discrete_sequence=["#009E73"],
    )
    col_c.plotly_chart(
        apply_chart_style(fig3, "Top 10 Clientes por Receita"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    df_estado = (
        df.groupby("estado").size().reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    fig4 = px.bar(
        df_estado, x="estado", y="count",
        color_discrete_sequence=["#E69F00"],
    )
    col_d.plotly_chart(
        apply_chart_style(fig4, "Clientes por Estado"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    # Tabela detalhada filtrada pelo selectbox
    st.markdown("### Detalhamento de Clientes")
    df_tabela = df if seg_sel == "Todos" else df[df["segmento_cliente"] == seg_sel]
    st.dataframe(df_tabela, use_container_width=True, hide_index=True)
```

- [ ] **Step 2: Verificar que a página renderiza com dados reais**

```bash
cd case-01-dashboard
python -m streamlit run app.py
```

Navegar para "👥 Clientes". Verificar:
- 4 cards com borda esquerda teal (`#009E73`)
- Donut mostra VIP (azul), TOP_TIER (azul céu), REGULAR (lilás) — distinguíveis sem cor
- Top 10 mostra barras horizontais com nomes dos clientes
- Ao mudar o segmento no sidebar, apenas a tabela é filtrada (KPIs ficam inalterados)

- [ ] **Step 3: Commit**

```bash
git add case-01-dashboard/pages/clientes.py
git commit -m "feat(dashboard): página Clientes — segmentação VIP, top 10 e distribuição geográfica"
```

---

## Task 7: pages/pricing.py — Página do Diretor de Pricing

**Files:**
- Create: `case-01-dashboard/pages/pricing.py`

- [ ] **Step 1: Criar pages/pricing.py**

`case-01-dashboard/pages/pricing.py`:
```python
import streamlit as st
import plotly.express as px
from db import get_data
from utils import fmt_int, fmt_pct, kpi_card, apply_chart_style, CLASS_COLORS

THEME_COLOR = "#E69F00"
QUERY = "SELECT * FROM public_gold_pricing.gold_pricing_precos_competitividade"


def render():
    try:
        df = get_data(QUERY)
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        return

    # Filtro de categoria na sidebar — afeta tudo
    categorias = sorted(df["categoria"].unique().tolist())
    with st.sidebar:
        cats_sel = st.multiselect(
            "Categoria",
            categorias,
            default=categorias,
            key="pricing_cats",
        )

    df_f = df[df["categoria"].isin(cats_sel)] if cats_sel else df

    # Header
    st.markdown(
        f"<h1 style='color:#1A2332;font-size:28px;font-weight:700;"
        f"border-bottom:3px solid {THEME_COLOR};padding-bottom:8px;margin-bottom:24px'>"
        f"💰 Pricing</h1>",
        unsafe_allow_html=True,
    )

    # KPIs
    total_prod = len(df_f)
    mais_caros = int((df_f["classificacao_preco"] == "MAIS_CARO_QUE_TODOS").sum())
    mais_baratos = int((df_f["classificacao_preco"] == "MAIS_BARATO_QUE_TODOS").sum())
    dif_media = float(df_f["diferenca_percentual_vs_media"].mean())

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in [
        (c1, "Produtos Monitorados", fmt_int(total_prod)),
        (c2, "Mais Caros que Todos", fmt_int(mais_caros)),
        (c3, "Mais Baratos que Todos", fmt_int(mais_baratos)),
        (c4, "Diferença Média vs Mercado", fmt_pct(dif_media)),
    ]:
        col.markdown(kpi_card(label, value, THEME_COLOR), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Linha 1: Pie classificação (1/3) | Barras competitividade por categoria (2/3)
    col_a, col_b = st.columns([1, 2])

    df_class = df_f.groupby("classificacao_preco").size().reset_index(name="count")
    fig1 = px.pie(
        df_class, values="count", names="classificacao_preco",
        color="classificacao_preco", color_discrete_map=CLASS_COLORS,
    )
    col_a.plotly_chart(
        apply_chart_style(fig1, "Posicionamento vs Concorrência"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    df_cat = (
        df_f.groupby("categoria")["diferenca_percentual_vs_media"]
        .mean().reset_index()
        .sort_values("diferenca_percentual_vs_media", ascending=False)
    )
    df_cat["cor"] = df_cat["diferenca_percentual_vs_media"].apply(
        lambda x: "#D55E00" if x > 0 else "#009E73"
    )
    fig2 = px.bar(
        df_cat, x="categoria", y="diferenca_percentual_vs_media",
        color="cor", color_discrete_map="identity",
        text="diferenca_percentual_vs_media",
    )
    fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig2.update_layout(showlegend=False)
    col_b.plotly_chart(
        apply_chart_style(fig2, "Competitividade por Categoria"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    # Linha 2: Scatter competitividade × volume (full width)
    fig3 = px.scatter(
        df_f,
        x="diferenca_percentual_vs_media",
        y="quantidade_total",
        color="classificacao_preco",
        size="receita_total",
        size_max=40,
        color_discrete_map=CLASS_COLORS,
        hover_data=["nome_produto", "categoria", "nosso_preco"],
    )
    st.plotly_chart(
        apply_chart_style(fig3, "Competitividade × Volume de Vendas"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    # Tabela de alertas
    st.markdown("### ⚠️ Produtos em Alerta (mais caros que todos os concorrentes)")
    df_alert = df_f[df_f["classificacao_preco"] == "MAIS_CARO_QUE_TODOS"][[
        "produto_id", "nome_produto", "categoria",
        "nosso_preco", "preco_maximo_concorrentes", "diferenca_percentual_vs_media",
    ]]
    if df_alert.empty:
        st.info("Nenhum produto nesta seleção está mais caro que todos os concorrentes.")
    else:
        st.dataframe(df_alert, use_container_width=True, hide_index=True)
```

- [ ] **Step 2: Verificar que a página renderiza com dados reais**

```bash
cd case-01-dashboard
python -m streamlit run app.py
```

Navegar para "💰 Pricing". Verificar:
- 4 cards com borda esquerda âmbar (`#E69F00`)
- Pie mostra 5 classificações com cores Okabe-Ito (sem vermelho puro, sem verde puro)
- Barras de categoria com cor condicional (vermelho-tijolo para mais caro, teal para mais barato) e valores numéricos visíveis
- Scatter com tamanho proporcional à receita
- Tabela de alertas exibe apenas `MAIS_CARO_QUE_TODOS`
- Filtro de categoria atualiza KPIs, gráficos e tabela

- [ ] **Step 3: Commit**

```bash
git add case-01-dashboard/pages/pricing.py
git commit -m "feat(dashboard): página Pricing — competitividade, scatter e tabela de alertas"
```

---

## Task 8: Smoke Test Final

**Files:** nenhum novo arquivo

- [ ] **Step 1: Rodar todos os testes unitários**

```bash
cd case-01-dashboard
python -m pytest tests/ -v
```

Saída esperada:
```
tests/test_db.py::TestGetEngine::test_usa_postgres_url_quando_definida PASSED
tests/test_db.py::TestGetEngine::test_fallback_para_profiles_yml PASSED
tests/test_db.py::TestGetData::test_retorna_dataframe PASSED
tests/test_db.py::TestGetData::test_resultado_vazio_e_dataframe PASSED
tests/test_utils.py::TestFmtBrl::test_basic PASSED
tests/test_utils.py::TestFmtBrl::test_zero PASSED
tests/test_utils.py::TestFmtBrl::test_large PASSED
tests/test_utils.py::TestFmtBrl::test_cents_only PASSED
tests/test_utils.py::TestFmtInt::test_basic PASSED
tests/test_utils.py::TestFmtInt::test_small PASSED
tests/test_utils.py::TestFmtInt::test_large PASSED
tests/test_utils.py::TestFmtPct::test_positive PASSED
tests/test_utils.py::TestFmtPct::test_negative PASSED
tests/test_utils.py::TestFmtPct::test_zero PASSED
tests/test_utils.py::TestApplyChartStyle::test_returns_same_figure PASSED
tests/test_utils.py::TestApplyChartStyle::test_fundo_transparente PASSED
tests/test_utils.py::TestKpiCard::test_contem_valor PASSED
tests/test_utils.py::TestKpiCard::test_contem_label PASSED
tests/test_utils.py::TestKpiCard::test_contem_cor_tema PASSED

19 passed in X.XXs
```

- [ ] **Step 2: Configurar .env com credenciais reais**

```bash
cd case-01-dashboard
cp .env.example .env
# Editar .env com a POSTGRES_URL real do Supabase (porta 5432)
```

- [ ] **Step 3: Rodar o app completo e validar visualmente**

```bash
cd case-01-dashboard
python -m streamlit run app.py
```

Checklist visual em http://localhost:8501:
- [ ] Sidebar navy com "📊 E-commerce / Analytics Dashboard"
- [ ] Página Vendas: 4 cards com borda azul, dados reais carregados
- [ ] Gráfico de linha com área preenchida azul claro
- [ ] Filtro de mês filtra corretamente KPIs e gráficos
- [ ] Página Clientes: 4 cards com borda teal
- [ ] Donut distinguível em escala de cinza (VIP azul ≠ TOP_TIER azul céu ≠ REGULAR lilás)
- [ ] Filtro de segmento afeta apenas a tabela (KPIs não mudam)
- [ ] Página Pricing: 4 cards com borda âmbar
- [ ] Barras de categoria com vermelho-tijolo/teal conforme posicionamento
- [ ] Tabela de alertas exibe apenas produtos MAIS_CARO_QUE_TODOS
- [ ] Testar erro: definir `POSTGRES_URL=postgresql://invalid` → ver `st.error()` amigável (não traceback)

- [ ] **Step 4: Commit final**

```bash
git add case-01-dashboard/
git commit -m "feat(dashboard): case-01 completo — Streamlit, Okabe-Ito, design corporativo"
```
