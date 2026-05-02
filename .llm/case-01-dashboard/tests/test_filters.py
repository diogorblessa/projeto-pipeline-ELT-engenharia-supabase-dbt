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
