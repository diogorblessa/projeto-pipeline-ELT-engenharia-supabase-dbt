"""Painel de filtros unificado do dashboard.

Concentra registry de filtros, contrato de seleção (FilterSelection),
carregamento cacheado de opções via SELECT DISTINCT e helpers apply_*
reutilizados pelas três views.
"""

from dataclasses import dataclass
from typing import Literal

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

MES_PT: list[str] = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

MES_PT_TO_INT: dict[str, int] = {nome: i + 1 for i, nome in enumerate(MES_PT)}
