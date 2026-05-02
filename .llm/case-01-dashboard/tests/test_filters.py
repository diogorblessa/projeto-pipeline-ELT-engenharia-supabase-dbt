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
