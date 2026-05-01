# Spec — Painel de filtros unificado do Dashboard

**Data:** 2026-05-01
**Escopo:** `.llm/case-01-dashboard/` (Streamlit)
**Status:** Aprovado pelo usuário em brainstorming; pendente de revisão final do spec.

---

## 1. Objetivo

Substituir os três painéis de filtros independentes (um por página) por um **painel global único na sidebar**, sempre presente em qualquer página do dashboard, com 9 filtros agrupados em 3 seções. Filtros que não se aplicam à página atual ficam visíveis mas desabilitados, comunicando o porquê. Corrige também o retângulo preto do header do Streamlit.

## 2. Não-objetivos

- **Não criar filtros cruzados temporais em Clientes/Pricing.** Os marts agregados desses domínios não têm grão temporal e o PRD do dashboard proíbe alterar regras de negócio ou schemas dbt para servir o dashboard. Filtros temporais ficam ativos apenas na página de Vendas.
- **Não trocar single-select por multiselect.** O Pricing perde a capacidade atual de combinar valores em Categoria/Marca/Classificação em troca de uniformidade.
- **Não alterar marts dbt nem `gold_*` SQL.** Toda a mudança é no app Streamlit.
- **Não introduzir filtros novos** além dos 9 listados.

## 3. Decisões fechadas (brainstorming)

| # | Decisão | Escolha |
|---|---|---|
| 1 | Filtros não-aplicáveis à página atual | Visíveis, desabilitados (`disabled=True`), com tooltip via `help=` |
| 2 | Organização visual | 3 seções: **Temporal** (Ano, Mês, Dia da Semana) → **Cliente** (Segmento, Estado, Top N) → **Produto** (Categoria, Marca, Classificação) |
| 3 | Filtros temporais cruzados | Não. Ativos apenas em Vendas. |
| 4 | Persistência entre páginas | Sim, via `st.session_state` com `key=` estável |
| 5 | Sourcing das opções | 3 queries `SELECT DISTINCT` cacheadas com TTL 5min |
| 6 | Tipo de controle | `st.selectbox` único com opção `"Todos"` para todos os 9 filtros |
| 7 | Estrutura de código | Módulo dedicado `filters.py` (registry, contratos, helpers) |
| 8 | Mês | Renderizado como `Janeiro, …, Dezembro` em ordem do calendário |
| 9 | Top N Clientes | Mantém opções `[5, 10, 15, 20, 50]`, default 10 |
| 10 | Header preto | Corrigido via CSS em `[data-testid="stHeader"]` |

## 4. Arquitetura

### 4.1 Layout de arquivos

```
.llm/case-01-dashboard/
├── app.py                  ← injeta CSS, dispatch de página, chama render_sidebar
├── filters.py              ← NOVO: registry, FilterSelection, load_filter_options, render_sidebar, apply_*
├── db.py                   ← inalterado
├── utils.py                ← inalterado (constantes Mês PT-BR podem migrar para cá ou ficar em filters.py)
├── views/
│   ├── vendas.py           ← recebe FilterSelection; chama apply_temporal
│   ├── clientes.py         ← recebe FilterSelection; chama apply_customer
│   └── pricing.py          ← recebe FilterSelection; chama apply_pricing
└── tests/
    ├── test_filters.py     ← NOVO
    └── ... (existentes)
```

### 4.2 Fluxo a cada interação

1. `app.py` injeta CSS (incluindo correção do `[data-testid="stHeader"]`).
2. `app.py` lê a página ativa via `st.radio` (Vendas / Clientes / Pricing).
3. `app.py` chama `filters.render_sidebar(active_page)` → retorna `FilterSelection`.
   - Internamente: `load_filter_options()` (cacheado 5min) → 3 queries `DISTINCT`.
   - Renderiza 3 seções agrupadas; cada filtro fora da página atual entra com `disabled=True`.
   - Lê valores via `st.session_state` (persistência entre páginas).
4. `app.py` faz dispatch para a view passando o `FilterSelection`.
5. Cada view aplica o helper correspondente (`apply_temporal` / `apply_customer` / `apply_pricing`), valida `df_f.empty`, renderiza KPIs e gráficos.

**Princípio:** `app.py` orquestra; `filters.py` é o componente de filtros; views só aplicam e renderizam. `db.py` continua a única porta para o banco — `filters.py` reutiliza `db.get_data`.

## 5. `filters.py` — contratos

### 5.1 Registry declarativo

```python
from dataclasses import dataclass
from typing import Literal

Page = Literal["Vendas", "Clientes", "Pricing"]
SectionId = Literal["temporal", "cliente", "produto"]

@dataclass(frozen=True)
class FilterDef:
    key: str                  # session_state key
    label: str                # rótulo na UI
    section: SectionId
    pages: tuple[Page, ...]   # páginas onde o filtro tem efeito

FILTER_REGISTRY: tuple[FilterDef, ...] = (
    FilterDef("ano",           "Ano",            "temporal", ("Vendas",)),
    FilterDef("mes",           "Mês",            "temporal", ("Vendas",)),
    FilterDef("dia_semana",    "Dia da Semana",  "temporal", ("Vendas",)),
    FilterDef("segmento",      "Segmento",       "cliente",  ("Clientes",)),
    FilterDef("estado",        "Estado",         "cliente",  ("Clientes",)),
    FilterDef("top_n",         "Top N Clientes", "cliente",  ("Clientes",)),
    FilterDef("categoria",     "Categoria",      "produto",  ("Pricing",)),
    FilterDef("marca",         "Marca",          "produto",  ("Pricing",)),
    FilterDef("classificacao", "Classificação",  "produto",  ("Pricing",)),
)

SECTION_TITLES = {
    "temporal": "Temporal",
    "cliente":  "Cliente",
    "produto":  "Produto",
}
```

Adicionar/remover filtro = uma linha no registry.

### 5.2 `FilterSelection`

```python
FILTER_ALL = "Todos"

@dataclass(frozen=True)
class FilterSelection:
    ano: str = FILTER_ALL
    mes: str = FILTER_ALL          # "Janeiro" ... "Dezembro" ou "Todos"
    dia_semana: str = FILTER_ALL
    segmento: str = FILTER_ALL
    estado: str = FILTER_ALL
    top_n: int = 10
    categoria: str = FILTER_ALL
    marca: str = FILTER_ALL
    classificacao: str = FILTER_ALL
```

### 5.3 `load_filter_options()`

```python
@st.cache_data(ttl=300, show_spinner=False)
def load_filter_options() -> dict:
    sales = get_data("""
        SELECT DISTINCT ano_venda, mes_venda, dia_semana_nome
        FROM public_gold_sales.gold_sales_vendas_temporais
        WHERE ano_venda IS NOT NULL
    """)
    customers = get_data("""
        SELECT DISTINCT segmento_cliente, estado
        FROM public_gold_cs.gold_customer_success_clientes_segmentacao
    """)
    pricing = get_data("""
        SELECT DISTINCT categoria, marca, classificacao_preco
        FROM public_gold_pricing.gold_pricing_precos_competitividade
    """)
    return {
        "anos":           sorted(sales["ano_venda"].dropna().astype(int).unique()),
        "meses":          sorted(sales["mes_venda"].dropna().astype(int).unique()),
        "dias_semana":    [d for d in DAY_ORDER if d in set(sales["dia_semana_nome"])],
        "segmentos":      sorted(customers["segmento_cliente"].dropna().unique(), key=segment_label),
        "estados":        sorted(customers["estado"].dropna().unique()),
        "top_n":          [5, 10, 15, 20, 50],
        "categorias":     sorted(pricing["categoria"].dropna().unique()),
        "marcas":         sorted(pricing["marca"].dropna().unique()),
        "classificacoes": sorted(pricing["classificacao_preco"].dropna().unique(),
                                  key=classification_label),
    }
```

Em caso de exceção (banco indisponível, schema inesperado), captura `Exception`, devolve dict com todas as listas vazias e dispara `st.warning` no topo da sidebar: *"Não foi possível carregar opções de filtros. Páginas operam sem filtragem."*

### 5.4 `render_sidebar(page) -> FilterSelection`

Renderiza o shell existente (cabeçalho "E-commerce Analytics" + título), depois 3 seções na ordem **Temporal → Cliente → Produto**. Cada seção tem título estilizado via `<div class="sidebar-section-title">` (CSS já presente em `app.py`).

Para cada `FilterDef` do registry:

```python
applies = page in fdef.pages
st.selectbox(
    fdef.label,
    options=options_for(fdef.key),
    key=fdef.key,
    disabled=not applies,
    help=None if applies else f"Disponível em {', '.join(fdef.pages)}.",
    format_func=label_for(fdef.key),  # apenas Mês usa format
)
```

Mês: opções armazenadas como nome PT-BR (`"Janeiro"`, ...), com mapa interno `MES_PT_TO_INT` para o `apply_*`. Default `"Todos"`.

Botão `st.button("Recarregar opções")` no fim da sidebar, discretamente estilizado, chama `load_filter_options.clear()`.

Retorna `FilterSelection(...)` com os valores correntes do `st.session_state`.

### 5.5 Helpers `apply_*`

```python
def apply_temporal(df, sel: FilterSelection) -> pd.DataFrame:
    df = filter_equals(df, "ano_venda", sel.ano)
    if sel.mes != FILTER_ALL:
        df = df[df["mes_venda"] == MES_PT_TO_INT[sel.mes]]
    df = filter_equals(df, "dia_semana_nome", sel.dia_semana)
    return df

def apply_customer(df, sel: FilterSelection) -> pd.DataFrame:
    df = filter_equals(df, "segmento_cliente", sel.segmento)
    df = filter_equals(df, "estado", sel.estado)
    return df

def apply_pricing(df, sel: FilterSelection) -> pd.DataFrame:
    df = filter_equals(df, "categoria", sel.categoria)
    df = filter_equals(df, "marca", sel.marca)
    df = filter_equals(df, "classificacao_preco", sel.classificacao)
    return df
```

`filter_equals` já existe em `utils.py` e é reutilizado tal qual. `top_n` é aplicado dentro de `views/clientes.py` lendo `sel.top_n` — lógica atual preservada.

## 6. UI / CSS

### 6.1 Header preto — fix

Adicionar ao bloco `inject_css()` em `app.py`:

```css
[data-testid="stHeader"] {
    background: transparent;
    height: 0;
}
[data-testid="stToolbar"] {
    right: 1rem;
    top: 0.5rem;
}
```

### 6.2 Estrutura visual da sidebar

Cabeçalho atual ("E-commerce Analytics" + "Relatório Analítico") preservado. Abaixo, três blocos com título existente `.sidebar-section-title`. Espaçamento entre seções via `st.divider()` ou `<hr>` consistente com o app atual.

### 6.3 Visual de filtro desabilitado

Streamlit nativo (`disabled=True`) já aplica opacidade reduzida. Reforço opcional via CSS:

```css
[data-testid="stSidebar"] [data-baseweb="select"][aria-disabled="true"] {
    opacity: 0.55;
}
[data-testid="stSidebar"] label:has(+ div [aria-disabled="true"]) {
    color: #94A3B8 !important;
}
```

Tooltip via `help=` exibe *"Disponível em <página>."* no ícone `(?)` ao lado do rótulo.

### 6.4 Mês em português

```python
MES_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MES_PT_TO_INT = {nome: i + 1 for i, nome in enumerate(MES_PT)}
```

Opções: `[FILTER_ALL] + [MES_PT[i-1] for i in meses_disponiveis_ordenados]`. Filtra apenas meses presentes no mart, em ordem do calendário.

### 6.5 Layout do conteúdo principal

Sem mudanças. Cada view continua renderizando seu próprio `<h1>` com a barra colorida e seus KPIs. O título da página (`📈 Vendas` etc.) sinaliza o contexto mesmo com a sidebar global.

## 7. Segurança

| Risco | Mitigação |
|---|---|
| Queries de opções puxando PII | `SELECT DISTINCT` apenas de colunas categóricas (`ano_venda`, `mes_venda`, `dia_semana_nome`, `segmento_cliente`, `estado`, `categoria`, `marca`, `classificacao_preco`). Nunca lê `cliente_id`, `nome_cliente`, `produto_id`, `nome_produto`, `nosso_preco`. |
| SQL injection via valores selecionados | `filters.py` **não monta SQL com input do usuário**. As 3 queries de opções são strings estáticas. Filtragem por valor selecionado acontece em pandas via `filter_equals` ou comparação direta — sem concatenação. |
| Cache servindo dados a outro usuário | `@st.cache_data` é por sessão/processo. Conteúdo cacheado contém só dimensões categóricas públicas (já visíveis no dashboard). Sem PII. |
| Stack trace vazando schema/credenciais | Erros do banco são interceptados em `load_filter_options()` e `views/*` e exibidos como mensagens genéricas, mantendo padrão atual (`"Não foi possível conectar ao banco de dados."`). |
| `.env` no repositório | Já protegido pelo `.gitignore`. Sem mudança. |
| Botão "Recarregar opções" | Apenas chama `load_filter_options.clear()`. Não recebe input nem é endpoint HTTP. Risco baixíssimo. |

## 8. Tratamento de erros

1. **`load_filter_options()` falha:** captura `Exception`, devolve dict de listas vazias, exibe `st.warning` no topo da sidebar. Filtros mostram só `"Todos"`. Cada view continua tentando carregar seu mart e exibe seu erro nativo se falhar.
2. **Filtro reduz a 0 linhas:** comportamento atual preservado: `st.warning("Nenhum dado encontrado para os filtros selecionados.")`.
3. **Inconsistência entre opções cacheadas e mart atual** (após `dbt run`): `filter_equals` devolve DataFrame vazio → cai no caso 2. Sem crash. TTL 5min limita a janela.

## 9. Plano de testes

Arquivo novo: `.llm/case-01-dashboard/tests/test_filters.py`.

| Teste | O que verifica |
|---|---|
| `test_filter_registry_pages_match_views` | Todo `FilterDef.pages` referencia páginas existentes; nenhum filtro fica órfão. |
| `test_filter_selection_defaults_safe` | `FilterSelection()` default não filtra (todos `Todos`, `top_n=10`). |
| `test_apply_temporal_with_all_returns_unchanged` | `apply_temporal` com seleção default devolve DataFrame igual à entrada. |
| `test_apply_temporal_filters_year_month_dow` | ano=2025, mês=Junho, dia=Segunda → DataFrame restrito corretamente. |
| `test_apply_customer_filters_segmento_estado` | Idem para segmento + estado. |
| `test_apply_pricing_filters_three_axes` | Idem para categoria + marca + classificação. |
| `test_mes_pt_round_trip` | `MES_PT_TO_INT["Janeiro"] == 1`, `MES_PT[0] == "Janeiro"`. |
| `test_load_filter_options_uses_distinct_queries` | Mock de `db.get_data`: 3 chamadas com `SELECT DISTINCT`, **nenhuma** referência a `nome_cliente`/`cliente_id`/`produto_id`/`nosso_preco` (anti-regressão de segurança). |

Testes existentes (`test_db.py`, `test_utils.py`, `test_vendas_view.py`) continuam passando. `test_vendas_view.py` pode precisar de ajuste se a assinatura de `render()` passar a receber `FilterSelection`.

## 10. Critérios de sucesso

1. `uv run pytest` passa, incluindo `test_filters.py`.
2. `uv run ruff check` passa.
3. Verificação manual no navegador (`python -m streamlit run .llm/case-01-dashboard/app.py`):
   - Sidebar mostra **9 filtros** agrupados em 3 seções, em qualquer das 3 páginas.
   - Em **Vendas**: bloco Cliente e Produto cinzas com tooltip *"Disponível em Clientes/Pricing."*; bloco Temporal ativo.
   - Em **Clientes**: bloco Temporal e Produto cinzas; bloco Cliente ativo.
   - Em **Pricing**: bloco Temporal e Cliente cinzas; bloco Produto ativo.
   - Selecionar `Ano=2025` em Vendas, navegar para Clientes, voltar para Vendas → seleção preservada.
   - Mês mostra `Janeiro, Fevereiro, …` em ordem de calendário.
   - Topo da página sem retângulo preto — fundo `#F8FAFC` contínuo.

## 11. Referências

- PRD do dashboard: `.llm/case-01-dashboard/PRD-dashboard.md`
- CLAUDE.md raiz (princípios "Pense Antes de Codificar", "Simplicidade Primeiro", "Mudanças Cirúrgicas")
- Marts dbt: `transform/models/gold/marts/{sales,customer_success,pricing}/`
- Estado atual das views: `.llm/case-01-dashboard/views/{vendas,clientes,pricing}.py`
- Helpers reutilizados: `.llm/case-01-dashboard/utils.py` (`filter_equals`, `DAY_ORDER`, `SEGMENT_LABELS`, `CLASS_LABELS`)
