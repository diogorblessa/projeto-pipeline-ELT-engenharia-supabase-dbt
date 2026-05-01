# Painel de Filtros Unificado — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir os três painéis de filtros independentes do dashboard Streamlit por uma sidebar global única com 9 filtros agrupados em 3 seções (Temporal / Cliente / Produto), filtros não aplicáveis à página atual desabilitados com tooltip, persistência entre páginas e correção do retângulo preto do header.

**Architecture:** Novo módulo `filters.py` com registry declarativo, dataclass `FilterSelection`, queries `SELECT DISTINCT` cacheadas e helpers `apply_*`. `app.py` orquestra (renderiza sidebar + dispatch). Cada view recebe `FilterSelection` e aplica seu helper. Reutiliza `filter_equals` de `utils.py`. Mudança cirúrgica: zero alterações em `db.py`, `dbt`, ou marts SQL.

**Tech Stack:** Python 3.11+, Streamlit ≥1.32, pandas ≥2.0, pytest, ruff. Workspace `uv`. PostgreSQL (Supabase) via SQLAlchemy.

**Spec de referência:** `docs/superpowers/specs/2026-05-01-painel-filtros-unificado-design.md`

---

## File Structure

| Arquivo | Tipo | Responsabilidade |
|---|---|---|
| `.llm/case-01-dashboard/filters.py` | NOVO | Registry, `FilterSelection`, `load_filter_options`, `render_sidebar`, `apply_temporal/customer/pricing`, mapas Mês PT-BR |
| `.llm/case-01-dashboard/utils.py` | MODIFICAR | Adicionar `segment_label()` (espelhando `classification_label`) |
| `.llm/case-01-dashboard/app.py` | MODIFICAR | Injetar CSS do header, chamar `render_sidebar`, passar `FilterSelection` para views |
| `.llm/case-01-dashboard/views/vendas.py` | MODIFICAR | Assinatura `render(selection)`; remover bloco sidebar; chamar `apply_temporal` |
| `.llm/case-01-dashboard/views/clientes.py` | MODIFICAR | Assinatura `render(selection)`; remover bloco sidebar e `_segment_filter_options`/`_apply_customer_filters`; chamar `apply_customer`; ler `selection.top_n` |
| `.llm/case-01-dashboard/views/pricing.py` | MODIFICAR | Assinatura `render(selection)`; remover bloco sidebar e `_apply_pricing_filters`/`_multiselect_options`/`_classification_filter_options`; chamar `apply_pricing` |
| `.llm/case-01-dashboard/tests/test_filters.py` | NOVO | Testes de registry, contratos, helpers `apply_*`, segurança (anti-PII) |
| `.llm/case-01-dashboard/tests/test_utils.py` | MODIFICAR | Adicionar teste de `segment_label`; remover `TestClientesHelpers._segment_filter_options` e `TestPricingHelpers._apply_pricing_filters` (movidos/substituídos por testes em `test_filters.py`); ajustar `TestClientesHelpers._apply_customer_filters` |
| `.llm/case-01-dashboard/tests/test_vendas_view.py` | MODIFICAR | Atualizar para nova assinatura `render(selection)` |

**Princípio:** cada arquivo tem responsabilidade única. `filters.py` é o componente; views só renderizam.

---

## Task 1: Adicionar `segment_label` em utils.py

Por que: `filters.load_filter_options` precisa ordenar segmentos por rótulo legível. Hoje essa lógica vive em `views/clientes.py::_segment_label` (privado). Mover para `utils.py` espelhando `classification_label`.

**Files:**
- Modify: `.llm/case-01-dashboard/utils.py`
- Test: `.llm/case-01-dashboard/tests/test_utils.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar no fim de `tests/test_utils.py`:

```python
class TestSegmentLabel:
    def test_formats_known_segments_for_display(self):
        from utils import segment_label

        assert segment_label("VIP") == "VIP"
        assert segment_label("TOP_TIER") == "Top tier"
        assert segment_label("REGULAR") == "Regular"

    def test_falls_back_to_raw_value_for_unknown_segments(self):
        from utils import segment_label

        assert segment_label("DESCONHECIDO") == "DESCONHECIDO"
```

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_utils.py::TestSegmentLabel -v
```

Esperado: `ImportError` ou `AttributeError: module 'utils' has no attribute 'segment_label'`.

- [ ] **Step 3: Implementar**

Adicionar em `.llm/case-01-dashboard/utils.py` logo abaixo da função `classification_label` (~linha 230):

```python
def segment_label(value: str) -> str:
    return SEGMENT_LABELS.get(value, str(value))
```

- [ ] **Step 4: Rodar teste e verificar que passa**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_utils.py::TestSegmentLabel -v
```

Esperado: `2 passed`.

- [ ] **Step 5: Rodar bateria completa de testes**

```bash
uv run pytest
```

Esperado: tudo verde, incluindo testes existentes.

- [ ] **Step 6: Commit**

```bash
git add .llm/case-01-dashboard/utils.py .llm/case-01-dashboard/tests/test_utils.py
git commit -m "refactor(dashboard): expõe segment_label em utils" -m "- Espelha o padrão de classification_label para reuso fora de views/clientes.py.
- Mantém SEGMENT_LABELS como fonte de verdade.
- Prepara terreno para o módulo de filtros unificado."
```

---

## Task 2: Criar `filters.py` com constantes Mês PT-BR

Por que: começar pelo mais simples — constantes puras testáveis sem mockar Streamlit/banco.

**Files:**
- Create: `.llm/case-01-dashboard/filters.py`
- Test: `.llm/case-01-dashboard/tests/test_filters.py`

- [ ] **Step 1: Escrever teste falhando**

Criar `.llm/case-01-dashboard/tests/test_filters.py`:

```python
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
```

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestMesPt -v
```

Esperado: `ModuleNotFoundError: No module named 'filters'`.

- [ ] **Step 3: Implementar**

Criar `.llm/case-01-dashboard/filters.py`:

```python
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
```

- [ ] **Step 4: Rodar teste e verificar que passa**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestMesPt -v
```

Esperado: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/filters.py .llm/case-01-dashboard/tests/test_filters.py
git commit -m "feat(dashboard): inicia módulo filters com mapa Mês PT-BR" -m "- Cria filters.py com MES_PT em ordem do calendário.
- Adiciona MES_PT_TO_INT para conversão usada em apply_temporal.
- Estabelece arquivo base para registry, FilterSelection e helpers."
```

---

## Task 3: Definir `FilterDef`, `FILTER_REGISTRY` e `SECTION_TITLES`

Por que: registry declarativo é a fonte de verdade para "qual filtro pertence a qual seção e quais páginas o aplicam". Pura estrutura, fácil de TDD.

**Files:**
- Modify: `.llm/case-01-dashboard/filters.py`
- Test: `.llm/case-01-dashboard/tests/test_filters.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar em `tests/test_filters.py`:

```python
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
```

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestFilterRegistry -v
```

Esperado: `ImportError: cannot import name 'FILTER_REGISTRY' from 'filters'`.

- [ ] **Step 3: Implementar**

Adicionar em `.llm/case-01-dashboard/filters.py` (acima de `MES_PT`):

```python
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
```

- [ ] **Step 4: Rodar testes e verificar que passam**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py -v
```

Esperado: todos os testes de `TestFilterRegistry` e `TestMesPt` passando.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/filters.py .llm/case-01-dashboard/tests/test_filters.py
git commit -m "feat(dashboard): adiciona FilterDef e FILTER_REGISTRY" -m "- Define dataclass FilterDef com chave, rótulo, seção e páginas aplicáveis.
- Lista os 9 filtros agrupados em Temporal, Cliente e Produto.
- Mapeia SECTION_TITLES com rótulos de cabeçalho da sidebar."
```

---

## Task 4: Definir `FilterSelection` (dataclass) e `FILTER_ALL`

Por que: contrato passado das views à função render. Imutável (frozen=True), defaults seguros.

**Files:**
- Modify: `.llm/case-01-dashboard/filters.py`
- Test: `.llm/case-01-dashboard/tests/test_filters.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar em `tests/test_filters.py`:

```python
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
```

(Adicionar `import pytest` no topo do arquivo se ainda não existir.)

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestFilterSelection -v
```

Esperado: `ImportError: cannot import name 'FilterSelection' from 'filters'`.

- [ ] **Step 3: Implementar**

Adicionar em `filters.py` logo após `SECTION_TITLES`:

```python
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
```

- [ ] **Step 4: Rodar testes e verificar que passam**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestFilterSelection -v
```

Esperado: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/filters.py .llm/case-01-dashboard/tests/test_filters.py
git commit -m "feat(dashboard): define FilterSelection e FILTER_ALL" -m "- Adiciona dataclass frozen com defaults seguros para os 9 filtros.
- Reusa rótulo 'Todos' compatível com utils.FILTER_ALL.
- top_n default 10 preserva comportamento atual da página de Clientes."
```

---

## Task 5: `apply_temporal` — filtra por ano, mês e dia da semana

Por que: helper puro, fácil de TDD. Reutiliza `filter_equals` de `utils.py`.

**Files:**
- Modify: `.llm/case-01-dashboard/filters.py`
- Test: `.llm/case-01-dashboard/tests/test_filters.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar em `tests/test_filters.py`:

```python
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
```

(Adicionar `import pandas as pd` no topo do arquivo se ainda não existir.)

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestApplyTemporal -v
```

Esperado: `ImportError: cannot import name 'apply_temporal' from 'filters'`.

- [ ] **Step 3: Implementar**

Adicionar imports no topo de `filters.py` (após docstring):

```python
import pandas as pd

from utils import filter_equals
```

E adicionar a função `apply_temporal` logo abaixo da `FilterSelection`:

```python
def apply_temporal(df: pd.DataFrame, sel: FilterSelection) -> pd.DataFrame:
    df = filter_equals(df, "ano_venda", sel.ano)
    if sel.mes != FILTER_ALL:
        mes_int = MES_PT_TO_INT[sel.mes]
        df = df[df["mes_venda"] == mes_int]
    df = filter_equals(df, "dia_semana_nome", sel.dia_semana)
    return df
```

- [ ] **Step 4: Rodar testes e verificar que passam**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestApplyTemporal -v
```

Esperado: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/filters.py .llm/case-01-dashboard/tests/test_filters.py
git commit -m "feat(dashboard): adiciona apply_temporal em filters" -m "- Filtra por ano, mês (nome PT-BR) e dia da semana usando filter_equals de utils.
- Converte 'Janeiro'..'Dezembro' para inteiro via MES_PT_TO_INT.
- Retorna DataFrame inalterado quando seleção é o default."
```

---

## Task 6: `apply_customer` — filtra por segmento e estado

Por que: helper análogo ao `apply_temporal`. Top N continua sendo aplicado dentro de `views/clientes.py` via `selection.top_n`.

**Files:**
- Modify: `.llm/case-01-dashboard/filters.py`
- Test: `.llm/case-01-dashboard/tests/test_filters.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar em `tests/test_filters.py`:

```python
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
```

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestApplyCustomer -v
```

Esperado: `ImportError: cannot import name 'apply_customer' from 'filters'`.

- [ ] **Step 3: Implementar**

Adicionar em `filters.py` abaixo de `apply_temporal`:

```python
def apply_customer(df: pd.DataFrame, sel: FilterSelection) -> pd.DataFrame:
    df = filter_equals(df, "segmento_cliente", sel.segmento)
    df = filter_equals(df, "estado", sel.estado)
    return df
```

- [ ] **Step 4: Rodar testes e verificar que passam**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestApplyCustomer -v
```

Esperado: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/filters.py .llm/case-01-dashboard/tests/test_filters.py
git commit -m "feat(dashboard): adiciona apply_customer em filters" -m "- Filtra DataFrame de clientes por segmento_cliente e estado.
- Reusa filter_equals de utils para tratar 'Todos'.
- Top N continua aplicado dentro da view via selection.top_n."
```

---

## Task 7: `apply_pricing` — filtra por categoria, marca e classificação

Por que: completar o trio de helpers. Substitui `pricing._apply_pricing_filters` (que era multiselect — agora single-select com FILTER_ALL).

**Files:**
- Modify: `.llm/case-01-dashboard/filters.py`
- Test: `.llm/case-01-dashboard/tests/test_filters.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar em `tests/test_filters.py`:

```python
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
```

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestApplyPricing -v
```

Esperado: `ImportError: cannot import name 'apply_pricing' from 'filters'`.

- [ ] **Step 3: Implementar**

Adicionar em `filters.py` abaixo de `apply_customer`:

```python
def apply_pricing(df: pd.DataFrame, sel: FilterSelection) -> pd.DataFrame:
    df = filter_equals(df, "categoria", sel.categoria)
    df = filter_equals(df, "marca", sel.marca)
    df = filter_equals(df, "classificacao_preco", sel.classificacao)
    return df
```

- [ ] **Step 4: Rodar testes e verificar que passam**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestApplyPricing -v
```

Esperado: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/filters.py .llm/case-01-dashboard/tests/test_filters.py
git commit -m "feat(dashboard): adiciona apply_pricing em filters" -m "- Filtra DataFrame de pricing por categoria, marca e classificacao_preco.
- Substitui multiselect anterior por seleção única + FILTER_ALL.
- Reusa filter_equals para uniformidade entre os três helpers apply_*."
```

---

## Task 8: Constantes de query e teste anti-PII

Por que: as 3 queries `SELECT DISTINCT` precisam ser strings constantes para serem inspecionáveis e auditáveis. O teste anti-PII é uma trava de segurança contra regressões.

**Files:**
- Modify: `.llm/case-01-dashboard/filters.py`
- Test: `.llm/case-01-dashboard/tests/test_filters.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar em `tests/test_filters.py`:

```python
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
```

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestOptionsQueriesSecurity -v
```

Esperado: `ImportError: cannot import name 'SALES_OPTIONS_QUERY' from 'filters'`.

- [ ] **Step 3: Implementar**

Adicionar em `filters.py` abaixo de `MES_PT_TO_INT`:

```python
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
```

- [ ] **Step 4: Rodar testes e verificar que passam**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestOptionsQueriesSecurity -v
```

Esperado: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/filters.py .llm/case-01-dashboard/tests/test_filters.py
git commit -m "feat(dashboard): define queries de opções e trava anti-PII" -m "- Extrai SALES/CUSTOMERS/PRICING_OPTIONS_QUERY como constantes auditáveis.
- Adiciona testes garantindo SELECT DISTINCT e ausência de PII nas queries.
- Cobertura preventiva contra regressões de segurança."
```

---

## Task 9: `load_filter_options()` cacheado

Por que: invoca as 3 queries via `db.get_data`, normaliza para um dict consumido pela sidebar. Cache de 5min reduz tráfego ao banco.

**Files:**
- Modify: `.llm/case-01-dashboard/filters.py`
- Test: `.llm/case-01-dashboard/tests/test_filters.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar em `tests/test_filters.py`:

```python
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
        assert options["dias_semana"] == ["Quarta", "Sábado", "Segunda"]
        assert options["segmentos"] == ["REGULAR", "TOP_TIER", "VIP"]
        assert options["estados"] == ["MG", "RJ", "SP"]
        assert options["top_n"] == [5, 10, 15, 20, 50]
        assert options["categorias"] == ["Casa", "Eletrônicos"]
        assert options["marcas"] == ["Marca A", "Marca B"]
        assert options["classificacoes"] == [
            "MAIS_CARO_QUE_TODOS",
            "ACIMA_DA_MEDIA",
            "ABAIXO_DA_MEDIA",
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
```

Notas:
- `dias_semana` ordenado por `DAY_ORDER` (Segunda → Domingo) preservando só os presentes.
- `segmentos` ordenado por rótulo legível (`segment_label`): "Regular" < "Top tier" < "VIP" — então `REGULAR`, `TOP_TIER`, `VIP`.
- `classificacoes` ordenado por rótulo legível via `classification_label`. Os valores `MAIS_CARO_QUE_TODOS` ("Mais caro que todos"), `ACIMA_DA_MEDIA` ("Acima da média"), `ABAIXO_DA_MEDIA` ("Abaixo da média") em ordem alfabética dos rótulos: A < Aci < Mai → `ABAIXO_DA_MEDIA, ACIMA_DA_MEDIA, MAIS_CARO_QUE_TODOS`. Mas o teste espera `MAIS_CARO_QUE_TODOS, ACIMA_DA_MEDIA, ABAIXO_DA_MEDIA` — isso vem de uma ordem **canônica de negócio** definida no spec, não alfabética. Para evitar ambiguidade, definir uma `CLASS_ORDER` explícita em `filters.py` e usá-la como sort key.

Ajuste no teste: o spec diz "ordem das opções por rótulo legível". Os rótulos PT-BR são "Mais caro que todos", "Acima da média", "Abaixo da média". Em ordem alfabética: "Abaixo da média", "Acima da média", "Mais caro que todos". Vamos seguir essa ordem alfabética (consistente com `sorted(... key=classification_label)` do spec).

**Atualize o teste para refletir a ordem alfabética por rótulo:**

```python
        assert options["classificacoes"] == [
            "ABAIXO_DA_MEDIA",
            "ACIMA_DA_MEDIA",
            "MAIS_CARO_QUE_TODOS",
        ]
```

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestLoadFilterOptions -v
```

Esperado: `AttributeError: module 'filters' has no attribute '_load_filter_options_uncached'`.

- [ ] **Step 3: Implementar**

Adicionar imports no topo de `filters.py`:

```python
import pandas as pd
import streamlit as st

from db import get_data
from utils import DAY_ORDER, classification_label, filter_equals, segment_label
```

Adicionar a função abaixo das constantes de query:

```python
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
    except Exception as exc:  # noqa: BLE001 — captura defensiva, mensagem é exibida na UI
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
```

- [ ] **Step 4: Rodar testes e verificar que passam**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestLoadFilterOptions -v
```

Esperado: `2 passed`.

- [ ] **Step 5: Rodar bateria completa**

```bash
uv run pytest
```

Esperado: tudo verde.

- [ ] **Step 6: Commit**

```bash
git add .llm/case-01-dashboard/filters.py .llm/case-01-dashboard/tests/test_filters.py
git commit -m "feat(dashboard): carrega opções de filtros via DISTINCT cacheado" -m "- Adiciona _load_filter_options_uncached chamando as 3 queries auditáveis.
- Cacheia o resultado por 5 minutos via st.cache_data com TTL.
- Em caso de falha de banco, retorna estrutura vazia segura com chave _error."
```

---

## Task 10: `selection_from_state` — extrai FilterSelection do session_state

Por que: lógica testável separada da UI. `render_sidebar` renderiza widgets; `selection_from_state` constrói o objeto a partir do `st.session_state`.

**Files:**
- Modify: `.llm/case-01-dashboard/filters.py`
- Test: `.llm/case-01-dashboard/tests/test_filters.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar em `tests/test_filters.py`:

```python
class TestSelectionFromState:
    def test_uses_defaults_when_state_is_empty(self):
        from filters import FILTER_ALL, FilterSelection, selection_from_state

        sel = selection_from_state({})

        assert sel == FilterSelection()
        assert sel.ano == FILTER_ALL
        assert sel.top_n == 10

    def test_reads_each_key_from_state(self):
        from filters import selection_from_state

        state = {
            "ano": "2025",
            "mes": "Junho",
            "dia_semana": "Segunda",
            "segmento": "VIP",
            "estado": "SP",
            "top_n": 20,
            "categoria": "Eletrônicos",
            "marca": "Marca A",
            "classificacao": "MAIS_CARO_QUE_TODOS",
        }

        sel = selection_from_state(state)

        assert sel.ano == "2025"
        assert sel.mes == "Junho"
        assert sel.dia_semana == "Segunda"
        assert sel.segmento == "VIP"
        assert sel.estado == "SP"
        assert sel.top_n == 20
        assert sel.categoria == "Eletrônicos"
        assert sel.marca == "Marca A"
        assert sel.classificacao == "MAIS_CARO_QUE_TODOS"

    def test_ignores_unknown_keys_in_state(self):
        from filters import FilterSelection, selection_from_state

        sel = selection_from_state({"ano": "2025", "ruido": "ignorar"})

        assert sel.ano == "2025"
        assert sel == FilterSelection(ano="2025")
```

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestSelectionFromState -v
```

Esperado: `ImportError: cannot import name 'selection_from_state'`.

- [ ] **Step 3: Implementar**

Adicionar em `filters.py` abaixo de `apply_pricing`:

```python
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
```

(Aceita qualquer mapping com `.get()` — `dict` ou `st.session_state`.)

- [ ] **Step 4: Rodar testes e verificar que passam**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestSelectionFromState -v
```

Esperado: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/filters.py .llm/case-01-dashboard/tests/test_filters.py
git commit -m "feat(dashboard): adiciona selection_from_state em filters" -m "- Extrai FilterSelection a partir de qualquer mapping (.get-friendly).
- Aceita st.session_state ou dict puro para facilitar testes.
- Mantém defaults seguros do FilterSelection quando chave ausente."
```

---

## Task 11: `is_filter_applicable` — predicado puro de elegibilidade

Por que: lógica de "este filtro está habilitado nesta página?" precisa ser pura para ser testável e reutilizada por `render_sidebar`.

**Files:**
- Modify: `.llm/case-01-dashboard/filters.py`
- Test: `.llm/case-01-dashboard/tests/test_filters.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar em `tests/test_filters.py`:

```python
class TestIsFilterApplicable:
    def test_temporal_filters_apply_only_to_vendas(self):
        from filters import is_filter_applicable

        for key in ("ano", "mes", "dia_semana"):
            assert is_filter_applicable(key, "Vendas") is True
            assert is_filter_applicable(key, "Clientes") is False
            assert is_filter_applicable(key, "Pricing") is False

    def test_cliente_filters_apply_only_to_clientes(self):
        from filters import is_filter_applicable

        for key in ("segmento", "estado", "top_n"):
            assert is_filter_applicable(key, "Clientes") is True
            assert is_filter_applicable(key, "Vendas") is False
            assert is_filter_applicable(key, "Pricing") is False

    def test_produto_filters_apply_only_to_pricing(self):
        from filters import is_filter_applicable

        for key in ("categoria", "marca", "classificacao"):
            assert is_filter_applicable(key, "Pricing") is True
            assert is_filter_applicable(key, "Vendas") is False
            assert is_filter_applicable(key, "Clientes") is False

    def test_unknown_filter_is_not_applicable(self):
        from filters import is_filter_applicable

        assert is_filter_applicable("desconhecido", "Vendas") is False
```

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestIsFilterApplicable -v
```

Esperado: `ImportError: cannot import name 'is_filter_applicable'`.

- [ ] **Step 3: Implementar**

Adicionar em `filters.py` abaixo de `selection_from_state`:

```python
def is_filter_applicable(filter_key: str, page: Page) -> bool:
    fdef = next((f for f in FILTER_REGISTRY if f.key == filter_key), None)
    return fdef is not None and page in fdef.pages
```

- [ ] **Step 4: Rodar testes e verificar que passam**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestIsFilterApplicable -v
```

Esperado: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/filters.py .llm/case-01-dashboard/tests/test_filters.py
git commit -m "feat(dashboard): adiciona is_filter_applicable" -m "- Predicado puro consultando FILTER_REGISTRY para decidir habilitação.
- Reutilizado pela sidebar para definir disabled=True/False por filtro.
- Retorna False para chaves desconhecidas, sem levantar exceção."
```

---

## Task 12: `render_sidebar` — orquestração da UI

Por que: o componente que efetivamente desenha a sidebar com 3 seções e 9 filtros, lê o estado e devolve `FilterSelection`. Como envolve calls do Streamlit, o teste cobre apenas o *contrato* (assinatura, retorno) com stub de Streamlit.

**Files:**
- Modify: `.llm/case-01-dashboard/filters.py`
- Test: `.llm/case-01-dashboard/tests/test_filters.py`

- [ ] **Step 1: Escrever teste falhando**

Adicionar em `tests/test_filters.py`:

```python
class _SidebarStub:
    def __init__(self):
        self.markdowns: list[str] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def markdown(self, *args, **kwargs):
        if args:
            self.markdowns.append(str(args[0]))

    def warning(self, message):
        self.warnings.append(message)

    def error(self, message):
        self.errors.append(message)


class _StreamlitStub:
    def __init__(self, state=None):
        self.sidebar = _SidebarStub()
        self.session_state = state if state is not None else {}
        self.selectbox_calls: list[dict] = []
        self.button_calls: list[dict] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def selectbox(self, label, options, **kwargs):
        self.selectbox_calls.append({"label": label, "options": options, **kwargs})
        key = kwargs.get("key")
        if key in self.session_state:
            return self.session_state[key]
        return options[0]

    def button(self, label, **kwargs):
        self.button_calls.append({"label": label, **kwargs})
        return False

    def divider(self):
        return None

    def warning(self, message):
        self.warnings.append(message)

    def error(self, message):
        self.errors.append(message)

    def markdown(self, *args, **kwargs):
        return None

    def rerun(self):
        return None


class TestRenderSidebar:
    def _options(self):
        return {
            "anos": [2024, 2025],
            "meses": [1, 6, 12],
            "dias_semana": ["Segunda", "Quarta", "Sábado"],
            "segmentos": ["REGULAR", "VIP"],
            "estados": ["RJ", "SP"],
            "top_n": [5, 10, 15, 20, 50],
            "categorias": ["Casa", "Eletrônicos"],
            "marcas": ["Marca A", "Marca B"],
            "classificacoes": ["MAIS_CARO_QUE_TODOS"],
        }

    def test_returns_filter_selection_with_defaults_when_state_empty(self, monkeypatch):
        import filters

        st_stub = _StreamlitStub()
        monkeypatch.setattr(filters, "st", st_stub)
        monkeypatch.setattr(filters, "load_filter_options", lambda: self._options())

        selection = filters.render_sidebar("Vendas")

        assert isinstance(selection, filters.FilterSelection)
        assert selection.ano == filters.FILTER_ALL
        assert selection.top_n == 10

    def test_renders_nine_selectboxes_for_any_page(self, monkeypatch):
        import filters

        st_stub = _StreamlitStub()
        monkeypatch.setattr(filters, "st", st_stub)
        monkeypatch.setattr(filters, "load_filter_options", lambda: self._options())

        filters.render_sidebar("Pricing")

        labels = [call["label"] for call in st_stub.selectbox_calls]
        assert labels == [
            "Ano", "Mês", "Dia da Semana",
            "Segmento", "Estado", "Top N Clientes",
            "Categoria", "Marca", "Classificação",
        ]

    def test_disables_filters_outside_active_page(self, monkeypatch):
        import filters

        st_stub = _StreamlitStub()
        monkeypatch.setattr(filters, "st", st_stub)
        monkeypatch.setattr(filters, "load_filter_options", lambda: self._options())

        filters.render_sidebar("Vendas")

        disabled_by_label = {
            call["label"]: call.get("disabled", False) for call in st_stub.selectbox_calls
        }
        assert disabled_by_label["Ano"] is False
        assert disabled_by_label["Mês"] is False
        assert disabled_by_label["Dia da Semana"] is False
        assert disabled_by_label["Segmento"] is True
        assert disabled_by_label["Estado"] is True
        assert disabled_by_label["Top N Clientes"] is True
        assert disabled_by_label["Categoria"] is True
        assert disabled_by_label["Marca"] is True
        assert disabled_by_label["Classificação"] is True

    def test_passes_help_text_to_disabled_filters(self, monkeypatch):
        import filters

        st_stub = _StreamlitStub()
        monkeypatch.setattr(filters, "st", st_stub)
        monkeypatch.setattr(filters, "load_filter_options", lambda: self._options())

        filters.render_sidebar("Vendas")

        help_by_label = {
            call["label"]: call.get("help") for call in st_stub.selectbox_calls
        }
        assert help_by_label["Ano"] is None
        assert help_by_label["Segmento"] == "Disponível em Clientes."
        assert help_by_label["Categoria"] == "Disponível em Pricing."

    def test_uses_consistent_session_state_keys_across_pages(self, monkeypatch):
        import filters

        st_stub = _StreamlitStub()
        monkeypatch.setattr(filters, "st", st_stub)
        monkeypatch.setattr(filters, "load_filter_options", lambda: self._options())

        filters.render_sidebar("Vendas")

        keys = [call.get("key") for call in st_stub.selectbox_calls]
        assert keys == [
            "ano", "mes", "dia_semana",
            "segmento", "estado", "top_n",
            "categoria", "marca", "classificacao",
        ]

    def test_warns_when_options_failed_to_load(self, monkeypatch):
        import filters

        st_stub = _StreamlitStub()
        monkeypatch.setattr(filters, "st", st_stub)
        monkeypatch.setattr(
            filters,
            "load_filter_options",
            lambda: {**self._options(), "_error": "conexão recusada"},
        )

        filters.render_sidebar("Vendas")

        assert any(
            "Não foi possível carregar opções de filtros" in msg
            for msg in st_stub.warnings
        )

    def test_includes_reload_button(self, monkeypatch):
        import filters

        st_stub = _StreamlitStub()
        monkeypatch.setattr(filters, "st", st_stub)
        monkeypatch.setattr(filters, "load_filter_options", lambda: self._options())

        filters.render_sidebar("Vendas")

        button_labels = [call["label"] for call in st_stub.button_calls]
        assert "Recarregar opções" in button_labels
```

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestRenderSidebar -v
```

Esperado: `AttributeError: module 'filters' has no attribute 'render_sidebar'`.

- [ ] **Step 3: Implementar**

Adicionar em `filters.py` abaixo de `is_filter_applicable`:

```python
def _options_for(filter_key: str, options: dict) -> tuple[list, callable | None]:
    """Devolve (lista_de_opcoes_com_todos, format_func) para um filtro do registry."""
    if filter_key == "ano":
        anos = options["anos"]
        return [FILTER_ALL, *[str(ano) for ano in anos]], None
    if filter_key == "mes":
        meses_int = options["meses"]
        return [FILTER_ALL, *[MES_PT[m - 1] for m in meses_int if 1 <= m <= 12]], None
    if filter_key == "dia_semana":
        return [FILTER_ALL, *options["dias_semana"]], None
    if filter_key == "segmento":
        return [FILTER_ALL, *options["segmentos"]], lambda v: segment_label(v) if v != FILTER_ALL else FILTER_ALL
    if filter_key == "estado":
        return [FILTER_ALL, *options["estados"]], None
    if filter_key == "top_n":
        return options["top_n"], None
    if filter_key == "categoria":
        return [FILTER_ALL, *options["categorias"]], None
    if filter_key == "marca":
        return [FILTER_ALL, *options["marcas"]], None
    if filter_key == "classificacao":
        return [FILTER_ALL, *options["classificacoes"]], lambda v: classification_label(v) if v != FILTER_ALL else FILTER_ALL
    return [FILTER_ALL], None


def render_sidebar(page: Page) -> FilterSelection:
    options = load_filter_options()
    error = options.get("_error")

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="sidebar-eyebrow">E-commerce Analytics</div>
                <h1 class="sidebar-title">Relatório Analítico</h1>
                <p class="sidebar-description">
                    Visão estratégica de vendas, clientes e pricing.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        if error:
            st.warning(
                "Não foi possível carregar opções de filtros. "
                "Páginas operam sem filtragem."
            )

        last_section = None
        for fdef in FILTER_REGISTRY:
            if fdef.section != last_section:
                st.markdown(
                    f'<div class="sidebar-section-title">{SECTION_TITLES[fdef.section].upper()}</div>',
                    unsafe_allow_html=True,
                )
                last_section = fdef.section

            applies = is_filter_applicable(fdef.key, page)
            choices, format_func = _options_for(fdef.key, options)
            help_text = (
                None
                if applies
                else f"Disponível em {', '.join(fdef.pages)}."
            )
            kwargs = {
                "options": choices,
                "key": fdef.key,
                "disabled": not applies,
                "help": help_text,
            }
            if format_func is not None:
                kwargs["format_func"] = format_func
            st.selectbox(fdef.label, **kwargs)

        st.divider()
        if st.button("Recarregar opções", help="Limpa o cache e busca novas opções no banco."):
            load_filter_options.clear()
            st.rerun()

    return selection_from_state(st.session_state)
```

Notas:
- O stub de teste não implementa `st.rerun`. Como o botão sempre devolve `False` no stub, o caminho `if st.button(...)` é falso e `st.rerun` não é chamado nos testes.
- O bloco `if error` usa `st.warning` direto (renderizado dentro do `with st.sidebar`). O stub registra em `sidebar.warnings`.

- [ ] **Step 4: Rodar testes e verificar que passam**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_filters.py::TestRenderSidebar -v
```

Esperado: `7 passed`.

- [ ] **Step 5: Rodar bateria completa**

```bash
uv run pytest
```

Esperado: tudo verde.

- [ ] **Step 6: Commit**

```bash
git add .llm/case-01-dashboard/filters.py .llm/case-01-dashboard/tests/test_filters.py
git commit -m "feat(dashboard): renderiza sidebar global com 9 filtros agrupados" -m "- Cria render_sidebar exibindo Temporal, Cliente e Produto em blocos.
- Desabilita filtros fora da página ativa com tooltip explicativo via help.
- Inclui botão 'Recarregar opções' que limpa o cache de DISTINCT."
```

---

## Task 13: Refatorar `views/vendas.py` para receber `FilterSelection`

Por que: a view não renderiza mais a sidebar. Recebe a seleção e aplica `apply_temporal`.

**Files:**
- Modify: `.llm/case-01-dashboard/views/vendas.py`
- Modify: `.llm/case-01-dashboard/tests/test_vendas_view.py`

- [ ] **Step 1: Atualizar teste de vendas**

Substituir o conteúdo de `.llm/case-01-dashboard/tests/test_vendas_view.py` por:

```python
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
```

- [ ] **Step 2: Rodar teste e verificar que falha**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_vendas_view.py -v
```

Esperado: falha em `vendas.render(FilterSelection())` com `TypeError` (signatures não batem) ou erro em `from filters import FilterSelection`.

- [ ] **Step 3: Refatorar `views/vendas.py`**

Substituir todo o arquivo `.llm/case-01-dashboard/views/vendas.py` por:

```python
import pandas as pd
import plotly.express as px
import streamlit as st
from db import get_data
from filters import FilterSelection, apply_temporal
from utils import (
    DAY_ORDER,
    MissingColumnsError,
    apply_chart_style,
    fmt_brl,
    fmt_brl_compact,
    fmt_int,
    kpi_card,
    normalize_sales_columns,
    validate_sales_columns,
)

THEME_COLOR = "#0072B2"
QUERY = "SELECT * FROM public_gold_sales.gold_sales_vendas_temporais"


def render(selection: FilterSelection) -> None:
    try:
        df = get_data(QUERY)
        df = normalize_sales_columns(df)
        validate_sales_columns(df)
    except MissingColumnsError as e:
        st.error(str(e))
        return
    except Exception:
        st.error("Não foi possível conectar ao banco de dados.")
        return

    try:
        _render_sales_page(df, selection)
    except Exception:
        st.error("Não foi possível renderizar a página de vendas.")
        return


def _render_sales_page(df: pd.DataFrame, selection: FilterSelection) -> None:
    df_f = apply_temporal(df, selection)
    if df_f.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    st.markdown(
        f"<h1 style='color:#0F172A;font-size:28px;font-weight:700;"
        f"border-bottom:3px solid {THEME_COLOR};padding-bottom:8px;margin-bottom:24px'>"
        f"📈 Vendas</h1>",
        unsafe_allow_html=True,
    )

    receita = float(df_f["receita_total"].sum())
    total_vendas = int(df_f["total_vendas"].sum())
    ticket = receita / total_vendas if total_vendas > 0 else 0.0
    clientes = int(df_f.groupby("data_venda")["total_clientes_unicos"].max().sum())

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in [
        (c1, "Receita Total", fmt_brl(receita)),
        (c2, "Total de Vendas", fmt_int(total_vendas)),
        (c3, "Ticket Médio", fmt_brl(ticket)),
        (c4, "Clientes Únicos", fmt_int(clientes)),
    ]:
        col.markdown(kpi_card(label, value, THEME_COLOR), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    df_daily = df_f.groupby("data_venda", as_index=False)["receita_total"].sum()
    df_daily["data_venda"] = pd.to_datetime(df_daily["data_venda"])
    df_daily["receita_label"] = df_daily["receita_total"].map(fmt_brl_compact)
    fig1 = px.line(
        df_daily,
        x="data_venda",
        y="receita_total",
        labels={"data_venda": "Data da venda", "receita_total": "Receita total"},
    )
    fig1.update_traces(
        customdata=df_daily[["receita_label"]],
        fill="tozeroy",
        fillcolor="rgba(0,114,178,0.12)",
        hovertemplate="Data: %{x|%d/%m/%Y}<br>Receita: %{customdata[0]}<extra></extra>",
        line_color=THEME_COLOR,
        mode="lines+markers",
    )
    st.plotly_chart(
        apply_chart_style(fig1, "Receita Diária"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    col_a, col_b = st.columns(2)

    df_dow = df_f.groupby("dia_semana_nome", as_index=False)["receita_total"].sum()
    df_dow["dia_semana_nome"] = pd.Categorical(
        df_dow["dia_semana_nome"], categories=DAY_ORDER, ordered=True
    )
    df_dow = df_dow.sort_values("dia_semana_nome")
    df_dow["receita_label"] = df_dow["receita_total"].map(fmt_brl_compact)
    fig2 = px.bar(
        df_dow,
        x="dia_semana_nome",
        y="receita_total",
        text="receita_label",
        color_discrete_sequence=["#E69F00"],
        labels={"dia_semana_nome": "Dia da semana", "receita_total": "Receita total"},
    )
    fig2.update_traces(
        hovertemplate="Dia: %{x}<br>Receita: %{text}<extra></extra>",
        textfont=dict(color="#0F172A", size=11),
        textposition="outside",
    )
    col_a.plotly_chart(
        apply_chart_style(fig2, "Receita por Dia da Semana"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    df_hora = df_f.groupby("hora_venda", as_index=False)["total_vendas"].sum()
    df_hora["vendas_label"] = df_hora["total_vendas"].map(fmt_int)
    fig3 = px.bar(
        df_hora,
        x="hora_venda",
        y="total_vendas",
        text="vendas_label",
        color_discrete_sequence=["#56B4E9"],
        labels={"hora_venda": "Hora da venda", "total_vendas": "Total de vendas"},
    )
    fig3.update_traces(
        hovertemplate="Hora: %{x}h<br>Vendas: %{text}<extra></extra>",
        textfont=dict(color="#0F172A", size=11),
        textposition="outside",
    )
    col_b.plotly_chart(
        apply_chart_style(fig3, "Volume de Vendas por Hora"),
        use_container_width=True,
        config={"displayModeBar": False},
    )
```

- [ ] **Step 4: Rodar teste de vendas**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_vendas_view.py -v
```

Esperado: `1 passed`.

- [ ] **Step 5: Rodar bateria completa**

```bash
uv run pytest
```

Esperado: tudo verde.

- [ ] **Step 6: Commit**

```bash
git add .llm/case-01-dashboard/views/vendas.py .llm/case-01-dashboard/tests/test_vendas_view.py
git commit -m "refactor(dashboard): vendas consome FilterSelection da sidebar global" -m "- render(selection) substitui o bloco interno de filtros da view.
- Aplica filtros via apply_temporal de filters.py, sem duplicar lógica.
- Atualiza test_vendas_view para a nova assinatura."
```

---

## Task 14: Refatorar `views/clientes.py` para receber `FilterSelection`

Por que: análogo ao Task 13. `_apply_customer_filters` e `_segment_filter_options` saem; `apply_customer` entra; `top_n` vem do `selection.top_n`.

**Files:**
- Modify: `.llm/case-01-dashboard/views/clientes.py`
- Modify: `.llm/case-01-dashboard/tests/test_utils.py` (remover testes que viram redundantes)

- [ ] **Step 1: Ajustar testes em `test_utils.py`**

Em `tests/test_utils.py`, dentro de `class TestClientesHelpers`:

- **Remover** o teste `test_segment_filter_options_keep_raw_values_with_readable_labels` (a função `_segment_filter_options` será removida; o sourcing das opções de segmento agora é responsabilidade de `filters.load_filter_options`, já testada em `test_filters.py::TestLoadFilterOptions`).
- **Remover** o teste `test_apply_customer_filters_uses_segment_and_state` (substituído por `TestApplyCustomer` em `test_filters.py`).
- **Manter** o teste `test_top_customers_limits_by_top_n_and_preserves_ranking_order` (a função `_top_customers` permanece em `clientes.py`).

A classe deve ficar reduzida a:

```python
class TestClientesHelpers:
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
```

- [ ] **Step 2: Rodar testes e verificar que (alguns) falham**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_utils.py::TestClientesHelpers -v
```

Esperado: `1 passed` no que sobrou. Pode aparecer falha em outro lugar se a refatoração ainda não aconteceu — vamos resolver no próximo step.

- [ ] **Step 3: Refatorar `views/clientes.py`**

Substituir `.llm/case-01-dashboard/views/clientes.py` por:

```python
import pandas as pd
import plotly.express as px
import streamlit as st
from db import get_data
from filters import FilterSelection, apply_customer
from utils import (
    SEGMENT_COLORS,
    MissingColumnsError,
    apply_chart_style,
    fmt_brl,
    fmt_brl_compact,
    fmt_int,
    fmt_pct,
    kpi_card,
    segment_label,
    validate_customers_columns,
)

THEME_COLOR = "#009E73"
QUERY = "SELECT * FROM public_gold_cs.gold_customer_success_clientes_segmentacao"


def _top_customers(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    return df.nsmallest(top_n, "ranking_receita").sort_values("ranking_receita")


def _format_customer_table(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["receita_total"] = result["receita_total"].map(fmt_brl)
    result["ticket_medio"] = result["ticket_medio"].map(fmt_brl)
    result["segmento_cliente"] = result["segmento_cliente"].map(segment_label)
    return result.rename(
        columns={
            "cliente_id": "ID do cliente",
            "nome_cliente": "Nome do cliente",
            "estado": "Estado",
            "receita_total": "Receita total",
            "total_compras": "Total de compras",
            "ticket_medio": "Ticket médio",
            "primeira_compra": "Primeira compra",
            "ultima_compra": "Última compra",
            "segmento_cliente": "Segmento",
            "ranking_receita": "Ranking por receita",
        }
    )


def render(selection: FilterSelection) -> None:
    try:
        df = get_data(QUERY)
        validate_customers_columns(df)
    except MissingColumnsError as e:
        st.error(str(e))
        return
    except Exception:
        st.error("Não foi possível conectar ao banco de dados.")
        return

    try:
        _render_customers_page(df, selection)
    except Exception:
        st.error("Não foi possível renderizar a página de clientes.")
        return


def _render_customers_page(df: pd.DataFrame, selection: FilterSelection) -> None:
    df_f = apply_customer(df, selection)
    if df_f.empty:
        st.warning("Nenhum cliente encontrado para os filtros selecionados.")
        return

    top_n = selection.top_n

    st.markdown(
        f"<h1 style='color:#0F172A;font-size:28px;font-weight:700;"
        f"border-bottom:3px solid {THEME_COLOR};padding-bottom:8px;margin-bottom:24px'>"
        "Clientes</h1>",
        unsafe_allow_html=True,
    )

    receita_total = float(df_f["receita_total"].sum())
    total_clientes = len(df_f)
    vip_count = int((df_f["segmento_cliente"] == "VIP").sum())
    ticket_medio = float(df_f["ticket_medio"].mean())
    total_compras = int(df_f["total_compras"].sum())

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in [
        (c1, "Receita Total", fmt_brl(receita_total)),
        (c2, "Total de Clientes", fmt_int(total_clientes)),
        (c3, "Clientes VIP", fmt_int(vip_count)),
        (c4, "Ticket Médio", fmt_brl(ticket_medio)),
    ]:
        col.markdown(kpi_card(label, value, THEME_COLOR), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 2])

    df_seg = df_f.groupby("segmento_cliente", as_index=False).agg(
        total_clientes=("cliente_id", "count")
    )
    df_seg["percentual"] = df_seg["total_clientes"] / df_seg["total_clientes"].sum() * 100
    df_seg["segmento_label"] = df_seg["segmento_cliente"].map(segment_label)
    df_seg["clientes_label"] = df_seg["total_clientes"].map(fmt_int)
    df_seg["texto"] = df_seg.apply(
        lambda row: f"{fmt_int(row['total_clientes'])} ({fmt_pct(row['percentual'])})",
        axis=1,
    )
    fig1 = px.bar(
        df_seg.sort_values("total_clientes"),
        x="total_clientes",
        y="segmento_label",
        orientation="h",
        color="segmento_cliente",
        color_discrete_map=SEGMENT_COLORS,
        text="texto",
        custom_data=["clientes_label", "texto"],
        labels={"segmento_label": "Segmento", "total_clientes": "Total de clientes"},
    )
    fig1.update_traces(
        hovertemplate=(
            "Segmento: %{y}<br>Clientes: %{customdata[0]}<br>"
            "Participação: %{customdata[1]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=11),
        textposition="outside",
    )
    fig1.update_layout(showlegend=False)
    col_a.plotly_chart(
        apply_chart_style(fig1, "Clientes por Segmento"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    df_rev_seg = df_f.groupby("segmento_cliente", as_index=False)["receita_total"].sum()
    df_rev_seg["segmento_label"] = df_rev_seg["segmento_cliente"].map(segment_label)
    df_rev_seg["receita_label"] = df_rev_seg["receita_total"].map(fmt_brl_compact)
    fig2 = px.bar(
        df_rev_seg.sort_values("receita_total", ascending=False),
        x="segmento_label",
        y="receita_total",
        color="segmento_cliente",
        color_discrete_map=SEGMENT_COLORS,
        text="receita_label",
        custom_data=["receita_label"],
        labels={"segmento_label": "Segmento", "receita_total": "Receita total"},
    )
    fig2.update_traces(
        hovertemplate="Segmento: %{x}<br>Receita: %{customdata[0]}<extra></extra>",
        textfont=dict(color="#0F172A", size=11),
        textposition="outside",
    )
    fig2.update_layout(showlegend=False)
    col_b.plotly_chart(
        apply_chart_style(fig2, "Receita por Segmento"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    col_c, col_d = st.columns(2)

    df_top = _top_customers(df_f, top_n)
    df_top_chart = df_top.sort_values("ranking_receita", ascending=False).copy()
    df_top_chart["receita_label"] = df_top_chart["receita_total"].map(fmt_brl_compact)
    fig3 = px.bar(
        df_top_chart,
        x="receita_total",
        y="nome_cliente",
        orientation="h",
        text="receita_label" if len(df_top_chart) <= 20 else None,
        custom_data=["receita_label", "ranking_receita"],
        color_discrete_sequence=[THEME_COLOR],
        labels={"nome_cliente": "Cliente", "receita_total": "Receita total"},
    )
    fig3.update_traces(
        hovertemplate=(
            "Cliente: %{y}<br>Receita: %{customdata[0]}<br>"
            "Ranking: %{customdata[1]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=10),
        textposition="outside",
    )
    col_c.plotly_chart(
        apply_chart_style(fig3, f"Top {top_n} Clientes por Receita"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    df_estado = df_f.groupby("estado", as_index=False).agg(
        total_clientes=("cliente_id", "count"),
        receita_total=("receita_total", "sum"),
    )
    df_estado = df_estado.sort_values("receita_total", ascending=True)
    df_estado["receita_label"] = df_estado["receita_total"].map(fmt_brl_compact)
    df_estado["clientes_label"] = df_estado["total_clientes"].map(fmt_int)
    fig4 = px.bar(
        df_estado,
        x="receita_total",
        y="estado",
        orientation="h",
        text="receita_label" if len(df_estado) <= 15 else None,
        custom_data=["receita_label", "clientes_label"],
        color_discrete_sequence=["#E69F00"],
        labels={"estado": "Estado", "receita_total": "Receita total"},
    )
    fig4.update_traces(
        hovertemplate=(
            "Estado: %{y}<br>Receita: %{customdata[0]}<br>"
            "Clientes: %{customdata[1]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=10),
        textposition="outside",
    )
    col_d.plotly_chart(
        apply_chart_style(fig4, "Receita por Estado"),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.markdown(f"### Top {top_n} Clientes")
    st.caption(
        f"Dados filtrados: {fmt_int(total_clientes)} clientes, {fmt_int(total_compras)} compras."
    )
    st.dataframe(_format_customer_table(df_top), use_container_width=True, hide_index=True)
```

Mudanças vs. arquivo atual:
- Removidas as funções privadas `_segment_label`, `_segment_filter_options`, `_apply_customer_filters`. Uso de `utils.segment_label` em vez do helper local. Filtragem feita via `apply_customer` de `filters.py`.
- `render()` agora aceita `selection: FilterSelection`.
- Bloco `with st.sidebar:` removido (sidebar é responsabilidade de `filters.render_sidebar`).
- `top_n` lido de `selection.top_n` em vez de `st.selectbox`.

- [ ] **Step 4: Rodar bateria completa**

```bash
uv run pytest
```

Esperado: tudo verde.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/views/clientes.py .llm/case-01-dashboard/tests/test_utils.py
git commit -m "refactor(dashboard): clientes consome FilterSelection da sidebar global" -m "- render(selection) substitui sidebar local e helpers privados de filtragem.
- Top N e segmento agora vêm do FilterSelection em vez de selectbox local.
- Atualiza test_utils removendo cobertura redundante movida para test_filters."
```

---

## Task 15: Refatorar `views/pricing.py` para receber `FilterSelection`

Por que: análogo a Tasks 13-14. Pricing era multiselect — passa a ser single-select com FILTER_ALL.

**Files:**
- Modify: `.llm/case-01-dashboard/views/pricing.py`
- Modify: `.llm/case-01-dashboard/tests/test_utils.py` (atualizar testes)

- [ ] **Step 1: Ajustar testes em `test_utils.py`**

Em `tests/test_utils.py`, dentro de `class TestPricingHelpers`:

- **Remover** os testes `test_apply_pricing_filters_uses_category_brand_and_raw_classification` e `test_apply_pricing_filters_returns_empty_for_empty_selection` (substituídos por `TestApplyPricing` em `test_filters.py`).
- **Manter** os testes `test_pricing_metrics_calculates_revenue_risk_and_exposure_category` e `test_executive_narrative_mentions_risk_context_and_decision_caution` (as funções `_pricing_metrics` e `_build_executive_narrative` permanecem).

A classe deve ficar com 2 testes restantes. Verifique também os imports no topo do arquivo: a chamada `from views import clientes, pricing` continua válida.

- [ ] **Step 2: Rodar testes e verificar que ainda funcionam**

```bash
uv run pytest .llm/case-01-dashboard/tests/test_utils.py::TestPricingHelpers -v
```

Esperado: `2 passed`.

- [ ] **Step 3: Refatorar `views/pricing.py`**

Substituir `.llm/case-01-dashboard/views/pricing.py` por:

```python
import pandas as pd
import plotly.express as px
import streamlit as st
from db import get_data
from filters import FilterSelection, apply_pricing
from utils import (
    CLASS_COLORS,
    MissingColumnsError,
    apply_chart_style,
    classification_label,
    fmt_brl,
    fmt_brl_compact,
    fmt_int,
    fmt_pct,
    kpi_card,
    validate_pricing_columns,
)

THEME_COLOR = "#E69F00"
QUERY = "SELECT * FROM public_gold_pricing.gold_pricing_precos_competitividade"
RISK_CLASS = "MAIS_CARO_QUE_TODOS"


def _pricing_metrics(df: pd.DataFrame) -> dict[str, float | int | str]:
    risk_df = df[df["classificacao_preco"] == RISK_CLASS]
    receita_total = float(df["receita_total"].sum())
    receita_risco = float(risk_df["receita_total"].sum())
    pct_receita_risco = receita_risco / receita_total * 100 if receita_total else 0.0

    if risk_df.empty:
        categoria_maior_exposicao = "Sem exposição"
    else:
        categoria_maior_exposicao = (
            risk_df.groupby("categoria")["receita_total"].sum().idxmax()
        )

    return {
        "total_produtos": len(df),
        "mais_caros": int((df["classificacao_preco"] == RISK_CLASS).sum()),
        "mais_baratos": int((df["classificacao_preco"] == "MAIS_BARATO_QUE_TODOS").sum()),
        "acima_media": int((df["classificacao_preco"] == "ACIMA_DA_MEDIA").sum()),
        "dif_media": float(df["diferenca_percentual_vs_media"].mean()),
        "receita_total": receita_total,
        "receita_risco": receita_risco,
        "pct_receita_risco": pct_receita_risco,
        "categoria_maior_exposicao": categoria_maior_exposicao,
    }


def _build_executive_narrative(metrics: dict[str, float | int | str]) -> str:
    return (
        "<div class='insight-box'>"
        "<strong>Leitura executiva:</strong> "
        f"a seleção contém {fmt_int(metrics['total_produtos'])} produtos monitorados, "
        f"com diferença média vs mercado de {fmt_pct(metrics['dif_media'])}. "
        f"Há {fmt_int(metrics['mais_caros'])} produtos mais caros que todos os concorrentes, "
        f"concentrando {fmt_brl(metrics['receita_risco'])} em receita em risco, "
        f"equivalente a {fmt_pct(metrics['pct_receita_risco'])} da receita filtrada. "
        f"A maior exposição aparece em {metrics['categoria_maior_exposicao']}. "
        "Qualquer decisão de preço deve considerar margem, estoque e posicionamento antes "
        "de aplicar reajustes."
        "</div>"
    )


def _format_alert_table(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in [
        "nosso_preco",
        "preco_medio_concorrentes",
        "preco_maximo_concorrentes",
        "receita_total",
    ]:
        result[column] = result[column].map(fmt_brl)
    result["diferenca_percentual_vs_media"] = result["diferenca_percentual_vs_media"].map(
        fmt_pct
    )
    return result.rename(
        columns={
            "produto_id": "ID do produto",
            "nome_produto": "Produto",
            "categoria": "Categoria",
            "marca": "Marca",
            "nosso_preco": "Nosso preço",
            "preco_medio_concorrentes": "Preço médio concorrentes",
            "preco_maximo_concorrentes": "Maior preço concorrente",
            "diferenca_percentual_vs_media": "Diferença vs média",
            "receita_total": "Receita total",
        }
    )


def render(selection: FilterSelection) -> None:
    try:
        df = get_data(QUERY)
        validate_pricing_columns(df)
    except MissingColumnsError as e:
        st.error(str(e))
        return
    except Exception:
        st.error("Não foi possível conectar ao banco de dados.")
        return

    try:
        _render_pricing_page(df, selection)
    except Exception:
        st.error("Não foi possível renderizar a página de pricing.")
        return


def _render_pricing_page(df: pd.DataFrame, selection: FilterSelection) -> None:
    df_f = apply_pricing(df, selection)

    st.markdown(
        f"<h1 style='color:#0F172A;font-size:28px;font-weight:700;"
        f"border-bottom:3px solid {THEME_COLOR};padding-bottom:8px;margin-bottom:24px'>"
        "Pricing</h1>",
        unsafe_allow_html=True,
    )

    if df_f.empty:
        st.warning("Nenhum produto encontrado para os filtros selecionados.")
        return

    metrics = _pricing_metrics(df_f)

    kpi_rows = [
        [
            ("Produtos Monitorados", fmt_int(metrics["total_produtos"])),
            ("Mais Caros que Todos", fmt_int(metrics["mais_caros"])),
            ("Mais Baratos que Todos", fmt_int(metrics["mais_baratos"])),
            ("Acima da Média", fmt_int(metrics["acima_media"])),
        ],
        [
            ("Dif. Média vs Mercado", fmt_pct(metrics["dif_media"])),
            ("Receita Total", fmt_brl(metrics["receita_total"])),
            ("Receita em Risco", fmt_brl(metrics["receita_risco"])),
            ("% Receita em Risco", fmt_pct(metrics["pct_receita_risco"])),
        ],
    ]
    for row in kpi_rows:
        columns = st.columns(4)
        for col, (label, value) in zip(columns, row, strict=True):
            col.markdown(kpi_card(label, value, THEME_COLOR), unsafe_allow_html=True)

    st.markdown(_build_executive_narrative(metrics), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 2])
    _render_classification_chart(col_a, df_f)
    _render_category_chart(col_b, df_f)
    _render_volume_chart(df_f)
    _render_alert_table(df_f)


def _render_classification_chart(container, df: pd.DataFrame) -> None:
    df_class = df.groupby("classificacao_preco", as_index=False).agg(
        total_produtos=("produto_id", "count"),
        receita_total=("receita_total", "sum"),
    )
    df_class["percentual"] = df_class["total_produtos"] / df_class["total_produtos"].sum() * 100
    df_class["classificacao_label"] = df_class["classificacao_preco"].map(classification_label)
    df_class["produtos_label"] = df_class["total_produtos"].map(fmt_int)
    df_class["percentual_label"] = df_class["percentual"].map(fmt_pct)
    df_class["receita_label"] = df_class["receita_total"].map(fmt_brl_compact)
    df_class["texto"] = df_class.apply(
        lambda row: f"{row['produtos_label']} ({row['percentual_label']})",
        axis=1,
    )
    fig = px.bar(
        df_class.sort_values("total_produtos"),
        x="total_produtos",
        y="classificacao_label",
        orientation="h",
        color="classificacao_preco",
        color_discrete_map=CLASS_COLORS,
        text="texto",
        custom_data=["produtos_label", "percentual_label", "receita_label"],
        labels={"classificacao_label": "Classificação", "total_produtos": "Produtos"},
    )
    fig.update_traces(
        hovertemplate=(
            "Classificação: %{y}<br>"
            "Produtos: %{customdata[0]}<br>"
            "Participação: %{customdata[1]}<br>"
            "Receita: %{customdata[2]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=10),
        textposition="outside",
    )
    fig.update_layout(showlegend=False)
    container.plotly_chart(
        apply_chart_style(fig, "Posicionamento vs Concorrência"),
        use_container_width=True,
        config={"displayModeBar": False},
    )


def _render_category_chart(container, df: pd.DataFrame) -> None:
    df_cat = (
        df.dropna(subset=["diferenca_percentual_vs_media"])
        .groupby("categoria", as_index=False)
        .agg(
            diferenca_percentual_vs_media=("diferenca_percentual_vs_media", "mean"),
            total_produtos=("produto_id", "count"),
            receita_total=("receita_total", "sum"),
        )
        .sort_values("diferenca_percentual_vs_media", ascending=True)
    )
    if df_cat.empty:
        container.info("Não há dados de concorrência para calcular competitividade por categoria.")
        return

    df_cat["cor"] = df_cat["diferenca_percentual_vs_media"].apply(
        lambda value: "#D55E00" if value > 0 else "#009E73"
    )
    df_cat["percentual_label"] = df_cat["diferenca_percentual_vs_media"].map(fmt_pct)
    df_cat["produtos_label"] = df_cat["total_produtos"].map(fmt_int)
    df_cat["receita_label"] = df_cat["receita_total"].map(fmt_brl_compact)
    fig = px.bar(
        df_cat,
        x="diferenca_percentual_vs_media",
        y="categoria",
        orientation="h",
        color="cor",
        color_discrete_map="identity",
        text="percentual_label" if len(df_cat) <= 12 else None,
        custom_data=["percentual_label", "produtos_label", "receita_label"],
        labels={
            "categoria": "Categoria",
            "diferenca_percentual_vs_media": "Diferença média vs mercado",
        },
    )
    fig.update_traces(
        hovertemplate=(
            "Categoria: %{y}<br>"
            "Diferença: %{customdata[0]}<br>"
            "Produtos: %{customdata[1]}<br>"
            "Receita: %{customdata[2]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=11),
        textposition="outside",
    )
    fig.update_layout(showlegend=False)
    fig.add_vline(line_dash="dash", line_color="#475569", x=0)
    container.plotly_chart(
        apply_chart_style(fig, "Competitividade por Categoria"),
        use_container_width=True,
        config={"displayModeBar": False},
    )


def _render_volume_chart(df: pd.DataFrame) -> None:
    df_volume = (
        df.dropna(subset=["diferenca_percentual_vs_media"])
        .groupby("classificacao_preco", as_index=False)
        .agg(
            diferenca_percentual_vs_media=("diferenca_percentual_vs_media", "mean"),
            quantidade_total=("quantidade_total", "sum"),
            receita_total=("receita_total", "sum"),
            total_produtos=("produto_id", "count"),
        )
    )
    if df_volume.empty:
        st.info("Não há dados suficientes para cruzar competitividade e volume de vendas.")
        return

    df_volume["classificacao_label"] = df_volume["classificacao_preco"].map(
        classification_label
    )
    df_volume["diferenca_label"] = df_volume["diferenca_percentual_vs_media"].map(fmt_pct)
    df_volume["quantidade_label"] = df_volume["quantidade_total"].map(fmt_int)
    df_volume["receita_label"] = df_volume["receita_total"].map(fmt_brl_compact)
    df_volume["produtos_label"] = df_volume["total_produtos"].map(fmt_int)
    fig = px.scatter(
        df_volume,
        x="diferenca_percentual_vs_media",
        y="quantidade_total",
        color="classificacao_preco",
        size="receita_total",
        size_max=46,
        text="classificacao_label",
        color_discrete_map=CLASS_COLORS,
        custom_data=[
            "classificacao_label",
            "diferenca_label",
            "receita_label",
            "produtos_label",
            "quantidade_label",
        ],
        labels={
            "diferenca_percentual_vs_media": "Diferença média vs mercado",
            "quantidade_total": "Quantidade vendida",
        },
    )
    fig.update_traces(
        hovertemplate=(
            "Classificação: %{customdata[0]}<br>"
            "Diferença: %{customdata[1]}<br>"
            "Quantidade: %{customdata[4]}<br>"
            "Receita: %{customdata[2]}<br>"
            "Produtos: %{customdata[3]}<extra></extra>"
        ),
        textfont=dict(color="#0F172A", size=10),
        textposition="top center",
    )
    fig.update_layout(showlegend=False)
    fig.add_vline(line_dash="dash", line_color="#475569", x=0)
    st.plotly_chart(
        apply_chart_style(fig, "Competitividade x Volume por Classificação"),
        use_container_width=True,
        config={"displayModeBar": False},
    )


def _render_alert_table(df: pd.DataFrame) -> None:
    st.markdown("### Produtos com maior risco de pricing")
    df_alert = (
        df[df["classificacao_preco"] == RISK_CLASS]
        .sort_values("receita_total", ascending=False)
        .head(15)
    )
    if df_alert.empty:
        st.info("Nenhum produto nesta seleção está mais caro que todos os concorrentes.")
        return

    columns = [
        "produto_id",
        "nome_produto",
        "categoria",
        "marca",
        "nosso_preco",
        "preco_medio_concorrentes",
        "preco_maximo_concorrentes",
        "diferenca_percentual_vs_media",
        "receita_total",
    ]
    st.dataframe(_format_alert_table(df_alert[columns]), use_container_width=True, hide_index=True)
```

Mudanças vs. arquivo atual:
- Removidas as funções privadas `_multiselect_options`, `_classification_filter_options`, `_apply_pricing_filters`. Filtragem feita via `apply_pricing` de `filters.py`.
- `render()` agora aceita `selection: FilterSelection`.
- Bloco `with st.sidebar:` removido.

- [ ] **Step 4: Rodar bateria completa**

```bash
uv run pytest
```

Esperado: tudo verde.

- [ ] **Step 5: Commit**

```bash
git add .llm/case-01-dashboard/views/pricing.py .llm/case-01-dashboard/tests/test_utils.py
git commit -m "refactor(dashboard): pricing consome FilterSelection da sidebar global" -m "- render(selection) substitui sidebar local com multiselect.
- Categoria, marca e classificação passam a usar selectbox único com 'Todos'.
- Atualiza test_utils removendo cobertura redundante movida para test_filters."
```

---

## Task 16: Atualizar `app.py` — orquestração + correção do header preto

Por que: a peça final que liga tudo. Remove a função antiga `render_sidebar_shell` (substituída por `filters.render_sidebar`) e adiciona o CSS do header.

**Files:**
- Modify: `.llm/case-01-dashboard/app.py`

- [ ] **Step 1: Substituir o conteúdo de `app.py`**

Substituir `.llm/case-01-dashboard/app.py` por:

```python
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from filters import render_sidebar

load_dotenv(Path(__file__).parent.parent.parent / ".env")

st.set_page_config(
    page_title="E-commerce Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }
        .stApp {
            background-color: #F8FAFC;
        }
        [data-testid="stHeader"] {
            background: transparent;
            height: 0;
        }
        [data-testid="stToolbar"] {
            right: 1rem;
            top: 0.5rem;
        }
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
            color: #0F172A;
        }
        [data-testid="stSidebar"] label {
            color: #334155 !important;
            font-size: 13px !important;
            font-weight: 700 !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"][aria-disabled="true"] {
            opacity: 0.55;
        }
        [data-testid="stSidebar"] label:has(+ div [aria-disabled="true"]) {
            color: #94A3B8 !important;
        }
        .sidebar-brand {
            padding: 0.25rem 0 0.75rem;
        }
        .sidebar-eyebrow {
            color: #0072B2;
            font-size: 13px !important;
            font-weight: 600 !important;
            margin-bottom: 0.35rem;
        }
        .sidebar-title {
            color: #0F172A;
            font-size: 22px;
            font-weight: 700;
            line-height: 1.2;
            margin: 0 0 0.4rem;
        }
        .sidebar-description {
            color: #475569;
            font-size: 14px;
            line-height: 1.45;
            margin: 0;
        }
        .sidebar-section-title {
            color: #64748B;
            font-size: 12px;
            font-weight: 700;
            margin: 0.35rem 0 0.75rem;
            text-transform: uppercase;
        }
        .block-container {
            padding-top: 2rem !important;
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
        }
        h1, h2, h3, h4, h5, h6, p, label {
            color: #0F172A;
        }
        [data-testid="stMarkdownContainer"] h3 {
            color: #0F172A;
            font-weight: 700;
        }
        [data-testid="stDataFrame"] {
            color: #0F172A;
        }
        [data-testid="stRadio"] div[role="radiogroup"] {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
        }
        [data-testid="stRadio"] div[role="radiogroup"] label {
            background-color: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            color: #334155;
            font-weight: 700;
            min-height: 44px;
            padding: 0.45rem 1rem;
        }
        [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
            background-color: #EFF6FF;
            border-color: #0072B2;
            color: #0F172A;
        }
        [data-testid="stRadio"] div[role="radiogroup"] label p {
            font-weight: 700;
        }
        .insight-box {
            background-color: #FFFBEB;
            border: 1px solid #FCD34D;
            border-left: 4px solid #E69F00;
            border-radius: 8px;
            color: #0F172A;
            line-height: 1.55;
            padding: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    inject_css()

    page = st.radio(
        "Página",
        options=["Vendas", "Clientes", "Pricing"],
        horizontal=True,
        label_visibility="collapsed",
        key="main_page",
    )
    st.divider()

    selection = render_sidebar(page)

    if page == "Vendas":
        from views.vendas import render

        render(selection)
    elif page == "Clientes":
        from views.clientes import render

        render(selection)
    else:
        from views.pricing import render

        render(selection)


main()
```

Mudanças vs. arquivo atual:
- Adicionados blocos CSS `[data-testid="stHeader"]`, `[data-testid="stToolbar"]`, e regras de filtro desabilitado.
- Função `render_sidebar_shell` removida (responsabilidade migrou para `filters.render_sidebar`).
- `main()` chama `filters.render_sidebar(page)` e propaga `selection` para a view selecionada.

- [ ] **Step 2: Rodar bateria completa**

```bash
uv run pytest
```

Esperado: tudo verde.

- [ ] **Step 3: Rodar lint**

```bash
uv run ruff check .llm/case-01-dashboard
uv run ruff format --check .llm/case-01-dashboard
```

Esperado: sem erros. Se houver, `uv run ruff check --fix .llm/case-01-dashboard` e `uv run ruff format .llm/case-01-dashboard` para corrigir.

- [ ] **Step 4: Commit**

```bash
git add .llm/case-01-dashboard/app.py
git commit -m "feat(dashboard): conecta sidebar global e corrige header preto" -m "- main() invoca filters.render_sidebar e propaga FilterSelection.
- Remove render_sidebar_shell duplicada agora que filters cuida da UI.
- Torna o header transparente e atenua filtros desabilitados via CSS."
```

---

## Task 17: Verificação manual no navegador

Por que: contratos verificáveis do spec exigem inspeção visual (a Section 6.3 do spec descreve interações UI). Subagent não consegue rodar Streamlit, então este passo é manual mas tem checklist preciso.

**Files:**
- Nenhum (verificação)

- [ ] **Step 1: Rodar o dashboard localmente**

```bash
python -m streamlit run .llm/case-01-dashboard/app.py
```

(Ou `.venv/Scripts/python -m streamlit run ...` em Windows.)

- [ ] **Step 2: Verificar critérios de sucesso do spec**

Para cada item, observar no navegador (`http://localhost:8501`):

- [ ] Topo da página: sem retângulo preto. Fundo `#F8FAFC` contínuo.
- [ ] Sidebar mostra **9 selectboxes** agrupados em 3 títulos: **TEMPORAL**, **CLIENTE**, **PRODUTO**.
- [ ] **Página Vendas:**
  - Bloco TEMPORAL ativo (Ano, Mês, Dia da Semana habilitados).
  - Bloco CLIENTE cinza com tooltip *"Disponível em Clientes."* nos 3 filtros.
  - Bloco PRODUTO cinza com tooltip *"Disponível em Pricing."* nos 3 filtros.
  - Filtro Mês mostra opções `Janeiro, Fevereiro, …` em ordem do calendário.
  - Aplicar Ano + Mês + Dia da Semana → KPIs e gráficos atualizam corretamente.
- [ ] **Página Clientes:**
  - Bloco TEMPORAL cinza com tooltip *"Disponível em Vendas."*.
  - Bloco CLIENTE ativo (Segmento, Estado, Top N).
  - Bloco PRODUTO cinza com tooltip *"Disponível em Pricing."*.
  - Aplicar Segmento + Estado + Top N → tabela e gráficos atualizam.
- [ ] **Página Pricing:**
  - Bloco TEMPORAL cinza com tooltip *"Disponível em Vendas."*.
  - Bloco CLIENTE cinza com tooltip *"Disponível em Clientes."*.
  - Bloco PRODUTO ativo (Categoria, Marca, Classificação).
  - Aplicar Categoria + Marca + Classificação → KPIs e narrativa atualizam.
- [ ] **Persistência:** selecionar Ano=2025 em Vendas, navegar Clientes → Pricing → Vendas; o `2025` ainda está selecionado.
- [ ] **Botão "Recarregar opções"** ao final da sidebar funciona (ao clicar, app reroda com cache limpo).

- [ ] **Step 3: Se algum critério falhar, voltar à task correspondente para ajustar**

Pontos comuns:
- Tooltip não aparece: confirmar que `help=` está sendo passado em `render_sidebar`.
- Cinza inconsistente: ajustar regras CSS no `app.py`.
- Sidebar não persiste: verificar `key=` consistente em todos os `selectbox`.

- [ ] **Step 4: Não há commit aqui** — esta task é só verificação.

---

## Task 18: Verificação final (testes + ruff) e commit de fechamento

Por que: garantir que a bateria completa passa antes de declarar pronto.

**Files:**
- Nenhum (verificação final)

- [ ] **Step 1: Rodar pytest**

```bash
uv run pytest .llm/case-01-dashboard
```

Esperado: 100% verde, com `test_filters.py` passando integralmente.

- [ ] **Step 2: Rodar ruff**

```bash
uv run ruff check .llm/case-01-dashboard
uv run ruff format --check .llm/case-01-dashboard
```

Esperado: sem erros nem diff.

- [ ] **Step 3: Rodar dbt parse para garantir que não tocamos sem querer no transform**

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```

Esperado: `parse` ok (não deve haver mudança em dbt).

- [ ] **Step 4: Verificar `git status` limpo**

```bash
git status
```

Esperado: nada pendente. Todos os commits parciais já foram feitos nas tasks anteriores.

- [ ] **Step 5: Não há commit aqui — verificação final**

Se tudo passou, o trabalho está completo. Push fica a critério do usuário.

---

## Riscos conhecidos e mitigações

| Risco | Mitigação |
|---|---|
| `st.cache_data` interfere com mock em testes | `_load_filter_options_uncached` é a versão sem cache, testada diretamente. `load_filter_options` (com `@st.cache_data`) é fina e não testada via unit. |
| Mudança em assinaturas de `render` quebra dispatch em `app.py` | `app.py` é atualizado na Task 16, depois das views. Cada Task 13-15 passa pytest antes de commitar. |
| `st.session_state` pode não existir em testes | Stub de Streamlit nos testes simula `session_state` como dict. `selection_from_state` aceita qualquer mapping. |
| Botão "Recarregar opções" pode causar `st.rerun` em ambiente de testes | Stub retorna `False` para `st.button`, evitando o caminho do rerun. |
| Migração de tests pode esconder cobertura | Testes movidos de `test_utils.py` para `test_filters.py` cobrem comportamento equivalente; assertivas estão preservadas em essência. |

## Checklist final (auto-revisão)

- [x] Cada task tem código completo nos steps (sem "TBD" ou "implementar depois").
- [x] Cada task começa com teste falhando (TDD).
- [x] Cada task termina com commit individual em PT-BR seguindo `COMMIT_GUIDELINES.md`.
- [x] Nenhuma task referencia tipo/função/método que não foi definido em outra task.
- [x] Spec coverage: registry (Task 3), FilterSelection (Task 4), helpers apply_* (Tasks 5-7), queries+segurança (Task 8), load_options (Task 9), render_sidebar (Task 12), CSS header (Task 16), Mês PT-BR (Tasks 2 e 5), persistência via session_state (todas as tasks de UI), critérios de sucesso (Task 17).
