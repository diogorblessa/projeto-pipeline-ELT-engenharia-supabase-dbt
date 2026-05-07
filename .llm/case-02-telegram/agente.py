"""Agente Telegram — chat livre, relatório executivo e envio direto via API HTTP."""

from __future__ import annotations

import logging
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import anthropic
import pandas as pd
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from db import execute_query

# ── Settings ─────────────────────────────────────────────────────────
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    telegram: SecretStr
    anthropic_api_key: SecretStr
    postgres_url: SecretStr
    chat_id: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"


# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ── Constantes ───────────────────────────────────────────────────────
MAX_ITERACOES_TOOL = 10
TELEGRAM_MAX_CHARS = 4096

SCHEMA = """
Tabelas disponíveis no banco PostgreSQL:

1. public_gold_sales.gold_sales_vendas_temporais
   Colunas: data_venda (DATE), ano_venda, mes_venda, dia_venda, dia_semana_nome (VARCHAR),
            hora_venda, receita_total (NUMERIC), quantidade_total, total_vendas,
            total_clientes_unicos, ticket_medio (NUMERIC)

2. public_gold_cs.gold_customer_success_clientes_segmentacao
   Colunas: cliente_id (VARCHAR), nome_cliente, estado (VARCHAR(2)), receita_total (NUMERIC),
            total_compras, ticket_medio (NUMERIC), primeira_compra (DATE), ultima_compra (DATE),
            segmento_cliente (VIP | TOP_TIER | REGULAR), ranking_receita (INTEGER)

3. public_gold_pricing.gold_pricing_precos_competitividade
   Colunas: produto_id (VARCHAR), nome_produto, categoria, marca, nosso_preco (NUMERIC),
            preco_medio_concorrentes, preco_minimo_concorrentes, preco_maximo_concorrentes,
            total_concorrentes, diferenca_percentual_vs_media (NUMERIC),
            diferenca_percentual_vs_minimo (NUMERIC),
            classificacao_preco (MAIS_CARO_QUE_TODOS | ACIMA_DA_MEDIA | NA_MEDIA | ABAIXO_DA_MEDIA | MAIS_BARATO_QUE_TODOS),
            receita_total (NUMERIC), quantidade_total
"""

TOOL = {
    "name": "executar_sql",
    "description": "Executa query SQL SELECT no banco PostgreSQL do e-commerce.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Query SQL SELECT para executar.",
            }
        },
        "required": ["sql"],
    },
}

QUERIES_RELATORIO: dict[str, str] = {
    "vendas": """
        SELECT data_venda, dia_semana_nome,
            SUM(receita_total) AS receita,
            SUM(total_vendas) AS vendas,
            SUM(total_clientes_unicos) AS clientes,
            AVG(ticket_medio) AS ticket_medio
        FROM public_gold_sales.gold_sales_vendas_temporais
        GROUP BY data_venda, dia_semana_nome
        ORDER BY data_venda DESC
        LIMIT 7
    """,
    "clientes": """
        SELECT segmento_cliente,
            COUNT(*) AS total_clientes,
            SUM(receita_total) AS receita_total,
            AVG(ticket_medio) AS ticket_medio_avg,
            AVG(total_compras) AS compras_avg
        FROM public_gold_cs.gold_customer_success_clientes_segmentacao
        GROUP BY segmento_cliente
        ORDER BY receita_total DESC
    """,
    "pricing": """
        SELECT classificacao_preco,
            COUNT(*) AS total_produtos,
            AVG(diferenca_percentual_vs_media) AS dif_media_pct,
            SUM(receita_total) AS receita_impactada
        FROM public_gold_pricing.gold_pricing_precos_competitividade
        GROUP BY classificacao_preco
        ORDER BY total_produtos DESC
    """,
    "criticos": """
        SELECT nome_produto, categoria, nosso_preco,
            preco_medio_concorrentes,
            diferenca_percentual_vs_media,
            receita_total
        FROM public_gold_pricing.gold_pricing_precos_competitividade
        WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS'
        ORDER BY diferenca_percentual_vs_media DESC
        LIMIT 10
    """,
}
