"""Painel de filtros unificado do dashboard.

Concentra registry de filtros, contrato de seleção (FilterSelection),
carregamento cacheado de opções via SELECT DISTINCT e helpers apply_*
reutilizados pelas três views.
"""

from dataclasses import dataclass
from typing import Literal

import pandas as pd
import streamlit as st
from db import get_data
from utils import DAY_ORDER, classification_label, filter_equals, segment_label

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


def apply_customer(df: pd.DataFrame, sel: FilterSelection) -> pd.DataFrame:
    df = filter_equals(df, "segmento_cliente", sel.segmento)
    df = filter_equals(df, "estado", sel.estado)
    return df


def apply_pricing(df: pd.DataFrame, sel: FilterSelection) -> pd.DataFrame:
    df = filter_equals(df, "categoria", sel.categoria)
    df = filter_equals(df, "marca", sel.marca)
    df = filter_equals(df, "classificacao_preco", sel.classificacao)
    return df


def selection_from_state(state) -> FilterSelection:
    return FilterSelection(
        ano=state.get("ano", FILTER_ALL),
        mes=state.get("mes", FILTER_ALL),
        dia_semana=state.get("dia_semana", FILTER_ALL),
        segmento=state.get("segmento", FILTER_ALL),
        estado=state.get("estado", FILTER_ALL),
        top_n=state.get("top_n", 10),
        categoria=state.get("categoria", FILTER_ALL),
        marca=state.get("marca", FILTER_ALL),
        classificacao=state.get("classificacao", FILTER_ALL),
    )


MES_PT: list[str] = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

MES_PT_TO_INT: dict[str, int] = {nome: i + 1 for i, nome in enumerate(MES_PT)}

SALES_OPTIONS_QUERY = """
SELECT DISTINCT ano_venda, mes_venda, dia_semana_nome
FROM public_gold_sales.gold_sales_vendas_temporais
WHERE ano_venda IS NOT NULL
""".strip()

CUSTOMERS_OPTIONS_QUERY = """
SELECT DISTINCT segmento_cliente, estado
FROM public_gold_cs.gold_customer_success_clientes_segmentacao
""".strip()

PRICING_OPTIONS_QUERY = """
SELECT DISTINCT categoria, marca, classificacao_preco
FROM public_gold_pricing.gold_pricing_precos_competitividade
""".strip()

TOP_N_OPTIONS: list[int] = [5, 10, 15, 20, 50]


def _load_filter_options_uncached() -> dict:
    empty: dict = {
        "anos": [],
        "meses": [],
        "dias_semana": [],
        "segmentos": [],
        "estados": [],
        "top_n": TOP_N_OPTIONS,
        "categorias": [],
        "marcas": [],
        "classificacoes": [],
    }
    try:
        sales = get_data(SALES_OPTIONS_QUERY)
        customers = get_data(CUSTOMERS_OPTIONS_QUERY)
        pricing = get_data(PRICING_OPTIONS_QUERY)
    except Exception as exc:
        return {**empty, "_error": str(exc)}

    dias_unicos = set(sales["dia_semana_nome"].dropna())
    return {
        "anos": sorted(sales["ano_venda"].dropna().astype(int).unique().tolist()),
        "meses": sorted(sales["mes_venda"].dropna().astype(int).unique().tolist()),
        "dias_semana": [d for d in DAY_ORDER if d in dias_unicos],
        "segmentos": sorted(
            customers["segmento_cliente"].dropna().unique().tolist(),
            key=segment_label,
        ),
        "estados": sorted(customers["estado"].dropna().unique().tolist()),
        "top_n": TOP_N_OPTIONS,
        "categorias": sorted(pricing["categoria"].dropna().unique().tolist()),
        "marcas": sorted(pricing["marca"].dropna().unique().tolist()),
        "classificacoes": sorted(
            pricing["classificacao_preco"].dropna().unique().tolist(),
            key=classification_label,
        ),
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_filter_options() -> dict:
    return _load_filter_options_uncached()
