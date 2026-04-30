# Spec: Dashboard Streamlit — E-commerce Analytics

**Data:** 2026-04-30  
**Status:** Aprovado  
**Arquivo de saída principal:** `case-01-dashboard/app.py`

---

## Contexto

Dashboard Streamlit para 3 diretores de um e-commerce consumirem os Data Marts Gold do PostgreSQL (Supabase). Cada diretor tem uma página dedicada. O design prioriza acessibilidade para daltonismo (paleta Okabe-Ito) e aparência corporativa profissional.

---

## Arquitetura de Arquivos

```
case-01-dashboard/
├── app.py              ← entry point: CSS global, sidebar, roteamento, apply_chart_style()
├── db.py               ← engine SQLAlchemy + função get_data(query) → DataFrame
├── pages/              ← módulos Python regulares (NOT Streamlit multi-page nativo)
│   ├── vendas.py       ← Página 1: Diretor Comercial
│   ├── clientes.py     ← Página 2: Diretora de Customer Success
│   └── pricing.py      ← Página 3: Diretor de Pricing
├── requirements.txt
└── .env.example
```

> `app.py` importa os módulos de `pages/` e chama a função `render()` da página selecionada. Não usa o sistema de roteamento nativo do Streamlit (`pages/` folder convention).

**Fontes de dados:**
- `public_gold_sales.gold_sales_vendas_temporais`
- `public_gold_cs.gold_customer_success_clientes_segmentacao`
- `public_gold_pricing.gold_pricing_precos_competitividade`

**Conexão (dois estágios, em `db.py`):**
1. Docker/produção: `POSTGRES_URL` do `.env`
2. Dev local (fallback): lê `~/.dbt/profiles.yml` via PyYAML, monta connection string de `ecommerce > outputs > dev`

---

## Identidade Visual

### Paleta de Cores (Okabe-Ito corporativa)

| Token | Hex | Uso |
|---|---|---|
| `primary` | `#0072B2` | Azul marinho — cor dominante, sidebar, Vendas |
| `accent` | `#E69F00` | Laranja âmbar — destaques, Pricing |
| `positive` | `#009E73` | Teal — favorável, Clientes, "mais barato" |
| `warning` | `#D55E00` | Vermelho-tijolo — alertas, "mais caro que todos" |
| `info` | `#56B4E9` | Azul céu — TOP_TIER, info secundária |
| `neutral` | `#CC79A7` | Lilás — 5ª categoria, "na média" |
| `bg` | `#F0F4F8` | Off-white azulado — fundo da página |
| `surface` | `#FFFFFF` | Cards, tabelas |
| `sidebar` | `#1A2B4A` | Navy escuro — sidebar |
| `text-primary` | `#1A2332` | Títulos e valores KPI |
| `text-secondary` | `#64748B` | Labels e legendas |

**Acessibilidade:** nenhum par primário compartilha matiz. `positive` é teal (não verde puro). `warning` é vermelho-tijolo (não vermelho puro). Distinguíveis em deuteranopia, protanopia e tritanopia, e em escala de cinza.

### Tipografia

**Google Fonts:** `Plus Jakarta Sans` — carregada via `@import` no CSS injetado.

| Elemento | Tamanho | Peso |
|---|---|---|
| Título da página (`h1`) | 28px | 700 |
| Subtítulo / seção | 16px | 600 |
| Valor KPI | 32px | 700 |
| Label KPI | 13px | 500 |
| Texto geral | 14px | 400 |

### Cards KPI

```css
background: #FFFFFF;
border-radius: 12px;
box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.06);
padding: 20px 24px;
border-left: 4px solid <cor-tema-da-página>;
```

Cor de borda por página:
- Vendas → `#0072B2`
- Clientes → `#009E73`
- Pricing → `#E69F00`

---

## Layout & Navegação

### Sidebar
- Fundo: `#1A2B4A` (navy)
- Título: **📊 E-commerce Analytics** — branco, 18px bold
- Navegação via `st.sidebar.radio`: `📈 Vendas` | `👥 Clientes` | `💰 Pricing`
- Filtros abaixo da navegação, separados por `st.sidebar.divider()`
- Item ativo: pill highlight em `#0072B2`

### Área de Conteúdo
- `st.set_page_config(layout="wide")`
- Header: título `h1` + linha divisória na cor tema da página
- KPIs: `st.columns(4)` com cards HTML via `st.markdown(unsafe_allow_html=True)`
- Gráficos: `px` Plotly com fundo transparente, fonte Plus Jakarta Sans
- Função `apply_chart_style(fig, title)` definida em `app.py`, importada nos módulos de página (`from app import apply_chart_style`), aplicada em todos os gráficos:
  - `plot_bgcolor='rgba(0,0,0,0)'`
  - `paper_bgcolor='rgba(0,0,0,0)'`
  - Grid cinza-claro `#E2E8F0`
  - Sem toolbar (`displayModeBar: False`)
  - Hover: fundo branco, borda suave

---

## Páginas

### Página 1 — Vendas (`pages/vendas.py`)

**Tabela:** `public_gold_sales.gold_sales_vendas_temporais`  
**Cor tema:** `#0072B2`  
**Filtro (sidebar):** seletor de mês `mes_venda` — default "Todos"

**KPIs:**
| Card | Lógica | Formato |
|---|---|---|
| Receita Total | `SUM(receita_total)` | `R$ X.XXX.XXX,XX` |
| Total de Vendas | `SUM(total_vendas)` | `X.XXX` |
| Ticket Médio | Receita Total / Total de Vendas | `R$ XXX,XX` |
| Clientes Únicos | `SUM(max por dia)`: subquery com `MAX(total_clientes_unicos) GROUP BY data_venda`, depois SUM | `XXX` |

**Gráficos:**
- **Linha 1 (full width):** Receita Diária — `px.line`, cor `#0072B2`, área preenchida 15% opacidade. X: `data_venda`, Y: `SUM(receita_total)` agrupado por `data_venda`.
- **Linha 2 col 1/2:** Receita por Dia da Semana — `px.bar`, cor `#E69F00`. Ordem fixa: Segunda → Domingo.
- **Linha 2 col 2/2:** Volume de Vendas por Hora — `px.bar`, cor `#56B4E9`. X: `hora_venda` (0–23).

---

### Página 2 — Clientes (`pages/clientes.py`)

**Tabela:** `public_gold_cs.gold_customer_success_clientes_segmentacao`  
**Cor tema:** `#009E73`  
**Filtro (sidebar):** `st.selectbox` por segmento (Todos / VIP / TOP_TIER / REGULAR) — aplicado apenas na tabela detalhada; KPIs sempre mostram totais.

**KPIs:**
| Card | Lógica | Formato |
|---|---|---|
| Total Clientes | `COUNT(*)` | `XXX` |
| Clientes VIP | `COUNT WHERE segmento = 'VIP'` | `XX` |
| Receita VIP | `SUM(receita_total) WHERE segmento = 'VIP'` | `R$ X.XXX.XXX` |
| Ticket Médio Geral | `AVG(ticket_medio)` | `R$ XXX,XX` |

**Gráficos:**
- **Linha 1 col 1/3:** Distribuição por Segmento — `px.pie` (donut, hole=0.5). Cores fixas: VIP=`#0072B2`, TOP_TIER=`#56B4E9`, REGULAR=`#CC79A7`.
- **Linha 1 col 2/3:** Receita por Segmento — `px.bar`. Mesmas cores dos segmentos.
- **Linha 2 col 1/2:** Top 10 Clientes — `px.bar orientation='h'`, cor `#009E73`. Ordenado por `ranking_receita`.
- **Linha 2 col 2/2:** Clientes por Estado — `px.bar`, cor `#E69F00`, ordenado DESC por contagem.
- **Tabela detalhada:** `st.dataframe` com todas as colunas, filtrada pelo selectbox da sidebar.

---

### Página 3 — Pricing (`pages/pricing.py`)

**Tabela:** `public_gold_pricing.gold_pricing_precos_competitividade`  
**Cor tema:** `#E69F00`  
**Filtro (sidebar):** `st.multiselect` de categoria — default: todas selecionadas.

**KPIs:**
| Card | Lógica | Formato |
|---|---|---|
| Produtos Monitorados | `COUNT(*)` | `XXX` |
| Mais Caros que Todos | `COUNT WHERE classificacao = 'MAIS_CARO_QUE_TODOS'` | `XX` |
| Mais Baratos que Todos | `COUNT WHERE classificacao = 'MAIS_BARATO_QUE_TODOS'` | `XX` |
| Diferença Média vs Mercado | `AVG(diferenca_percentual_vs_media)` | `+X.X%` |

**Cores das classificações (consistentes em todos os gráficos):**
| Classificação | Cor |
|---|---|
| `MAIS_CARO_QUE_TODOS` | `#D55E00` |
| `ACIMA_DA_MEDIA` | `#E69F00` |
| `NA_MEDIA` | `#CC79A7` |
| `ABAIXO_DA_MEDIA` | `#56B4E9` |
| `MAIS_BARATO_QUE_TODOS` | `#009E73` |

**Gráficos:**
- **Linha 1 col 1/3:** Posicionamento vs Concorrência — `px.pie`. Cores das classificações acima.
- **Linha 1 col 2/3:** Competitividade por Categoria — `px.bar`. Cor condicional: `#009E73` se negativo (mais barato), `#D55E00` se positivo (mais caro). Valor numérico exibido na barra.
- **Linha 2 (full width):** Scatter Competitividade × Volume — `px.scatter`. X: `diferenca_percentual_vs_media`, Y: `quantidade_total`, cor: `classificacao_preco` (paleta acima), tamanho: `receita_total`.
- **Tabela de alertas:** `st.dataframe` filtrada por `MAIS_CARO_QUE_TODOS`. Colunas: `produto_id`, `nome_produto`, `categoria`, `nosso_preco`, `preco_maximo_concorrentes`, `diferenca_percentual_vs_media`. Título: "⚠️ Produtos em Alerta".

---

## Requisitos Não Funcionais

- Sem cache agressivo — dados mudam após cada `dbt run`
- Erros de conexão: `st.error()` com mensagem amigável, não exceção não tratada
- Números em formato brasileiro: `locale` ou formatação manual (`f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')`)
- `requirements.txt` inclui: `streamlit`, `sqlalchemy`, `psycopg2-binary`, `pandas`, `plotly`, `python-dotenv`, `pyyaml`

---

## Critérios de Sucesso

1. `python -m streamlit run case-01-dashboard/app.py` sobe sem erro
2. Todas as 3 páginas carregam dados reais do Supabase
3. Filtros afetam KPIs e gráficos corretamente
4. Cards KPI renderizam com sombra e borda colorida
5. Gráficos usam paleta Okabe-Ito consistente entre páginas
6. Erros de conexão exibem mensagem amigável (não traceback)
