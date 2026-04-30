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
