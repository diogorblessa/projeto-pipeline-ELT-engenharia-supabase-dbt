# Spec: Correção e Evolução Local-First do Dashboard Case 01

**Data:** 2026-04-30
**Status:** Revisado pelo agente, pendente de revisão do usuário
**Escopo:** `.llm/case-01-dashboard`

## Contexto

O Case 01 é um dashboard Streamlit local para três diretorias de um e-commerce:
Comercial, Customer Success e Pricing. Ele consome os marts Gold publicados no
PostgreSQL/Supabase e deve rodar localmente com:

```bash
python -m streamlit run .llm/case-01-dashboard/app.py
```

O dashboard não será publicado no `docker-compose.yml`. O Compose continua restrito aos
serviços `extract` e `dbt`.

## Decisões de Escopo

- Manter execução local do Streamlit.
- Usar `POSTGRES_URL` como única fonte de conexão do dashboard, carregada do `.env` da raiz.
- Não adicionar fallback para `profiles.yml`.
- Não alterar schemas, marts ou regras de negócio dbt para acomodar a UI.
- Corrigir problemas que impeçam execução completa, incluindo `KeyError`, imports, entrypoint,
  workspace `uv`, testes e compatibilidade do Docker existente.
- Melhorar o design do dashboard com filtros laterais por domínio e navegação superior por abas.
- Tratar acentuação correta em português do Brasil como critério de aceite.

## Arquitetura Alvo

```text
.llm/case-01-dashboard/
  app.py
  db.py
  utils.py
  views/
    vendas.py
    clientes.py
    pricing.py
  tests/
    test_db.py
    test_utils.py
```

`app.py` é o entrypoint. Ele carrega o `.env` da raiz, injeta CSS global, monta a sidebar de
filtros e roteia as páginas por abas no topo.

`db.py` expõe `get_engine()` e `get_data(query)`. Se `POSTGRES_URL` estiver ausente ou inválida,
o erro deve ser capturado pela página e mostrado de forma amigável.

`utils.py` centraliza:

- paleta e tokens visuais;
- formatadores de `R$`, inteiros e percentuais;
- labels legíveis de segmentos e classificações;
- contratos mínimos de colunas;
- normalização de colunas conhecidas;
- helpers para filtros, cards e estilo Plotly.

As páginas em `views/` devem consumir os helpers, evitando lógica duplicada de formatação,
labels e validação de colunas.

## Contratos de Dados

### Vendas

Tabela fonte: `public_gold_sales.gold_sales_vendas_temporais`

Colunas mínimas:

- `data_venda`
- `ano_venda`
- `mes_venda`
- `dia_da_semana` ou `dia_semana_nome`
- `hora_venda`
- `receita_total`
- `total_vendas`
- `total_clientes_unicos`

Normalizações:

- `dia_da_semana` vira `dia_semana_nome` para uso interno.
- `Terca` vira `Terça`.
- `Sabado` vira `Sábado`.
- `mes_venda` é convertido para inteiro anulável antes de montar filtros.

### Clientes

Tabela fonte: `public_gold_cs.gold_customer_success_clientes_segmentacao`

Colunas mínimas:

- `cliente_id`
- `nome_cliente`
- `estado`
- `receita_total`
- `total_compras`
- `ticket_medio`
- `primeira_compra`
- `ultima_compra`
- `segmento_cliente`
- `ranking_receita`

A tabela detalhada deve exibir nomes legíveis e valores monetários em `R$`.

### Pricing

Tabela fonte: `public_gold_pricing.gold_pricing_precos_competitividade`

Colunas mínimas:

- `produto_id`
- `nome_produto`
- `categoria`
- `marca`
- `nosso_preco`
- `preco_medio_concorrentes`
- `preco_maximo_concorrentes`
- `diferenca_percentual_vs_media`
- `classificacao_preco`
- `receita_total`
- `quantidade_total`

Regras:

- `SEM_DADOS` entra em filtros, contagens e distribuição de classificação.
- Registros com `diferenca_percentual_vs_media` nulo não entram em médias percentuais.
- A tabela de alertas continua limitada a `MAIS_CARO_QUE_TODOS`.
- Preços, receitas e tickets aparecem com `R$`.

## Tratamento de Erros

As views não devem quebrar com traceback visível por `KeyError`. Antes de calcular filtros,
KPIs ou gráficos, cada página valida seu contrato mínimo.

Mensagens esperadas:

- `POSTGRES_URL não configurada. Defina a variável no .env da raiz do projeto.`
- `Não foi possível conectar ao banco de dados.`
- `A tabela <nome> não contém as colunas esperadas: <colunas>.`
- `Nenhum dado encontrado para os filtros selecionados.`

Todas as mensagens devem estar em português do Brasil, com acentuação correta.

## UX e Navegação

A interface segue o modelo aprovado na imagem enviada pelo usuário:

- sidebar com identidade do dashboard;
- navegação superior por abas: `Vendas`, `Clientes`, `Pricing`;
- filtros laterais agrupados por domínio;
- conteúdo principal com KPIs, bloco interpretativo curto e gráficos.

Filtros:

- **Filtros - Vendas:** `Ano`, `Mês`, `Dia da Semana`
- **Filtros - Clientes:** `Segmento`, `Estado`, `Top N Clientes`
- **Filtros - Pricing:** `Categoria`, `Marca`, `Classificação`

Os filtros devem ser claros, com opção equivalente a "Todos" quando fizer sentido. Filtros vazios
em multiselect não devem reverter silenciosamente para todos os dados se isso confundir o usuário;
devem mostrar mensagem de ausência de dados.

## Painéis

### Vendas

KPIs:

- Receita Total
- Total de Vendas
- Ticket Médio
- Clientes Únicos

Gráficos:

- Receita Diária, linha com área preenchida.
- Receita por Dia da Semana, barras ordenadas de Segunda a Domingo.
- Volume de Vendas por Hora, barras.

Os filtros de ano, mês e dia da semana afetam KPIs e gráficos.

### Clientes

KPIs:

- Total de Clientes
- Clientes VIP
- Receita VIP
- Ticket Médio Geral

Gráficos:

- Clientes por Segmento, preferencialmente barra horizontal com total e percentual.
- Receita por Segmento, barras com rótulos monetários.
- Top N Clientes por Receita, barras horizontais.
- Clientes por Estado, barras horizontais ordenadas.

O filtro `Top N Clientes` controla apenas o ranking. `Segmento` e `Estado` filtram KPIs,
gráficos e tabela, exceto se a página explicitar uma visão total.

### Pricing

KPIs:

- Produtos Monitorados
- Mais Caros que Todos
- Mais Baratos que Todos
- Acima da Média
- Diferença Média vs Mercado
- Receita Total
- Receita em Risco
- Percentual da Receita em Risco

`Receita em Risco` é a soma de `receita_total` dos produtos classificados como
`MAIS_CARO_QUE_TODOS`.

`Percentual da Receita em Risco` é `receita_em_risco / receita_total`.

Gráficos:

- Posicionamento vs Concorrência, barra horizontal ou donut apenas se as fatias ficarem legíveis.
- Competitividade Média por Categoria, barras com rótulos percentuais visíveis.
- Competitividade x Volume, bolhas agregadas para evitar excesso de pontos individuais.
- Tabela de alertas com produtos `MAIS_CARO_QUE_TODOS`.

A página deve incluir um bloco interpretativo curto, baseado somente nos dados filtrados, sem
prometer causalidade ou ROI.

## Legibilidade e Formatação

- Todo valor monetário deve usar `R$` em cards, tabelas, hovers e rótulos de gráficos.
- Percentuais devem usar `%`, sem `R$`.
- Rótulos longos podem usar formato compacto no gráfico e valor completo no hover.
- Eixos, legendas, títulos e mensagens devem estar em português com acentuação correta.
- Gráficos com categorias longas devem preferir barras horizontais.
- Textos e valores numéricos precisam ter contraste suficiente no fundo claro.
- A UI não deve exibir sequências típicas de mojibake em textos acentuados.

## Segurança

- Nenhuma credencial real deve ser versionada.
- `.env` da raiz continua ignorado pelo Git e pelo Docker.
- `.llm/case-01-dashboard/.env.example` pode existir apenas como template sem segredos.
- Não imprimir connection strings ou segredos em validações.
- Evitar `docker compose config` como evidência compartilhável, pois ele expande variáveis do
  `.env` em texto claro.

## Docker, Ignore Files e Workspace uv

Mesmo sem publicar o dashboard no Compose, o novo membro `.llm/case-01-dashboard` no workspace
`uv` não pode quebrar os Dockerfiles de `extract_load` e `transform`.

O design deve garantir uma das duas condições:

- os Dockerfiles copiam o `pyproject.toml` do dashboard antes do `uv sync --frozen`; ou
- o dashboard deixa de ser membro do workspace raiz e passa a ser validado de outra forma.

A opção preferida é manter o dashboard no workspace e ajustar os Dockerfiles, pois assim `uv run
pytest`, `uv run ruff check` e o lockfile continuam cobrindo o case 01.

`.gitignore` e `.dockerignore` devem continuar alinhados para:

- ignorar `.env` e `.env.*`, exceto `.env.example`;
- ignorar caches Python;
- ignorar artefatos dbt (`target`, `dbt_packages`, `logs`);
- não enviar `.llm` inteiro para contexto Docker;
- permitir no máximo `.llm/case-01-dashboard/pyproject.toml` no contexto Docker se isso for
  necessário para resolver o workspace `uv` com `--frozen`.

## Testes e Validação

Validação mínima antes de concluir implementação:

```bash
uv lock --check
uv run ruff check
uv run pytest
uv run --env-file .env --package transform dbt parse --project-dir transform --profiles-dir transform
uv run --env-file .env --package transform dbt build --project-dir transform --profiles-dir transform
python -m streamlit run .llm/case-01-dashboard/app.py
```

O smoke visual do Streamlit deve conferir:

- as três abas carregam;
- filtros aparecem na sidebar com acentuação correta;
- ausência de `KeyError`;
- mensagens amigáveis para filtros sem dados;
- gráficos legíveis;
- valores monetários com `R$`;
- textos sem mojibake.

Se Docker Desktop estiver indisponível, registrar que `docker compose build` não foi validado e
manter a análise como risco pendente.

## Critérios de Aceite

- Dashboard local abre sem erro com `POSTGRES_URL` válida.
- Todas as páginas carregam os marts Gold atuais.
- Não há `KeyError` por `dia_da_semana`, `dia_semana_nome`, `marca`, `classificacao_preco` ou
  outras colunas contratadas.
- Filtros novos funcionam conforme o domínio da página.
- Pricing exibe KPIs adicionais, receita em risco e texto executivo.
- Textos da UI e documentação do case estão acentuados corretamente.
- Não há credenciais reais versionadas.
- `uv lock --check`, `uv run ruff check` e `uv run pytest` passam.
- `dbt parse` e `dbt build` passam quando `.env` está carregado.
- Docker existente não fica incompatível com o workspace `uv`, ou a impossibilidade de validar
  Docker fica registrada por indisponibilidade do daemon.

## Fora de Escopo

- Criar serviço Streamlit no `docker-compose.yml`.
- Publicar o dashboard em ambiente externo.
- Alterar regras de negócio dos marts Gold.
- Trocar o banco de dados ou a estratégia de conexão.
- Adicionar autenticação ao dashboard.
