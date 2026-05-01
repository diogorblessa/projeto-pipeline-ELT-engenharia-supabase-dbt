from decimal import Decimal

import pandas as pd
import plotly.graph_objects as go
import pytest
import utils
from utils import (
    apply_chart_style,
    classification_label,
    fmt_brl,
    fmt_brl_compact,
    fmt_int,
    fmt_pct,
    kpi_card,
    month_filter_options,
    normalize_sales_columns,
)
from views import clientes, pricing


def _dataframe_with_columns(columns: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame({column: [f"{column}_value"] for column in columns})


class TestColumnContracts:
    def test_filter_all_label_is_todos(self):
        assert utils.FILTER_ALL == "Todos"

    def test_table_names_match_dashboard_marts(self):
        assert utils.SALES_TABLE == "public_gold_sales.gold_sales_vendas_temporais"
        assert (
            utils.CUSTOMERS_TABLE
            == "public_gold_cs.gold_customer_success_clientes_segmentacao"
        )
        assert utils.PRICING_TABLE == "public_gold_pricing.gold_pricing_precos_competitividade"

    def test_sales_required_columns_match_sales_mart_without_weekday_aliases(self):
        assert utils.SALES_REQUIRED_COLUMNS == (
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
        assert {"dia_da_semana", "dia_semana_nome"} == utils.SALES_WEEKDAY_ALIASES
        assert not set(utils.SALES_REQUIRED_COLUMNS).intersection(
            utils.SALES_WEEKDAY_ALIASES
        )

    def test_customers_required_columns_match_customer_mart(self):
        assert utils.CUSTOMERS_REQUIRED_COLUMNS == (
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

    def test_pricing_required_columns_match_pricing_mart(self):
        assert utils.PRICING_REQUIRED_COLUMNS == (
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

    def test_missing_columns_error_formats_message_in_portuguese(self):
        error = utils.MissingColumnsError("public.tabela", ["coluna_b", "coluna_c"])

        assert str(error) == (
            "A tabela public.tabela não contém as colunas esperadas: coluna_b, coluna_c."
        )

    def test_validate_columns_accepts_required_columns(self):
        df = _dataframe_with_columns(("coluna_a", "coluna_b"))

        result = utils.validate_columns(df, ("coluna_a", "coluna_b"), "public.tabela")

        assert result is df

    def test_validate_columns_reports_missing_columns(self):
        df = _dataframe_with_columns(("coluna_a",))

        with pytest.raises(utils.MissingColumnsError) as exc_info:
            utils.validate_columns(df, ("coluna_a", "coluna_b"), "public.tabela")

        assert str(exc_info.value) == (
            "A tabela public.tabela não contém as colunas esperadas: coluna_b."
        )

    def test_validate_sales_columns_accepts_dia_da_semana_alias(self):
        df = _dataframe_with_columns((*utils.SALES_REQUIRED_COLUMNS, "dia_da_semana"))

        result = utils.validate_sales_columns(df)

        assert result is df

    def test_validate_sales_columns_accepts_dia_semana_nome_alias(self):
        df = _dataframe_with_columns((*utils.SALES_REQUIRED_COLUMNS, "dia_semana_nome"))

        result = utils.validate_sales_columns(df)

        assert result is df

    def test_validate_sales_columns_requires_a_weekday_alias(self):
        df = _dataframe_with_columns(utils.SALES_REQUIRED_COLUMNS)

        with pytest.raises(utils.MissingColumnsError) as exc_info:
            utils.validate_sales_columns(df)

        assert str(exc_info.value) == (
            f"A tabela {utils.SALES_TABLE} não contém as colunas esperadas: "
            "dia_da_semana ou dia_semana_nome."
        )

    def test_validate_customers_columns_uses_customer_contract_and_table(self):
        df = _dataframe_with_columns(utils.CUSTOMERS_REQUIRED_COLUMNS)

        result = utils.validate_customers_columns(df)

        assert result is df

    def test_validate_customers_columns_reports_customer_table(self):
        df = _dataframe_with_columns(tuple(utils.CUSTOMERS_REQUIRED_COLUMNS[:-1]))

        with pytest.raises(utils.MissingColumnsError) as exc_info:
            utils.validate_customers_columns(df)

        assert str(exc_info.value) == (
            f"A tabela {utils.CUSTOMERS_TABLE} não contém as colunas esperadas: "
            f"{utils.CUSTOMERS_REQUIRED_COLUMNS[-1]}."
        )

    def test_validate_pricing_columns_uses_pricing_contract_and_table(self):
        df = _dataframe_with_columns(utils.PRICING_REQUIRED_COLUMNS)

        result = utils.validate_pricing_columns(df)

        assert result is df

    def test_validate_pricing_columns_reports_pricing_table(self):
        df = _dataframe_with_columns(tuple(utils.PRICING_REQUIRED_COLUMNS[:-1]))

        with pytest.raises(utils.MissingColumnsError) as exc_info:
            utils.validate_pricing_columns(df)

        assert str(exc_info.value) == (
            f"A tabela {utils.PRICING_TABLE} não contém as colunas esperadas: "
            f"{utils.PRICING_REQUIRED_COLUMNS[-1]}."
        )


class TestFilterHelpers:
    def test_build_filter_options_returns_all_and_sorted_unique_strings(self):
        values = pd.Series(["B", "A", None, "B", "C", pd.NA])

        assert utils.build_filter_options(values) == ["Todos", "A", "B", "C"]

    def test_build_filter_options_returns_numeric_values_as_strings(self):
        values = pd.Series([2026, 2024, pd.NA, 2026, 2025], dtype="Int64")

        assert utils.build_filter_options(values) == ["Todos", "2024", "2025", "2026"]

    def test_build_filter_options_sorts_numeric_values_by_number(self):
        values = pd.Series([10, 2, 1])

        assert utils.build_filter_options(values) == ["Todos", "1", "2", "10"]

    def test_build_filter_options_canonicalizes_integral_float_and_decimal_values(self):
        values = pd.Series([2026.0, Decimal("2025.00"), pd.NA, Decimal("2026.00")])

        assert utils.build_filter_options(values) == ["Todos", "2025", "2026"]

    def test_build_filter_options_strips_string_values(self):
        values = pd.Series([" B ", "A", None, "A "])

        assert utils.build_filter_options(values) == ["Todos", "A", "B"]

    def test_filter_equals_returns_dataframe_unchanged_for_all(self):
        df = pd.DataFrame({"categoria": ["A", "B"]})

        result = utils.filter_equals(df, "categoria", utils.FILTER_ALL)

        assert result is df

    def test_filter_equals_returns_matching_rows(self):
        df = pd.DataFrame({"categoria": ["A", "B", "A"]})

        result = utils.filter_equals(df, "categoria", "A")

        assert result["categoria"].tolist() == ["A", "A"]

    def test_filter_equals_matches_numeric_column_from_string_selection(self):
        df = pd.DataFrame({"ano_venda": [2025, 2026, 2026]})

        result = utils.filter_equals(df, "ano_venda", "2026")

        assert result["ano_venda"].tolist() == [2026, 2026]

    def test_filter_equals_matches_integral_float_and_decimal_from_string_selection(self):
        df = pd.DataFrame({"ano_venda": [2025, 2026.0, Decimal("2026.00")]})

        result = utils.filter_equals(df, "ano_venda", "2026")

        assert result["ano_venda"].tolist() == [2026.0, Decimal("2026.00")]

    def test_filter_equals_strips_string_values_before_comparing(self):
        df = pd.DataFrame({"categoria": [" A ", "B", "A"]})

        result = utils.filter_equals(df, "categoria", "A")

        assert result["categoria"].tolist() == [" A ", "A"]

    def test_filter_in_returns_empty_dataframe_for_empty_selection(self):
        df = pd.DataFrame({"categoria": ["A", "B"]})

        result = utils.filter_in(df, "categoria", [])

        assert result.empty
        assert list(result.columns) == ["categoria"]

    def test_filter_in_returns_matching_rows(self):
        df = pd.DataFrame({"categoria": ["A", "B", "C"]})

        result = utils.filter_in(df, "categoria", ["A", "C"])

        assert result["categoria"].tolist() == ["A", "C"]

    def test_filter_in_matches_numeric_column_from_string_selections(self):
        df = pd.DataFrame({"ano_venda": [2024, 2025, 2026]})

        result = utils.filter_in(df, "ano_venda", ["2024", "2026"])

        assert result["ano_venda"].tolist() == [2024, 2026]

    def test_filter_in_matches_mixed_numeric_representations_from_string_selections(self):
        df = pd.DataFrame({"ano_venda": [2024, 2025.0, Decimal("2026.00"), 2026.5]})

        result = utils.filter_in(df, "ano_venda", ["2024", "2026"])

        assert result["ano_venda"].tolist() == [2024, Decimal("2026.00")]


class TestClientesHelpers:
    def test_segment_filter_options_keep_raw_values_with_readable_labels(self):
        df = pd.DataFrame({"segmento_cliente": ["TOP_TIER", "VIP", "REGULAR", "VIP"]})

        options = clientes._segment_filter_options(df)

        assert options == ["Todos", "REGULAR", "TOP_TIER", "VIP"]
        assert [clientes._segment_label(option) for option in options] == [
            "Todos",
            "Regular",
            "Top tier",
            "VIP",
        ]

    def test_apply_customer_filters_uses_segment_and_state(self):
        df = pd.DataFrame(
            {
                "cliente_id": [1, 2, 3],
                "segmento_cliente": ["VIP", "REGULAR", "VIP"],
                "estado": ["SP", "RJ", "RJ"],
            }
        )

        result = clientes._apply_customer_filters(df, "VIP", "RJ")

        assert result["cliente_id"].tolist() == [3]

    def test_top_customers_limits_by_top_n_and_preserves_ranking_order(self):
        df = pd.DataFrame(
            {
                "nome_cliente": ["Cliente A", "Cliente B", "Cliente C"],
                "receita_total": [300.0, 100.0, 200.0],
                "ranking_receita": [1, 3, 2],
            }
        )

        result = clientes._top_customers(df, 2)

        assert result["nome_cliente"].tolist() == ["Cliente A", "Cliente C"]


class TestPricingHelpers:
    def test_apply_pricing_filters_uses_category_brand_and_raw_classification(self):
        df = pd.DataFrame(
            {
                "produto_id": [1, 2, 3],
                "categoria": ["Eletrônicos", "Eletrônicos", "Casa"],
                "marca": ["Marca A", "Marca B", "Marca A"],
                "classificacao_preco": [
                    "MAIS_CARO_QUE_TODOS",
                    "ACIMA_DA_MEDIA",
                    "MAIS_CARO_QUE_TODOS",
                ],
            }
        )

        result = pricing._apply_pricing_filters(
            df,
            categories=["Eletrônicos"],
            brands=["Marca A"],
            classifications=["MAIS_CARO_QUE_TODOS"],
        )

        assert result["produto_id"].tolist() == [1]

    def test_apply_pricing_filters_returns_empty_for_empty_selection(self):
        df = pd.DataFrame(
            {
                "produto_id": [1],
                "categoria": ["Eletrônicos"],
                "marca": ["Marca A"],
                "classificacao_preco": ["MAIS_CARO_QUE_TODOS"],
            }
        )

        result = pricing._apply_pricing_filters(
            df,
            categories=[],
            brands=["Marca A"],
            classifications=["MAIS_CARO_QUE_TODOS"],
        )

        assert result.empty

    def test_pricing_metrics_calculates_revenue_risk_and_exposure_category(self):
        df = pd.DataFrame(
            {
                "produto_id": [1, 2, 3],
                "categoria": ["Eletrônicos", "Casa", "Eletrônicos"],
                "classificacao_preco": [
                    "MAIS_CARO_QUE_TODOS",
                    "ACIMA_DA_MEDIA",
                    "MAIS_CARO_QUE_TODOS",
                ],
                "diferenca_percentual_vs_media": [12.0, 4.0, 8.0],
                "receita_total": [1000.0, 500.0, 3000.0],
            }
        )

        metrics = pricing._pricing_metrics(df)

        assert metrics["total_produtos"] == 3
        assert metrics["mais_caros"] == 2
        assert metrics["acima_media"] == 1
        assert metrics["receita_total"] == 4500.0
        assert metrics["receita_risco"] == 4000.0
        assert metrics["pct_receita_risco"] == pytest.approx(88.8888888889)
        assert metrics["categoria_maior_exposicao"] == "Eletrônicos"

    def test_executive_narrative_mentions_risk_context_and_decision_caution(self):
        metrics = {
            "total_produtos": 3,
            "dif_media": 8.0,
            "mais_caros": 2,
            "receita_risco": 4000.0,
            "pct_receita_risco": 88.9,
            "categoria_maior_exposicao": "Eletrônicos",
        }

        narrative = pricing._build_executive_narrative(metrics)

        assert "3 produtos monitorados" in narrative
        assert "+8.0%" in narrative
        assert "2 produtos mais caros que todos os concorrentes" in narrative
        assert "R$ 4.000,00" in narrative
        assert "+88.9%" in narrative
        assert "Eletrônicos" in narrative
        assert "margem, estoque e posicionamento" in narrative


class TestFmtBrl:
    def test_basic(self):
        assert fmt_brl(1234.56) == "R$ 1.234,56"

    def test_zero(self):
        assert fmt_brl(0) == "R$ 0,00"

    def test_large(self):
        assert fmt_brl(1_234_567.89) == "R$ 1.234.567,89"

    def test_cents_only(self):
        assert fmt_brl(0.50) == "R$ 0,50"


class TestFmtBrlCompact:
    def test_thousands(self):
        assert fmt_brl_compact(28_450) == "R$ 28,5 mil"

    def test_small_value_uses_full_currency(self):
        assert fmt_brl_compact(950) == "R$ 950,00"


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


class TestNormalizeSalesColumns:
    def test_accepts_dia_da_semana_and_decimal_month(self):
        df = pd.DataFrame(
            {
                "dia_da_semana": ["Terca", "Sabado"],
                "mes_venda": [12.0, 1.0],
            }
        )

        result = normalize_sales_columns(df)

        assert result["dia_semana_nome"].tolist() == ["Terça", "Sábado"]
        assert result["mes_venda"].tolist() == [12, 1]

    def test_accepts_existing_dia_semana_nome_column(self):
        df = pd.DataFrame({"dia_semana_nome": ["Quinta"], "mes_venda": [4.0]})

        result = normalize_sales_columns(df)

        assert result["dia_semana_nome"].tolist() == ["Quinta"]


class TestMonthFilterOptions:
    def test_returns_sorted_integer_months_without_nulls(self):
        months = pd.Series([12.0, 1.0, None, 12.0])

        assert month_filter_options(months) == [1, 12]


class TestClassificationLabel:
    def test_formats_known_pricing_classes_for_display(self):
        assert classification_label("MAIS_CARO_QUE_TODOS") == "Mais caro que todos"
        assert classification_label("SEM_DADOS") == "Sem dados"


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
