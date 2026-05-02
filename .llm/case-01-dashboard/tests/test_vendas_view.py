import pandas as pd
from filters import FilterSelection
from views import vendas


class _Column:
    def markdown(self, *args, **kwargs):
        return None

    def plotly_chart(self, *args, **kwargs):
        return None


class _StreamlitStub:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def markdown(self, *args, **kwargs):
        return None

    def error(self, message):
        self.errors.append(message)

    def warning(self, message):
        self.warnings.append(message)

    def columns(self, count):
        return [_Column() for _ in range(count)]

    def plotly_chart(self, *args, **kwargs):
        return None


def _sales_dataframe(data_venda: str = "data-invalida") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data_venda": [data_venda],
            "ano_venda": [2026],
            "mes_venda": [1],
            "dia_venda": [1],
            "hora_venda": [10],
            "receita_total": [100.0],
            "quantidade_total": [2],
            "total_vendas": [1],
            "total_clientes_unicos": [1],
            "ticket_medio": [100.0],
            "dia_da_semana": ["Segunda"],
        }
    )


def test_render_reports_transformation_errors_instead_of_crashing(monkeypatch):
    st_stub = _StreamlitStub()
    monkeypatch.setattr(vendas, "st", st_stub)
    monkeypatch.setattr(vendas, "get_data", lambda query: _sales_dataframe())

    vendas.render(FilterSelection())

    assert st_stub.errors == ["Não foi possível renderizar a página de vendas."]
    assert st_stub.warnings == []
