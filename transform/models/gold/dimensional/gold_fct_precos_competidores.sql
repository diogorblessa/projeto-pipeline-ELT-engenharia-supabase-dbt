WITH precos AS (
    SELECT
        pc.id_produto,
        md5(lower(trim(pc.nome_concorrente))) AS concorrente_key,
        pc.data_da_coleta,
        pc.preco_concorrente
    FROM {{ ref('silver_preco_competidores') }} pc
    WHERE pc.nome_concorrente IS NOT NULL
)

SELECT
    md5(
        id_produto::text
        || '|'
        || concorrente_key
        || '|'
        || data_da_coleta::text
    ) AS preco_competidor_key,
    id_produto,
    concorrente_key,
    data_da_coleta,
    preco_concorrente
FROM precos
