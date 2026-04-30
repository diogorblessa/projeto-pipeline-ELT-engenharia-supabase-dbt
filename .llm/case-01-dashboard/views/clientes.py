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

    df_top10 = df.nsmallest(10, "ranking_receita").sort_values("ranking_receita", ascending=False)
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
