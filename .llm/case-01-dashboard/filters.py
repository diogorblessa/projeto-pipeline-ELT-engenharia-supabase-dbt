"""Painel de filtros unificado do dashboard.

Concentra registry de filtros, contrato de seleção (FilterSelection),
carregamento cacheado de opções via SELECT DISTINCT e helpers apply_*
reutilizados pelas três views.
"""

MES_PT: list[str] = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

MES_PT_TO_INT: dict[str, int] = {nome: i + 1 for i, nome in enumerate(MES_PT)}
