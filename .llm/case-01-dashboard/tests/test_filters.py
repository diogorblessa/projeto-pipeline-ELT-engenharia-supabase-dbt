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
