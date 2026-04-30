# CLAUDE.md

Pipeline ELT de analytics para e-commerce: Python extrai Parquets do S3 e carrega no PostgreSQL; dbt transforma via Arquitetura Medallion (Bronze → Silver → Gold). Stack: uv workspace, dbt-postgres, Docker.

## Arquitetura

```
S3 Bucket (Parquet: vendas, clientes, produtos, preco_competidores)
  └─ extract_load (boto3 + pandas + SQLAlchemy)
     └─ PostgreSQL schema: public (tabelas raw)
        └─ Bronze (VIEWs) → Silver (TABLEs) → Gold dimensional (TABLEs)
           ├─ public_gold: gold_dim_clientes, gold_dim_produtos, gold_dim_datas,
           │               gold_dim_concorrentes, gold_fct_vendas, gold_fct_precos_competidores
           └─ Marts finais:
              ├─ public_gold_sales.gold_sales_vendas_temporais
              ├─ public_gold_cs.gold_customer_success_clientes_segmentacao
              └─ public_gold_pricing.gold_pricing_precos_competitividade
```

## Princípios de Desenvolvimento

**1. Pense Antes de Codificar** — Não assuma. Não esconda confusão. Exponha os trade-offs.
- Declare premissas explicitamente antes de implementar.
- Se houver múltiplas interpretações, apresente-as — não escolha em silêncio.
- Se existir uma abordagem mais simples, diga. Questione quando necessário.
- Se algo não está claro, pare. Nomeie a confusão. Pergunte.

**2. Simplicidade Primeiro** — Código mínimo que resolve o problema. Nada especulativo.
- Sem funcionalidades além do pedido, sem abstrações para código de uso único.
- Sem "flexibilidade" não solicitada, sem tratamento de erros impossíveis.
- Se escreveu 200 linhas e cabem em 50, reescreva.

**3. Mudanças Cirúrgicas** — Toque apenas o necessário. Limpe apenas a sua própria bagunça.
- Não melhore código adjacente, comentários ou formatação não relacionados ao pedido.
- Se notar código morto não relacionado, mencione — não delete.
- Cada linha alterada deve rastrear diretamente ao pedido.

**4. Execução Orientada a Objetivo** — Defina critérios de sucesso. Itere até verificar.
- Transforme tarefas em metas verificáveis antes de implementar:
  - "Adicionar validação" → "Escreva testes para entradas inválidas, depois faça-os passar"
  - "Corrigir o bug" → "Escreva um teste que reproduza, depois faça-o passar"
  - "Refatorar X" → "Garanta que os testes passam antes e depois"
- Para tarefas multi-etapa, declare um plano com verificação por etapa.

## Comandos Principais

### Convenção de Commits

Antes de qualquer `git commit`, leia o arquivo `COMMIT_GUIDELINES.md`.

### Pipeline Completo (atalho do dia a dia)

```bash
./scripts/run-pipeline.sh
```

O EL faz `DROP TABLE ... CASCADE` nas tabelas raw (apaga as views bronze); o `dbt run` logo em seguida reconstrói a cadeia bronze → silver → gold. Use este atalho sempre que ambas as etapas precisarem rodar.

## Convenções

**Nomenclatura:** modelos dbt no formato `camada_dominio` (`silver_vendas`, `gold_pricing`); colunas em snake_case PT-BR (`receita_total`, `ticket_medio`, `segmento_cliente`).

**Dimensões temporais:** sempre extrair `ano`, `mes`, `dia`, `dia_semana`, `hora` na camada silver para uso downstream.

## Segurança

- `.env` está no `.gitignore` — nunca commite credenciais reais
- Se um segredo vazar: rotacione imediatamente, mesmo após `git rm --cached` (o push já expôs a credencial)
- Antes de commitar: revise com `git status` e `git diff`

## Configuração de Ambiente

Variáveis obrigatórias no `.env` (use `.env.example` como template):

**Supabase:** use session pooler (porta 5432) — transaction pooler (6543) não é compatível com dbt.

## Documentação Técnica

@extract_load/CLAUDE.md
@transform/CLAUDE.md

| Documento | Conteúdo |
|---|---|
| `.llm/database.md` | Schemas completos das tabelas Gold |
| `transform/PRD-dbt.md` | Spec dbt: modelos, schemas, testes |
| `.llm/case-01-dashboard/PRD-dashboard.md` | Case: Dashboard Streamlit (3 diretores) |
| `.llm/case-02-telegram/PRD-agente-relatorios.md` | Case: Agente Telegram + Claude API |
| `COMMIT_GUIDELINES.md` | Guia completo de commits semânticos |
