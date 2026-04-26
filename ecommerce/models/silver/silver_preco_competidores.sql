SELECT
    pc.id_produto,
    pc.nome_concorrente,
    pc.preco_concorrente,
    pc.data_coleta,
    -- Coluna calculada
    DATE(pc.data_coleta::timestamp) AS data_da_coleta
FROM {{ ref('bronze_preco_competidores') }} pc
