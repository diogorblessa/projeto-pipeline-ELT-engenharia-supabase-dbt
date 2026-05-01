import pandas as pd
import plotly.express as px
import streamlit as st
from db import get_data
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

THEME_COLOR = "#0072B2"
QUERY = "SELECT * FROM public_gold_sales.gold_sales_vendas_temporais"


def render():
    try:
        df = get_data(QUERY)
        df = normalize_sales_columns(df)
        validate_sales_columns(df)
    except MissingColumnsError as e:
        st.error(str(e))
        return
    except Exception:
        st.error("Não foi possível conectar ao banco de dados.")
        return

    try:
        _render_sales_page(df)
    except Exception:
        st.error("Não foi possível renderizar a página de vendas.")
        return


def _render_sales_page(df: pd.DataFrame) -> None:
    with st.sidebar:
        st.markdown("#### Filtros - Vendas")
        ano_sel = st.selectbox(
            "Ano",
            build_filter_options(df["ano_venda"]),
            key="vendas_ano",
        )
        mes_sel = st.selectbox(
            "Mês",
            [FILTER_ALL, *[str(mes) for mes in month_filter_options(df["mes_venda"])]],
            key="vendas_mes",
        )
        dia_sel = st.selectbox(
            "Dia da Semana",
            [FILTER_ALL, *DAY_ORDER],
            key="vendas_dia_semana",
        )

    df_f = filter_equals(df, "ano_venda", ano_sel)
    if mes_sel != FILTER_ALL:
        df_f = df_f[df_f["mes_venda"] == int(mes_sel)]
    df_f = filter_equals(df_f, "dia_semana_nome", dia_sel)
    if df_f.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    st.markdown(
        f"<h1 style='color:#0F172A;font-size:28px;font-weight:700;"
        f"border-bottom:3px solid {THEME_COLOR};padding-bottom:8px;margin-bottom:24px'>"
        f"📈 Vendas</h1>",
        unsafe_allow_html=True,
    )

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

    df_daily = df_f.groupby("data_venda", as_index=False)["receita_total"].sum()
    df_daily["data_venda"] = pd.to_datetime(df_daily["data_venda"])
    df_daily["receita_label"] = df_daily["receita_total"].map(fmt_brl_compact)
    fig1 = px.line(
        df_daily,
        x="data_venda",
        y="receita_total",
        labels={"data_venda": "Data da venda", "receita_total": "Receita total"},
    )
    fig1.update_traces(
        customdata=df_daily[["receita_label"]],
        fill="tozeroy",
        fillcolor="rgba(0,114,178,0.12)",
        hovertemplate="Data: %{x|%d/%m/%Y}<br>Receita: %{customdata[0]}<extra></extra>",
        line_color=THEME_COLOR,
        mode="lines+markers",
    )
    st.plotly_chart(
        apply_chart_style(fig1, "Receita Diária"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    col_a, col_b = st.columns(2)

    df_dow = df_f.groupby("dia_semana_nome", as_index=False)["receita_total"].sum()
    df_dow["dia_semana_nome"] = pd.Categorical(
        df_dow["dia_semana_nome"], categories=DAY_ORDER, ordered=True
    )
    df_dow = df_dow.sort_values("dia_semana_nome")
    df_dow["receita_label"] = df_dow["receita_total"].map(fmt_brl_compact)
    fig2 = px.bar(
        df_dow,
        x="dia_semana_nome",
        y="receita_total",
        text="receita_label",
        color_discrete_sequence=["#E69F00"],
        labels={"dia_semana_nome": "Dia da semana", "receita_total": "Receita total"},
    )
    fig2.update_traces(
        hovertemplate="Dia: %{x}<br>Receita: %{text}<extra></extra>",
        textfont=dict(color="#0F172A", size=11),
        textposition="outside",
    )
    col_a.plotly_chart(
        apply_chart_style(fig2, "Receita por Dia da Semana"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    df_hora = df_f.groupby("hora_venda", as_index=False)["total_vendas"].sum()
    df_hora["vendas_label"] = df_hora["total_vendas"].map(fmt_int)
    fig3 = px.bar(
        df_hora,
        x="hora_venda",
        y="total_vendas",
        text="vendas_label",
        color_discrete_sequence=["#56B4E9"],
        labels={"hora_venda": "Hora da venda", "total_vendas": "Total de vendas"},
    )
    fig3.update_traces(
        hovertemplate="Hora: %{x}h<br>Vendas: %{text}<extra></extra>",
        textfont=dict(color="#0F172A", size=11),
        textposition="outside",
    )
    col_b.plotly_chart(
        apply_chart_style(fig3, "Volume de Vendas por Hora"),
        use_container_width=True,
        config={"displayModeBar": False},
    )
