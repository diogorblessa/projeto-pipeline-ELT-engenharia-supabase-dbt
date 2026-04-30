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
