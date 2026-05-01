import pandas as pd
import plotly.express as px
import streamlit as st
from db import get_data
from utils import (
    CLASS_COLORS,
    MissingColumnsError,
    apply_chart_style,
    build_filter_options,
    classification_label,
    filter_in,
    fmt_brl,
    fmt_brl_compact,
    fmt_int,
    fmt_pct,
    kpi_card,
    validate_pricing_columns,
)

THEME_COLOR = "#E69F00"
QUERY = "SELECT * FROM public_gold_pricing.gold_pricing_precos_competitividade"
RISK_CLASS = "MAIS_CARO_QUE_TODOS"


def _multiselect_options(values: pd.Series) -> list[str]:
    return build_filter_options(values)[1:]


def _classification_filter_options(df: pd.DataFrame) -> list[str]:
    classifications = df["classificacao_preco"].dropna().unique().tolist()
    return sorted(classifications, key=classification_label)


def _apply_pricing_filters(
    df: pd.DataFrame,
    categories: list[str],
    brands: list[str],
    classifications: list[str],
) -> pd.DataFrame:
    result = filter_in(df, "categoria", categories)
    result = filter_in(result, "marca", brands)
    return filter_in(result, "classificacao_preco", classifications)


def _pricing_metrics(df: pd.DataFrame) -> dict[str, float | int | str]:
    risk_df = df[df["classificacao_preco"] == RISK_CLASS]
    receita_total = float(df["receita_total"].sum())
    receita_risco = float(risk_df["receita_total"].sum())
    pct_receita_risco = receita_risco / receita_total * 100 if receita_total else 0.0

    if risk_df.empty:
        categoria_maior_exposicao = "Sem exposição"
    else:
        categoria_maior_exposicao = (
            risk_df.groupby("categoria")["receita_total"].sum().idxmax()
        )

    return {
        "total_produtos": len(df),
        "mais_caros": int((df["classificacao_preco"] == RISK_CLASS).sum()),
        "mais_baratos": int((df["classificacao_preco"] == "MAIS_BARATO_QUE_TODOS").sum()),
        "acima_media": int((df["classificacao_preco"] == "ACIMA_DA_MEDIA").sum()),
        "dif_media": float(df["diferenca_percentual_vs_media"].mean()),
        "receita_total": receita_total,
        "receita_risco": receita_risco,
        "pct_receita_risco": pct_receita_risco,
        "categoria_maior_exposicao": categoria_maior_exposicao,
    }


def _build_executive_narrative(metrics: dict[str, float | int | str]) -> str:
    return (
        "<div class='insight-box'>"
        "<strong>Leitura executiva:</strong> "
        f"a seleção contém {fmt_int(metrics['total_produtos'])} produtos monitorados, "
        f"com diferença média vs mercado de {fmt_pct(metrics['dif_media'])}. "
        f"Há {fmt_int(metrics['mais_caros'])} produtos mais caros que todos os concorrentes, "
        f"concentrando {fmt_brl(metrics['receita_risco'])} em receita em risco, "
        f"equivalente a {fmt_pct(metrics['pct_receita_risco'])} da receita filtrada. "
        f"A maior exposição aparece em {metrics['categoria_maior_exposicao']}. "
        "Qualquer decisão de preço deve considerar margem, estoque e posicionamento antes "
        "de aplicar reajustes."
        "</div>"
    )


def _format_alert_table(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in [
        "nosso_preco",
        "preco_medio_concorrentes",
        "preco_maximo_concorrentes",
        "receita_total",
    ]:
        result[column] = result[column].map(fmt_brl)
    result["diferenca_percentual_vs_media"] = result["diferenca_percentual_vs_media"].map(
        fmt_pct
    )
    return result.rename(
        columns={
            "produto_id": "ID do produto",
            "nome_produto": "Produto",
            "categoria": "Categoria",
            "marca": "Marca",
            "nosso_preco": "Nosso preço",
            "preco_medio_concorrentes": "Preço médio concorrentes",
            "preco_maximo_concorrentes": "Maior preço concorrente",
            "diferenca_percentual_vs_media": "Diferença vs média",
            "receita_total": "Receita total",
        }
    )


def render() -> None:
    try:
        df = get_data(QUERY)
        validate_pricing_columns(df)
    except MissingColumnsError as e:
        st.error(str(e))
        return
    except Exception:
        st.error("Não foi possível conectar ao banco de dados.")
        return

    try:
        _render_pricing_page(df)
    except Exception:
        st.error("Não foi possível renderizar a página de pricing.")
        return


def _render_pricing_page(df: pd.DataFrame) -> None:
    category_options = _multiselect_options(df["categoria"])
    brand_options = _multiselect_options(df["marca"])
    classification_options = _classification_filter_options(df)

    with st.sidebar:
        st.markdown("#### Filtros - Pricing")
        categories = st.multiselect(
            "Categoria",
            category_options,
            default=category_options,
            key="pricing_categorias",
        )
        brands = st.multiselect(
            "Marca",
            brand_options,
            default=brand_options,
            key="pricing_marcas",
        )
        classifications = st.multiselect(
            "Classificação",
            classification_options,
            default=classification_options,
            format_func=classification_label,
            key="pricing_classificacoes",
        )

    df_f = _apply_pricing_filters(df, categories, brands, classifications)

    st.markdown(
        f"<h1 style='color:#0F172A;font-size:28px;font-weight:700;"
        f"border-bottom:3px solid {THEME_COLOR};padding-bottom:8px;margin-bottom:24px'>"
        "Pricing</h1>",
        unsafe_allow_html=True,
    )

    if df_f.empty:
        st.warning("Nenhum produto encontrado para os filtros selecionados.")
        return

    metrics = _pricing_metrics(df_f)

    kpi_rows = [
        [
            ("Produtos Monitorados", fmt_int(metrics["total_produtos"])),
            ("Mais Caros que Todos", fmt_int(metrics["mais_caros"])),
            ("Mais Baratos que Todos", fmt_int(metrics["mais_baratos"])),
            ("Acima da Média", fmt_int(metrics["acima_media"])),
        ],
        [
            ("Dif. Média vs Mercado", fmt_pct(metrics["dif_media"])),
            ("Receita Total", fmt_brl(metrics["receita_total"])),
            ("Receita em Risco", fmt_brl(metrics["receita_risco"])),
            ("% Receita em Risco", fmt_pct(metrics["pct_receita_risco"])),
        ],
    ]
    for row in kpi_rows:
        columns = st.columns(4)
        for col, (label, value) in zip(columns, row, strict=True):
            col.markdown(kpi_card(label, value, THEME_COLOR), unsafe_allow_html=True)

    st.markdown(_build_executive_narrative(metrics), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 2])
    _render_classification_chart(col_a, df_f)
    _render_category_chart(col_b, df_f)
    _render_volume_chart(df_f)
    _render_alert_table(df_f)


def _render_classification_chart(container, df: pd.DataFrame) -> None:
    df_class = df.groupby("classificacao_preco", as_index=False).agg(
        total_produtos=("produto_id", "count"),
        receita_total=("receita_total", "sum"),
    )
    df_class["percentual"] = df_class["total_produtos"] / df_class["total_produtos"].sum() * 100
    df_class["classificacao_label"] = df_class["classificacao_preco"].map(classification_label)
    df_class["produtos_label"] = df_class["total_produtos"].map(fmt_int)
    df_class["percentual_label"] = df_class["percentual"].map(fmt_pct)
    df_class["receita_label"] = df_class["receita_total"].map(fmt_brl_compact)
    df_class["texto"] = df_class.apply(
        lambda row: f"{row['produtos_label']} ({row['percentual_label']})",
        axis=1,
    )
    fig = px.bar(
        df_class.sort_values("total_produtos"),
        x="total_produtos",
        y="classificacao_label",
        orientation="h",
        color="classificacao_preco",
        color_discrete_map=CLASS_COLORS,
        text="texto",
        custom_data=["produtos_label", "percentual_label", "receita_label"],
        labels={"classificacao_label": "Classificação", "total_produtos": "Produtos"},
    )
    fig.update_traces(
        hovertemplate=(
            "Classificação: %{y}<br>"
            "Produtos: %{customdata[0]}<br>"
            "Participação: %{customdata[1]}<br>"
            "Receita: %{customdata[2]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=10),
        textposition="outside",
    )
    fig.update_layout(showlegend=False)
    container.plotly_chart(
        apply_chart_style(fig, "Posicionamento vs Concorrência"),
        use_container_width=True,
        config={"displayModeBar": False},
    )


def _render_category_chart(container, df: pd.DataFrame) -> None:
    df_cat = (
        df.dropna(subset=["diferenca_percentual_vs_media"])
        .groupby("categoria", as_index=False)
        .agg(
            diferenca_percentual_vs_media=("diferenca_percentual_vs_media", "mean"),
            total_produtos=("produto_id", "count"),
            receita_total=("receita_total", "sum"),
        )
        .sort_values("diferenca_percentual_vs_media", ascending=True)
    )
    if df_cat.empty:
        container.info("Não há dados de concorrência para calcular competitividade por categoria.")
        return

    df_cat["cor"] = df_cat["diferenca_percentual_vs_media"].apply(
        lambda value: "#D55E00" if value > 0 else "#009E73"
    )
    df_cat["percentual_label"] = df_cat["diferenca_percentual_vs_media"].map(fmt_pct)
    df_cat["produtos_label"] = df_cat["total_produtos"].map(fmt_int)
    df_cat["receita_label"] = df_cat["receita_total"].map(fmt_brl_compact)
    fig = px.bar(
        df_cat,
        x="diferenca_percentual_vs_media",
        y="categoria",
        orientation="h",
        color="cor",
        color_discrete_map="identity",
        text="percentual_label" if len(df_cat) <= 12 else None,
        custom_data=["percentual_label", "produtos_label", "receita_label"],
        labels={
            "categoria": "Categoria",
            "diferenca_percentual_vs_media": "Diferença média vs mercado",
        },
    )
    fig.update_traces(
        hovertemplate=(
            "Categoria: %{y}<br>"
            "Diferença: %{customdata[0]}<br>"
            "Produtos: %{customdata[1]}<br>"
            "Receita: %{customdata[2]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=11),
        textposition="outside",
    )
    fig.update_layout(showlegend=False)
    fig.add_vline(line_dash="dash", line_color="#475569", x=0)
    container.plotly_chart(
        apply_chart_style(fig, "Competitividade por Categoria"),
        use_container_width=True,
        config={"displayModeBar": False},
    )


def _render_volume_chart(df: pd.DataFrame) -> None:
    df_volume = (
        df.dropna(subset=["diferenca_percentual_vs_media"])
        .groupby("classificacao_preco", as_index=False)
        .agg(
            diferenca_percentual_vs_media=("diferenca_percentual_vs_media", "mean"),
            quantidade_total=("quantidade_total", "sum"),
            receita_total=("receita_total", "sum"),
            total_produtos=("produto_id", "count"),
        )
    )
    if df_volume.empty:
        st.info("Não há dados suficientes para cruzar competitividade e volume de vendas.")
        return

    df_volume["classificacao_label"] = df_volume["classificacao_preco"].map(
        classification_label
    )
    df_volume["diferenca_label"] = df_volume["diferenca_percentual_vs_media"].map(fmt_pct)
    df_volume["quantidade_label"] = df_volume["quantidade_total"].map(fmt_int)
    df_volume["receita_label"] = df_volume["receita_total"].map(fmt_brl_compact)
    df_volume["produtos_label"] = df_volume["total_produtos"].map(fmt_int)
    fig = px.scatter(
        df_volume,
        x="diferenca_percentual_vs_media",
        y="quantidade_total",
        color="classificacao_preco",
        size="receita_total",
        size_max=46,
        text="classificacao_label",
        color_discrete_map=CLASS_COLORS,
        custom_data=[
            "classificacao_label",
            "diferenca_label",
            "receita_label",
            "produtos_label",
            "quantidade_label",
        ],
        labels={
            "diferenca_percentual_vs_media": "Diferença média vs mercado",
            "quantidade_total": "Quantidade vendida",
        },
    )
    fig.update_traces(
        hovertemplate=(
            "Classificação: %{customdata[0]}<br>"
            "Diferença: %{customdata[1]}<br>"
            "Quantidade: %{customdata[4]}<br>"
            "Receita: %{customdata[2]}<br>"
            "Produtos: %{customdata[3]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=10),
        textposition="top center",
    )
    fig.update_layout(showlegend=False)
    fig.add_vline(line_dash="dash", line_color="#475569", x=0)
    st.plotly_chart(
        apply_chart_style(fig, "Competitividade x Volume por Classificação"),
        use_container_width=True,
        config={"displayModeBar": False},
    )


def _render_alert_table(df: pd.DataFrame) -> None:
    st.markdown("### Produtos com maior risco de pricing")
    df_alert = (
        df[df["classificacao_preco"] == RISK_CLASS]
        .sort_values("receita_total", ascending=False)
        .head(15)
    )
    if df_alert.empty:
        st.info("Nenhum produto nesta seleção está mais caro que todos os concorrentes.")
        return

    columns = [
        "produto_id",
        "nome_produto",
        "categoria",
        "marca",
        "nosso_preco",
        "preco_medio_concorrentes",
        "preco_maximo_concorrentes",
        "diferenca_percentual_vs_media",
        "receita_total",
    ]
    st.dataframe(_format_alert_table(df_alert[columns]), use_container_width=True, hide_index=True)
