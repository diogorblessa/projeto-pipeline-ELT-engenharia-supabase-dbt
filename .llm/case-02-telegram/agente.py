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


# ── Helpers de tool use ──────────────────────────────────────────────


def _executar_tool_call(block, settings: Settings) -> dict:
    """Executa um tool_use block e retorna o tool_result correspondente."""
    try:
        df = execute_query(block.input["sql"], settings.postgres_url)
        resultado = df.to_markdown(index=False) if not df.empty else "Sem resultados."
    except Exception as e:
        resultado = f"Erro ao executar SQL: {e}"

    return {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": resultado,
    }


# ── Chat livre ───────────────────────────────────────────────────────


def chat(pergunta: str, settings: Settings) -> str:
    log.info("Chat recebido: %s", pergunta[:80])

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())

    system = (
        "Você é um analista de dados de um e-commerce brasileiro.\n"
        "Responda perguntas usando os dados do banco PostgreSQL.\n"
        "Use a ferramenta executar_sql para consultar os dados necessários.\n"
        "Formate valores monetários em R$. Responda em português.\n"
        "Seja conciso e direto.\n\n"
        + SCHEMA
    )

    messages = [{"role": "user", "content": pergunta}]

    for _ in range(MAX_ITERACOES_TOOL):
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=2048,
            system=system,
            tools=[TOOL],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Não consegui gerar uma resposta."

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = [
                _executar_tool_call(block, settings)
                for block in response.content
                if block.type == "tool_use" and block.name == "executar_sql"
            ]
            messages.append({"role": "user", "content": tool_results})

    return "Limite de iterações atingido. Tente reformular a pergunta."


# ── Relatório executivo ──────────────────────────────────────────────


def _executar_queries_relatorio(settings: Settings) -> dict[str, pd.DataFrame]:
    dados = {}
    for nome, sql in QUERIES_RELATORIO.items():
        log.info("Consultando %s...", nome)
        dados[nome] = execute_query(sql, settings.postgres_url)
    return dados


def _montar_prompt_relatorio(dados: dict[str, pd.DataFrame]) -> str:
    return f"""Gere o relatório diário com base nos dados abaixo.

## Dados de Vendas (últimos 7 dias)
{dados["vendas"].to_markdown(index=False)}

## Segmentação de Clientes
{dados["clientes"].to_markdown(index=False)}

## Posicionamento de Preços
{dados["pricing"].to_markdown(index=False)}

## Produtos Críticos (mais caros que todos os concorrentes)
{dados["criticos"].to_markdown(index=False)}

Gere o relatório com 3 seções:
1. Comercial (para o Diretor Comercial)
2. Customer Success (para a Diretora de CS)
3. Pricing (para o Diretor de Pricing)

Comece com um resumo executivo de 3 linhas antes das seções."""


_SYSTEM_RELATORIO = (
    "Você é um analista de dados senior de um e-commerce.\n"
    "Sua função é gerar um relatório executivo diário para 3 diretores.\n"
    "Cada diretor tem necessidades diferentes:\n\n"
    "1. Diretor Comercial: receita, vendas, ticket médio e tendências.\n"
    "2. Diretora de Customer Success: segmentação de clientes, VIPs e riscos.\n"
    "3. Diretor de Pricing: posicionamento de preço vs concorrência e alertas.\n\n"
    "Regras do relatório:\n"
    "- Seja direto e acionável. Cada insight deve sugerir uma ação.\n"
    "- Use números reais dos dados fornecidos.\n"
    "- Formate valores monetários em reais (R$).\n"
    "- Destaque alertas críticos no início.\n"
    "- O relatório deve ter no máximo 1 página por diretor.\n"
    "- Use formato Markdown."
)


def _fallback_markdown(dados: dict[str, pd.DataFrame], erro: Exception) -> str:
    """Fallback se a API do Claude falhar: dados crus em markdown."""
    return (
        f"# Relatório (FALLBACK — Claude indisponível)\n"
        f"Erro: {erro}\n\n"
        f"## Vendas\n{dados['vendas'].to_markdown(index=False)}\n\n"
        f"## Clientes\n{dados['clientes'].to_markdown(index=False)}\n\n"
        f"## Pricing\n{dados['pricing'].to_markdown(index=False)}\n\n"
        f"## Críticos\n{dados['criticos'].to_markdown(index=False)}\n"
    )


def gerar_relatorio(settings: Settings) -> str:
    log.info("Iniciando geração do relatório...")
    dados = _executar_queries_relatorio(settings)

    log.info("Enviando para Claude API...")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
    prompt = _montar_prompt_relatorio(dados)

    try:
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=_SYSTEM_RELATORIO,
            messages=[{"role": "user", "content": prompt}],
        )
        relatorio = response.content[0].text
    except Exception as e:
        log.exception("Falha na API do Claude — usando fallback")
        relatorio = _fallback_markdown(dados, e)

    hoje = datetime.now().strftime("%Y-%m-%d")
    arquivo = Path(__file__).parent / f"relatorio_{hoje}.md"
    arquivo.write_text(relatorio, encoding="utf-8")
    log.info("Relatório salvo em: %s", arquivo.name)
    return relatorio
