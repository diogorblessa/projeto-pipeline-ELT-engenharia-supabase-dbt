"""Painel de filtros unificado do dashboard.

Concentra registry de filtros, contrato de seleção (FilterSelection),
carregamento cacheado de opções via SELECT DISTINCT e helpers apply_*
reutilizados pelas três views.
"""

from dataclasses import dataclass
from typing import Literal

import pandas as pd
from utils import filter_equals

Page = Literal["Vendas", "Clientes", "Pricing"]
SectionId = Literal["temporal", "cliente", "produto"]


@dataclass(frozen=True)
class FilterDef:
    key: str
    label: str
    section: SectionId
    pages: tuple[Page, ...]


FILTER_REGISTRY: tuple[FilterDef, ...] = (
    FilterDef("ano",           "Ano",             "temporal", ("Vendas",)),
    FilterDef("mes",           "Mês",             "temporal", ("Vendas",)),
    FilterDef("dia_semana",    "Dia da Semana",   "temporal", ("Vendas",)),
    FilterDef("segmento",      "Segmento",        "cliente",  ("Clientes",)),
    FilterDef("estado",        "Estado",          "cliente",  ("Clientes",)),
    FilterDef("top_n",         "Top N Clientes",  "cliente",  ("Clientes",)),
    FilterDef("categoria",     "Categoria",       "produto",  ("Pricing",)),
    FilterDef("marca",         "Marca",           "produto",  ("Pricing",)),
    FilterDef("classificacao", "Classificação",   "produto",  ("Pricing",)),
)

SECTION_TITLES: dict[SectionId, str] = {
    "temporal": "Temporal",
    "cliente": "Cliente",
    "produto": "Produto",
}

FILTER_ALL = "Todos"


@dataclass(frozen=True)
class FilterSelection:
    ano: str = FILTER_ALL
    mes: str = FILTER_ALL
    dia_semana: str = FILTER_ALL
    segmento: str = FILTER_ALL
    estado: str = FILTER_ALL
    top_n: int = 10
    categoria: str = FILTER_ALL
    marca: str = FILTER_ALL
    classificacao: str = FILTER_ALL


def apply_temporal(df: pd.DataFrame, sel: FilterSelection) -> pd.DataFrame:
    df = filter_equals(df, "ano_venda", sel.ano)
    if sel.mes != FILTER_ALL:
        mes_int = MES_PT_TO_INT[sel.mes]
        df = df[df["mes_venda"] == mes_int]
    df = filter_equals(df, "dia_semana_nome", sel.dia_semana)
    return df


MES_PT: list[str] = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

MES_PT_TO_INT: dict[str, int] = {nome: i + 1 for i, nome in enumerate(MES_PT)}
