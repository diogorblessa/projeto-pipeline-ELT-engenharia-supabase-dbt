import pandas as pd
import plotly.express as px
import streamlit as st
from db import get_data
from utils import (
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
    validate_customers_columns,
)

THEME_COLOR = "#009E73"
QUERY = "SELECT * FROM public_gold_cs.gold_customer_success_clientes_segmentacao"
TOP_N_OPTIONS = [5, 10, 15, 20, 50]


def _segment_label(value: str) -> str:
    return SEGMENT_LABELS.get(value, value)


def _segment_filter_options(df: pd.DataFrame) -> list[str]:
    segments = df["segmento_cliente"].dropna().unique().tolist()
    return [FILTER_ALL, *sorted(segments, key=_segment_label)]


def _apply_customer_filters(
    df: pd.DataFrame,
    segment_selected: str,
    state_selected: str,
) -> pd.DataFrame:
    result = filter_equals(df, "segmento_cliente", segment_selected)
    return filter_equals(result, "estado", state_selected)


def _top_customers(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    return df.nsmallest(top_n, "ranking_receita").sort_values("ranking_receita")


def _format_customer_table(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["receita_total"] = result["receita_total"].map(fmt_brl)
    result["ticket_medio"] = result["ticket_medio"].map(fmt_brl)
    result["segmento_cliente"] = result["segmento_cliente"].map(_segment_label)
    return result.rename(
        columns={
            "cliente_id": "ID do cliente",
            "nome_cliente": "Nome do cliente",
            "estado": "Estado",
            "receita_total": "Receita total",
            "total_compras": "Total de compras",
            "ticket_medio": "Ticket médio",
            "primeira_compra": "Primeira compra",
            "ultima_compra": "Última compra",
            "segmento_cliente": "Segmento",
            "ranking_receita": "Ranking por receita",
        }
    )


def render() -> None:
    try:
        df = get_data(QUERY)
        validate_customers_columns(df)
    except MissingColumnsError as e:
        st.error(str(e))
        return
    except Exception:
        st.error("Não foi possível conectar ao banco de dados.")
        return

    try:
        _render_customers_page(df)
    except Exception:
        st.error("Não foi possível renderizar a página de clientes.")
        return


def _render_customers_page(df: pd.DataFrame) -> None:
    with st.sidebar:
        st.markdown("#### Filtros - Clientes")
        segment_selected = st.selectbox(
            "Segmento",
            _segment_filter_options(df),
            format_func=_segment_label,
            key="clientes_segmento",
        )
        state_selected = st.selectbox(
            "Estado",
            build_filter_options(df["estado"]),
            key="clientes_estado",
        )
        top_n = st.selectbox(
            "Top N Clientes",
            TOP_N_OPTIONS,
            index=1,
            key="clientes_top_n",
        )

    df_f = _apply_customer_filters(df, segment_selected, state_selected)
    if df_f.empty:
        st.warning("Nenhum cliente encontrado para os filtros selecionados.")
        return

    st.markdown(
        f"<h1 style='color:#0F172A;font-size:28px;font-weight:700;"
        f"border-bottom:3px solid {THEME_COLOR};padding-bottom:8px;margin-bottom:24px'>"
        "Clientes</h1>",
        unsafe_allow_html=True,
    )

    receita_total = float(df_f["receita_total"].sum())
    total_clientes = len(df_f)
    vip_count = int((df_f["segmento_cliente"] == "VIP").sum())
    ticket_medio = float(df_f["ticket_medio"].mean())
    total_compras = int(df_f["total_compras"].sum())

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in [
        (c1, "Receita Total", fmt_brl(receita_total)),
        (c2, "Total de Clientes", fmt_int(total_clientes)),
        (c3, "Clientes VIP", fmt_int(vip_count)),
        (c4, "Ticket Médio", fmt_brl(ticket_medio)),
    ]:
        col.markdown(kpi_card(label, value, THEME_COLOR), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 2])

    df_seg = df_f.groupby("segmento_cliente", as_index=False).agg(
        total_clientes=("cliente_id", "count")
    )
    df_seg["percentual"] = df_seg["total_clientes"] / df_seg["total_clientes"].sum() * 100
    df_seg["segmento_label"] = df_seg["segmento_cliente"].map(_segment_label)
    df_seg["clientes_label"] = df_seg["total_clientes"].map(fmt_int)
    df_seg["texto"] = df_seg.apply(
        lambda row: f"{fmt_int(row['total_clientes'])} ({fmt_pct(row['percentual'])})",
        axis=1,
    )
    fig1 = px.bar(
        df_seg.sort_values("total_clientes"),
        x="total_clientes",
        y="segmento_label",
        orientation="h",
        color="segmento_cliente",
        color_discrete_map=SEGMENT_COLORS,
        text="texto",
        custom_data=["clientes_label", "texto"],
        labels={"segmento_label": "Segmento", "total_clientes": "Total de clientes"},
    )
    fig1.update_traces(
        hovertemplate=(
            "Segmento: %{y}<br>Clientes: %{customdata[0]}<br>"
            "Participação: %{customdata[1]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=11),
        textposition="outside",
    )
    fig1.update_layout(showlegend=False)
    col_a.plotly_chart(
        apply_chart_style(fig1, "Clientes por Segmento"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    df_rev_seg = df_f.groupby("segmento_cliente", as_index=False)["receita_total"].sum()
    df_rev_seg["segmento_label"] = df_rev_seg["segmento_cliente"].map(_segment_label)
    df_rev_seg["receita_label"] = df_rev_seg["receita_total"].map(fmt_brl_compact)
    fig2 = px.bar(
        df_rev_seg.sort_values("receita_total", ascending=False),
        x="segmento_label",
        y="receita_total",
        color="segmento_cliente",
        color_discrete_map=SEGMENT_COLORS,
        text="receita_label",
        custom_data=["receita_label"],
        labels={"segmento_label": "Segmento", "receita_total": "Receita total"},
    )
    fig2.update_traces(
        hovertemplate="Segmento: %{x}<br>Receita: %{customdata[0]}<extra></extra>",
        textfont=dict(color="#0F172A", size=11),
        textposition="outside",
    )
    fig2.update_layout(showlegend=False)
    col_b.plotly_chart(
        apply_chart_style(fig2, "Receita por Segmento"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    col_c, col_d = st.columns(2)

    df_top = _top_customers(df_f, top_n)
    df_top_chart = df_top.sort_values("ranking_receita", ascending=False).copy()
    df_top_chart["receita_label"] = df_top_chart["receita_total"].map(fmt_brl_compact)
    fig3 = px.bar(
        df_top_chart,
        x="receita_total",
        y="nome_cliente",
        orientation="h",
        text="receita_label" if len(df_top_chart) <= 20 else None,
        custom_data=["receita_label", "ranking_receita"],
        color_discrete_sequence=[THEME_COLOR],
        labels={"nome_cliente": "Cliente", "receita_total": "Receita total"},
    )
    fig3.update_traces(
        hovertemplate=(
            "Cliente: %{y}<br>Receita: %{customdata[0]}<br>"
            "Ranking: %{customdata[1]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=10),
        textposition="outside",
    )
    col_c.plotly_chart(
        apply_chart_style(fig3, f"Top {top_n} Clientes por Receita"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    df_estado = df_f.groupby("estado", as_index=False).agg(
        total_clientes=("cliente_id", "count"),
        receita_total=("receita_total", "sum"),
    )
    df_estado = df_estado.sort_values("receita_total", ascending=True)
    df_estado["receita_label"] = df_estado["receita_total"].map(fmt_brl_compact)
    df_estado["clientes_label"] = df_estado["total_clientes"].map(fmt_int)
    fig4 = px.bar(
        df_estado,
        x="receita_total",
        y="estado",
        orientation="h",
        text="receita_label" if len(df_estado) <= 15 else None,
        custom_data=["receita_label", "clientes_label"],
        color_discrete_sequence=["#E69F00"],
        labels={"estado": "Estado", "receita_total": "Receita total"},
    )
    fig4.update_traces(
        hovertemplate=(
            "Estado: %{y}<br>Receita: %{customdata[0]}<br>"
            "Clientes: %{customdata[1]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=10),
        textposition="outside",
    )
    col_d.plotly_chart(
        apply_chart_style(fig4, "Receita por Estado"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.markdown(f"### Top {top_n} Clientes")
    st.caption(
        f"Dados filtrados: {fmt_int(total_clientes)} clientes, {fmt_int(total_compras)} compras."
    )
    st.dataframe(_format_customer_table(df_top), use_container_width=True, hide_index=True)
