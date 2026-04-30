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
