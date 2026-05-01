from decimal import ROUND_HALF_UP, Decimal

import pandas as pd
import plotly.graph_objects as go

FILTER_ALL = "Todos"

SALES_TABLE = "public_gold_sales.gold_sales_vendas_temporais"
CUSTOMERS_TABLE = "public_gold_cs.gold_customer_success_clientes_segmentacao"
PRICING_TABLE = "public_gold_pricing.gold_pricing_precos_competitividade"

SALES_REQUIRED_COLUMNS = (
    "data_venda",
    "ano_venda",
    "mes_venda",
    "dia_venda",
    "hora_venda",
    "receita_total",
    "quantidade_total",
    "total_vendas",
    "total_clientes_unicos",
    "ticket_medio",
)
SALES_WEEKDAY_ALIASES = {"dia_da_semana", "dia_semana_nome"}

CUSTOMERS_REQUIRED_COLUMNS = (
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
)

PRICING_REQUIRED_COLUMNS = (
    "produto_id",
    "nome_produto",
    "categoria",
    "marca",
    "nosso_preco",
    "preco_medio_concorrentes",
    "preco_minimo_concorrentes",
    "preco_maximo_concorrentes",
    "total_concorrentes",
    "sem_dados_concorrente",
    "diferenca_percentual_vs_media",
    "diferenca_percentual_vs_minimo",
    "classificacao_preco",
    "receita_total",
    "quantidade_total",
)

TEXT_DARK = "#0F172A"
TEXT_MUTED = "#475569"
GRID_COLOR = "#CBD5E1"
SURFACE = "#FFFFFF"

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#56B4E9", "#CC79A7", "#6B7280"]

SEGMENT_LABELS = {"VIP": "VIP", "TOP_TIER": "Top tier", "REGULAR": "Regular"}
SEGMENT_COLORS = {"VIP": "#0072B2", "TOP_TIER": "#56B4E9", "REGULAR": "#009E73"}

CLASS_LABELS = {
    "MAIS_CARO_QUE_TODOS": "Mais caro que todos",
    "ACIMA_DA_MEDIA": "Acima da média",
    "NA_MEDIA": "Na média",
    "ABAIXO_DA_MEDIA": "Abaixo da média",
    "MAIS_BARATO_QUE_TODOS": "Mais barato que todos",
    "SEM_DADOS": "Sem dados",
}

CLASS_COLORS = {
    "MAIS_CARO_QUE_TODOS": "#D55E00",
    "ACIMA_DA_MEDIA": "#E69F00",
    "NA_MEDIA": "#CC79A7",
    "ABAIXO_DA_MEDIA": "#56B4E9",
    "MAIS_BARATO_QUE_TODOS": "#009E73",
    "SEM_DADOS": "#6B7280",
}

DAY_ORDER = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
DAY_LABELS = {
    "Segunda": "Segunda",
    "Terca": "Terça",
    "Terça": "Terça",
    "Quarta": "Quarta",
    "Quinta": "Quinta",
    "Sexta": "Sexta",
    "Sabado": "Sábado",
    "Sábado": "Sábado",
    "Domingo": "Domingo",
}


class MissingColumnsError(ValueError):
    def __init__(self, table_name: str, missing: list[str] | tuple[str, ...]) -> None:
        missing_text = ", ".join(missing)
        super().__init__(
            f"A tabela {table_name} não contém as colunas esperadas: {missing_text}."
        )


def validate_columns(
    df: pd.DataFrame,
    required: tuple[str, ...],
    table_name: str,
) -> pd.DataFrame:
    missing = tuple(column for column in required if column not in df.columns)
    if missing:
        raise MissingColumnsError(table_name, missing)
    return df


def validate_sales_columns(df: pd.DataFrame) -> pd.DataFrame:
    validate_columns(df, SALES_REQUIRED_COLUMNS, SALES_TABLE)
    if not SALES_WEEKDAY_ALIASES.intersection(df.columns):
        raise MissingColumnsError(SALES_TABLE, ("dia_da_semana ou dia_semana_nome",))
    return df


def validate_customers_columns(df: pd.DataFrame) -> pd.DataFrame:
    return validate_columns(df, CUSTOMERS_REQUIRED_COLUMNS, CUSTOMERS_TABLE)


def validate_pricing_columns(df: pd.DataFrame) -> pd.DataFrame:
    return validate_columns(df, PRICING_REQUIRED_COLUMNS, PRICING_TABLE)


def build_filter_options(values: pd.Series) -> list[str]:
    clean_values = values.dropna().map(str)
    return [FILTER_ALL, *sorted(clean_values.unique().tolist())]


def filter_equals(df: pd.DataFrame, column: str, selected: str) -> pd.DataFrame:
    if selected == FILTER_ALL:
        return df
    return df[df[column].astype(str) == str(selected)]


def filter_in(df: pd.DataFrame, column: str, selected: list[str]) -> pd.DataFrame:
    if not selected:
        return df.iloc[0:0]
    return df[df[column].astype(str).isin([str(value) for value in selected])]


def fmt_brl(value: float) -> str:
    if pd.isna(value):
        value = 0
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_brl_compact(value: float) -> str:
    if pd.isna(value):
        value = 0
    value = float(value)
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        rounded = Decimal(str(value / 1_000_000)).quantize(Decimal("0.1"), ROUND_HALF_UP)
        return f"R$ {rounded} mi".replace(".", ",")
    if abs_value >= 1_000:
        rounded = Decimal(str(value / 1_000)).quantize(Decimal("0.1"), ROUND_HALF_UP)
        return f"R$ {rounded} mil".replace(".", ",")
    return fmt_brl(value)


def fmt_int(value: int) -> str:
    if pd.isna(value):
        value = 0
    return f"{int(value):,}".replace(",", ".")


def fmt_pct(value: float) -> str:
    if pd.isna(value):
        value = 0
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def classification_label(value: str) -> str:
    return CLASS_LABELS.get(value, str(value).replace("_", " ").title())


def month_filter_options(months: pd.Series) -> list[int]:
    clean = pd.to_numeric(months, errors="coerce").dropna().astype(int)
    return sorted(clean.unique().tolist())


def normalize_sales_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if "dia_semana_nome" not in result.columns and "dia_da_semana" in result.columns:
        result["dia_semana_nome"] = result["dia_da_semana"]
    if "dia_semana_nome" in result.columns:
        result["dia_semana_nome"] = result["dia_semana_nome"].map(
            lambda value: DAY_LABELS.get(str(value).strip(), str(value).strip())
        )
    if "mes_venda" in result.columns:
        result["mes_venda"] = pd.to_numeric(result["mes_venda"], errors="coerce").astype("Int64")
    return result


def kpi_card(label: str, value: str, theme_color: str) -> str:
    return f"""
    <div style="
        background:#FFFFFF;
        border-radius:8px;
        box-shadow:0 1px 3px rgba(15,23,42,0.10),0 4px 16px rgba(15,23,42,0.08);
        padding:20px 24px;
        border-left:4px solid {theme_color};
        margin-bottom:4px;
    ">
        <div style="font-size:13px;font-weight:600;color:#475569;">{label}</div>
        <div style="font-size:32px;font-weight:700;color:#0F172A;margin-top:8px;">{value}</div>
    </div>
    """


def apply_chart_style(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(family="Plus Jakarta Sans", size=16, color=TEXT_DARK)),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", color=TEXT_MUTED),
        margin=dict(l=16, r=16, t=56, b=24),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_DARK, size=12)),
        hoverlabel=dict(bgcolor=SURFACE, font=dict(color=TEXT_DARK)),
        uniformtext=dict(minsize=10, mode="show"),
    )
    fig.update_xaxes(
        gridcolor=GRID_COLOR,
        linecolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_DARK, size=11),
        title_font=dict(color=TEXT_MUTED, size=12),
    )
    fig.update_yaxes(
        gridcolor=GRID_COLOR,
        linecolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_DARK, size=11),
        title_font=dict(color=TEXT_MUTED, size=12),
    )
    return fig
