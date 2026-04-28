SELECT
    p.id_produto,
    p.nome_produto,
    p.categoria,
    p.marca,
    p.preco_atual,
    p.data_criacao,
    -- Coluna calculada
    CASE
        WHEN p.preco_atual > 1000 THEN 'PREMIUM'
        WHEN p.preco_atual > 500 THEN 'MEDIO'
        ELSE 'BASICO'
    END AS faixa_preco
FROM {{ ref('bronze_produtos') }} p
