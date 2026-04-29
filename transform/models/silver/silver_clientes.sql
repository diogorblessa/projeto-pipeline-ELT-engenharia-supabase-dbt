WITH clientes_tipados AS (
    SELECT
        nullif(trim(c.id_cliente::text), '') AS id_cliente,
        coalesce(nullif(trim(c.nome_cliente::text), ''), 'NAO_INFORMADO') AS nome_cliente,
        coalesce(nullif(upper(trim(c.estado::text)), ''), 'NAO_INFORMADO') AS estado,
        coalesce(nullif(initcap(trim(c.pais::text)), ''), 'NAO_INFORMADO') AS pais,
        c.data_cadastro::timestamp AS data_cadastro
    FROM {{ ref('bronze_clientes') }} c
),

clientes_deduplicados AS (
    SELECT
        *,
        row_number() OVER (
            PARTITION BY id_cliente
            ORDER BY data_cadastro DESC NULLS LAST
        ) AS ordem
    FROM clientes_tipados
    WHERE id_cliente IS NOT NULL
)

SELECT
    id_cliente,
    nome_cliente,
    estado,
    pais,
    data_cadastro,
    current_timestamp AS silver_processado_em
FROM clientes_deduplicados
WHERE ordem = 1
