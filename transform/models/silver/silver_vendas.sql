WITH vendas_tipadas AS (
    SELECT
        nullif(trim(v.id_venda::text), '') AS id_venda,
        v.data_venda::timestamp AS data_venda,
        nullif(trim(v.id_cliente::text), '') AS id_cliente,
        nullif(trim(v.id_produto::text), '') AS id_produto,
        coalesce(
            nullif(replace(lower(trim(v.canal_venda::text)), ' ', '_'), ''),
            'NAO_INFORMADO'
        ) AS canal_venda,
        v.quantidade::integer AS quantidade,
        v.preco_unitario::numeric(10,2) AS preco_unitario
    FROM {{ ref('bronze_vendas') }} v
),

vendas_validas AS (
    SELECT
        *,
        row_number() OVER (
            PARTITION BY id_venda
            ORDER BY data_venda DESC NULLS LAST
        ) AS ordem
    FROM vendas_tipadas
    WHERE id_venda IS NOT NULL
      AND id_cliente IS NOT NULL
      AND id_produto IS NOT NULL
      AND data_venda IS NOT NULL
      AND quantidade > 0
      AND preco_unitario > 0
)

SELECT
    id_venda,
    data_venda,
    id_cliente,
    id_produto,
    canal_venda,
    quantidade,
    preco_unitario,
    quantidade * preco_unitario AS receita_total,
    CASE
        WHEN preco_unitario < {{ var('faixa_venda_barato_max', 100) }} THEN 'barato'
        WHEN preco_unitario <= {{ var('faixa_venda_medio_max', 500) }} THEN 'medio'
        ELSE 'caro'
    END AS faixa_preco,
    DATE(data_venda) AS data_da_venda,
    EXTRACT(YEAR FROM data_venda) AS ano_venda,
    EXTRACT(MONTH FROM data_venda) AS mes_venda,
    EXTRACT(DAY FROM data_venda) AS dia_venda,
    EXTRACT(DOW FROM data_venda) AS dia_semana,
    EXTRACT(HOUR FROM data_venda)::integer AS hora_venda,
    current_timestamp AS silver_processado_em
FROM vendas_validas
WHERE ordem = 1
