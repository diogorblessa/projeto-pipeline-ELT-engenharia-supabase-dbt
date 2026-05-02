import pandas as pd
import pytest


class TestMesPt:
    def test_mes_pt_has_twelve_names_in_calendar_order(self):
        from filters import MES_PT

        assert MES_PT == [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ]

    def test_mes_pt_to_int_round_trips(self):
        from filters import MES_PT, MES_PT_TO_INT

        assert MES_PT_TO_INT["Janeiro"] == 1
        assert MES_PT_TO_INT["Dezembro"] == 12
        for index, nome in enumerate(MES_PT):
            assert MES_PT_TO_INT[nome] == index + 1


class TestFilterRegistry:
    def test_registry_has_nine_filters(self):
        from filters import FILTER_REGISTRY

        assert len(FILTER_REGISTRY) == 9

    def test_registry_keys_are_unique(self):
        from filters import FILTER_REGISTRY

        keys = [fdef.key for fdef in FILTER_REGISTRY]
        assert len(keys) == len(set(keys))

    def test_registry_groups_filters_by_expected_sections(self):
        from filters import FILTER_REGISTRY

        by_section: dict[str, list[str]] = {}
        for fdef in FILTER_REGISTRY:
            by_section.setdefault(fdef.section, []).append(fdef.key)

        assert by_section["temporal"] == ["ano", "mes", "dia_semana"]
        assert by_section["cliente"] == ["segmento", "estado", "top_n"]
        assert by_section["produto"] == ["categoria", "marca", "classificacao"]

    def test_temporal_filters_apply_only_to_vendas(self):
        from filters import FILTER_REGISTRY

        for fdef in FILTER_REGISTRY:
            if fdef.section == "temporal":
                assert fdef.pages == ("Vendas",)

    def test_cliente_filters_apply_only_to_clientes(self):
        from filters import FILTER_REGISTRY

        for fdef in FILTER_REGISTRY:
            if fdef.section == "cliente":
                assert fdef.pages == ("Clientes",)

    def test_produto_filters_apply_only_to_pricing(self):
        from filters import FILTER_REGISTRY

        for fdef in FILTER_REGISTRY:
            if fdef.section == "produto":
                assert fdef.pages == ("Pricing",)

    def test_section_titles_cover_all_section_ids(self):
        from filters import FILTER_REGISTRY, SECTION_TITLES

        used_sections = {fdef.section for fdef in FILTER_REGISTRY}
        assert used_sections == set(SECTION_TITLES)
        assert SECTION_TITLES == {
            "temporal": "Temporal",
            "cliente": "Cliente",
            "produto": "Produto",
        }


class TestFilterSelection:
    def test_default_selection_uses_filter_all_for_strings_and_ten_for_top_n(self):
        from filters import FILTER_ALL, FilterSelection

        sel = FilterSelection()

        assert sel.ano == FILTER_ALL
        assert sel.mes == FILTER_ALL
        assert sel.dia_semana == FILTER_ALL
        assert sel.segmento == FILTER_ALL
        assert sel.estado == FILTER_ALL
        assert sel.top_n == 10
        assert sel.categoria == FILTER_ALL
        assert sel.marca == FILTER_ALL
        assert sel.classificacao == FILTER_ALL

    def test_filter_all_label_matches_utils(self):
        import filters
        import utils

        assert filters.FILTER_ALL == utils.FILTER_ALL == "Todos"

    def test_selection_is_frozen(self):
        import dataclasses

        from filters import FilterSelection

        sel = FilterSelection()
        with pytest.raises(dataclasses.FrozenInstanceError):
            sel.ano = "2025"  # type: ignore[misc]


class TestApplyTemporal:
    def _sales_df(self):
        return pd.DataFrame(
            {
                "ano_venda": [2024, 2025, 2025, 2026],
                "mes_venda": [12, 1, 6, 6],
                "dia_semana_nome": ["Segunda", "Quarta", "Segunda", "Sexta"],
                "receita_total": [100.0, 200.0, 300.0, 400.0],
            }
        )

    def test_default_selection_returns_dataframe_unchanged(self):
        from filters import FilterSelection, apply_temporal

        df = self._sales_df()
        result = apply_temporal(df, FilterSelection())

        assert result is df

    def test_filters_year(self):
        from filters import FilterSelection, apply_temporal

        df = self._sales_df()
        result = apply_temporal(df, FilterSelection(ano="2025"))

        assert result["ano_venda"].tolist() == [2025, 2025]

    def test_filters_month_using_pt_name(self):
        from filters import FilterSelection, apply_temporal

        df = self._sales_df()
        result = apply_temporal(df, FilterSelection(mes="Junho"))

        assert result["mes_venda"].tolist() == [6, 6]

    def test_filters_day_of_week(self):
        from filters import FilterSelection, apply_temporal

        df = self._sales_df()
        result = apply_temporal(df, FilterSelection(dia_semana="Segunda"))

        assert result["dia_semana_nome"].tolist() == ["Segunda", "Segunda"]

    def test_combines_year_month_and_day_of_week(self):
        from filters import FilterSelection, apply_temporal

        df = self._sales_df()
        result = apply_temporal(
            df,
            FilterSelection(ano="2025", mes="Junho", dia_semana="Segunda"),
        )

        assert result["receita_total"].tolist() == [300.0]


class TestApplyCustomer:
    def _customers_df(self):
        return pd.DataFrame(
            {
                "cliente_id": [1, 2, 3, 4],
                "segmento_cliente": ["VIP", "REGULAR", "VIP", "TOP_TIER"],
                "estado": ["SP", "RJ", "RJ", "SP"],
            }
        )

    def test_default_selection_returns_dataframe_unchanged(self):
        from filters import FilterSelection, apply_customer

        df = self._customers_df()
        result = apply_customer(df, FilterSelection())

        assert result is df

    def test_filters_segment(self):
        from filters import FilterSelection, apply_customer

        df = self._customers_df()
        result = apply_customer(df, FilterSelection(segmento="VIP"))

        assert result["cliente_id"].tolist() == [1, 3]

    def test_filters_state(self):
        from filters import FilterSelection, apply_customer

        df = self._customers_df()
        result = apply_customer(df, FilterSelection(estado="SP"))

        assert result["cliente_id"].tolist() == [1, 4]

    def test_combines_segment_and_state(self):
        from filters import FilterSelection, apply_customer

        df = self._customers_df()
        result = apply_customer(df, FilterSelection(segmento="VIP", estado="RJ"))

        assert result["cliente_id"].tolist() == [3]


class TestApplyPricing:
    def _pricing_df(self):
        return pd.DataFrame(
            {
                "produto_id": [1, 2, 3, 4],
                "categoria": ["Eletrônicos", "Eletrônicos", "Casa", "Casa"],
                "marca": ["Marca A", "Marca B", "Marca A", "Marca B"],
                "classificacao_preco": [
                    "MAIS_CARO_QUE_TODOS",
                    "ACIMA_DA_MEDIA",
                    "MAIS_BARATO_QUE_TODOS",
                    "MAIS_CARO_QUE_TODOS",
                ],
            }
        )

    def test_default_selection_returns_dataframe_unchanged(self):
        from filters import FilterSelection, apply_pricing

        df = self._pricing_df()
        result = apply_pricing(df, FilterSelection())

        assert result is df

    def test_filters_category(self):
        from filters import FilterSelection, apply_pricing

        df = self._pricing_df()
        result = apply_pricing(df, FilterSelection(categoria="Casa"))

        assert result["produto_id"].tolist() == [3, 4]

    def test_filters_brand(self):
        from filters import FilterSelection, apply_pricing

        df = self._pricing_df()
        result = apply_pricing(df, FilterSelection(marca="Marca A"))

        assert result["produto_id"].tolist() == [1, 3]

    def test_filters_classification(self):
        from filters import FilterSelection, apply_pricing

        df = self._pricing_df()
        result = apply_pricing(df, FilterSelection(classificacao="MAIS_CARO_QUE_TODOS"))

        assert result["produto_id"].tolist() == [1, 4]

    def test_combines_three_axes(self):
        from filters import FilterSelection, apply_pricing

        df = self._pricing_df()
        result = apply_pricing(
            df,
            FilterSelection(
                categoria="Eletrônicos",
                marca="Marca A",
                classificacao="MAIS_CARO_QUE_TODOS",
            ),
        )

        assert result["produto_id"].tolist() == [1]


class TestOptionsQueriesSecurity:
    def test_queries_use_distinct_and_target_expected_marts(self):
        from filters import (
            CUSTOMERS_OPTIONS_QUERY,
            PRICING_OPTIONS_QUERY,
            SALES_OPTIONS_QUERY,
        )

        for query in (SALES_OPTIONS_QUERY, CUSTOMERS_OPTIONS_QUERY, PRICING_OPTIONS_QUERY):
            assert "SELECT DISTINCT" in query.upper()

        assert "public_gold_sales.gold_sales_vendas_temporais" in SALES_OPTIONS_QUERY
        assert (
            "public_gold_cs.gold_customer_success_clientes_segmentacao"
            in CUSTOMERS_OPTIONS_QUERY
        )
        assert (
            "public_gold_pricing.gold_pricing_precos_competitividade"
            in PRICING_OPTIONS_QUERY
        )

    def test_queries_do_not_reference_pii_or_identifier_columns(self):
        from filters import (
            CUSTOMERS_OPTIONS_QUERY,
            PRICING_OPTIONS_QUERY,
            SALES_OPTIONS_QUERY,
        )

        forbidden = (
            "nome_cliente",
            "cliente_id",
            "produto_id",
            "nome_produto",
            "nosso_preco",
        )
        for query in (SALES_OPTIONS_QUERY, CUSTOMERS_OPTIONS_QUERY, PRICING_OPTIONS_QUERY):
            for column in forbidden:
                assert column not in query, f"query proibida contém {column!r}"

    def test_queries_select_only_categorical_dimensions(self):
        from filters import (
            CUSTOMERS_OPTIONS_QUERY,
            PRICING_OPTIONS_QUERY,
            SALES_OPTIONS_QUERY,
        )

        assert "ano_venda" in SALES_OPTIONS_QUERY
        assert "mes_venda" in SALES_OPTIONS_QUERY
        assert "dia_semana_nome" in SALES_OPTIONS_QUERY

        assert "segmento_cliente" in CUSTOMERS_OPTIONS_QUERY
        assert "estado" in CUSTOMERS_OPTIONS_QUERY

        assert "categoria" in PRICING_OPTIONS_QUERY
        assert "marca" in PRICING_OPTIONS_QUERY
        assert "classificacao_preco" in PRICING_OPTIONS_QUERY


class TestLoadFilterOptions:
    def test_returns_normalized_dict_with_all_expected_keys(self, monkeypatch):
        import filters
        sales_df = pd.DataFrame(
            {
                "ano_venda": [2026, 2024, 2025, 2025],
                "mes_venda": [12, 1, 6, 6],
                "dia_semana_nome": ["Segunda", "Sábado", "Quarta", "Sábado"],
            }
        )
        customers_df = pd.DataFrame(
            {
                "segmento_cliente": ["VIP", "REGULAR", "TOP_TIER", "VIP"],
                "estado": ["SP", "RJ", "MG", "RJ"],
            }
        )
        pricing_df = pd.DataFrame(
            {
                "categoria": ["Casa", "Eletrônicos", "Casa"],
                "marca": ["Marca B", "Marca A", "Marca A"],
                "classificacao_preco": [
                    "ACIMA_DA_MEDIA",
                    "MAIS_CARO_QUE_TODOS",
                    "ABAIXO_DA_MEDIA",
                ],
            }
        )

        results_by_query = {
            filters.SALES_OPTIONS_QUERY: sales_df,
            filters.CUSTOMERS_OPTIONS_QUERY: customers_df,
            filters.PRICING_OPTIONS_QUERY: pricing_df,
        }
        monkeypatch.setattr(filters, "get_data", lambda query: results_by_query[query])

        options = filters._load_filter_options_uncached()

        assert options["anos"] == [2024, 2025, 2026]
        assert options["meses"] == [1, 6, 12]
        assert options["dias_semana"] == ["Segunda", "Quarta", "Sábado"]
        assert options["segmentos"] == ["REGULAR", "TOP_TIER", "VIP"]
        assert options["estados"] == ["MG", "RJ", "SP"]
        assert options["top_n"] == [5, 10, 15, 20, 50]
        assert options["categorias"] == ["Casa", "Eletrônicos"]
        assert options["marcas"] == ["Marca A", "Marca B"]
        assert options["classificacoes"] == [
            "ABAIXO_DA_MEDIA",
            "ACIMA_DA_MEDIA",
            "MAIS_CARO_QUE_TODOS",
        ]

    def test_returns_safe_empty_options_on_database_error(self, monkeypatch):
        import filters

        def boom(query):
            raise RuntimeError("conexão recusada")

        monkeypatch.setattr(filters, "get_data", boom)

        options = filters._load_filter_options_uncached()

        assert options == {
            "anos": [],
            "meses": [],
            "dias_semana": [],
            "segmentos": [],
            "estados": [],
            "top_n": [5, 10, 15, 20, 50],
            "categorias": [],
            "marcas": [],
            "classificacoes": [],
            "_error": "conexão recusada",
        }
