WITH receita_por_cliente AS (
    SELECT
        f.id_cliente,
        c.nome_cliente,
        c.estado,
        SUM(f.receita_total) AS receita_total,
        COUNT(DISTINCT f.id_venda) AS total_compras,
        AVG(f.receita_total) AS ticket_medio,
        MIN(f.data_venda) AS primeira_compra,
        MAX(f.data_venda) AS ultima_compra
    FROM {{ ref('gold_fct_vendas') }} f
    LEFT JOIN {{ ref('gold_dim_clientes') }} c
        ON f.id_cliente = c.id_cliente
    {% if var('data_referencia_cs', none) is not none %}
    WHERE f.data_venda <= '{{ var("data_referencia_cs") }}'::date
    {% endif %}
    GROUP BY f.id_cliente, c.nome_cliente, c.estado
)

SELECT
    id_cliente AS cliente_id,
    nome_cliente,
    estado,
    receita_total,
    total_compras,
    ticket_medio,
    primeira_compra,
    ultima_compra,
    CASE
        WHEN receita_total >= {{ var('segmentacao_vip_threshold', 10000) }} THEN 'VIP'
        WHEN receita_total >= {{ var('segmentacao_top_tier_threshold', 5000) }} THEN 'TOP_TIER'
        ELSE 'REGULAR'
    END AS segmento_cliente,
    ROW_NUMBER() OVER (ORDER BY receita_total DESC) AS ranking_receita
FROM receita_por_cliente
ORDER BY receita_total DESC
