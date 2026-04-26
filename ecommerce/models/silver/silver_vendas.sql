SELECT
    v.id_venda,
    v.data_venda,
    v.id_cliente,
    v.id_produto,
    v.canal_venda,
    v.quantidade,
    v.preco_unitario::numeric(10,2) AS preco_unitario,
      -- Colunas calculadas
    v.quantidade * v.preco_unitario::numeric(10,2) AS receita_total,
    CASE
        WHEN v.preco_unitario::numeric(10,2) < 100 THEN 'barato'
        WHEN v.preco_unitario::numeric(10,2) <= 500 THEN 'medio'
        ELSE 'caro'
    END AS faixa_preco,
    -- Dimensões temporais
    DATE(v.data_venda::timestamp) AS data_da_venda,
    EXTRACT(YEAR FROM v.data_venda::timestamp) AS ano_venda,
    EXTRACT(MONTH FROM v.data_venda::timestamp) AS mes_venda,
    EXTRACT(DAY FROM v.data_venda::timestamp) AS dia_venda,
    EXTRACT(DOW FROM v.data_venda::timestamp) AS dia_semana,
    TO_CHAR(v.data_venda::timestamp, 'HH24:MI') AS hora_venda
FROM {{ ref('bronze_vendas') }} v