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
