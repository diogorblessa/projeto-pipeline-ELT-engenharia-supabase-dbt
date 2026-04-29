WITH precos_tipados AS (
    SELECT
        nullif(trim(pc.id_produto::text), '') AS id_produto,
        coalesce(nullif(initcap(trim(pc.nome_concorrente::text)), ''), 'NAO_INFORMADO') AS nome_concorrente,
        pc.preco_concorrente::numeric(10,2) AS preco_concorrente,
        pc.data_coleta::timestamp AS data_coleta,
        DATE(pc.data_coleta::timestamp) AS data_da_coleta
    FROM {{ ref('bronze_preco_competidores') }} pc
),

precos_validos AS (
    SELECT
        md5(
            id_produto
            || '|'
            || lower(trim(nome_concorrente))
            || '|'
            || data_da_coleta::text
        ) AS preco_competidor_key,
        id_produto,
        nome_concorrente,
        preco_concorrente,
        data_coleta,
        data_da_coleta,
        row_number() OVER (
            PARTITION BY id_produto, lower(trim(nome_concorrente)), data_da_coleta
            ORDER BY data_coleta DESC NULLS LAST
        ) AS ordem
    FROM precos_tipados
    WHERE id_produto IS NOT NULL
      AND nome_concorrente <> 'NAO_INFORMADO'
      AND data_da_coleta IS NOT NULL
      AND preco_concorrente > 0
)

SELECT
    preco_competidor_key,
    id_produto,
    nome_concorrente,
    preco_concorrente,
    data_coleta,
    data_da_coleta
FROM precos_validos
WHERE ordem = 1
