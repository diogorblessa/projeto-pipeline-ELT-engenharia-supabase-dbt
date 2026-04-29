WITH produtos_tipados AS (
    SELECT
        nullif(trim(p.id_produto::text), '') AS id_produto,
        coalesce(nullif(trim(p.nome_produto::text), ''), 'NAO_INFORMADO') AS nome_produto,
        coalesce(nullif(upper(trim(p.categoria::text)), ''), 'NAO_INFORMADO') AS categoria,
        coalesce(nullif(upper(trim(p.marca::text)), ''), 'NAO_INFORMADO') AS marca,
        p.preco_atual::numeric(10,2) AS preco_atual,
        p.data_criacao::timestamp AS data_criacao
    FROM {{ ref('bronze_produtos') }} p
),

produtos_deduplicados AS (
    SELECT
        *,
        row_number() OVER (
            PARTITION BY id_produto
            ORDER BY data_criacao DESC NULLS LAST
        ) AS ordem
    FROM produtos_tipados
    WHERE id_produto IS NOT NULL
),

produtos_cadastrados AS (
    SELECT
        id_produto,
        nome_produto,
        categoria,
        marca,
        preco_atual,
        data_criacao,
        CASE
            WHEN preco_atual IS NULL THEN 'NAO_INFORMADO'
            WHEN preco_atual > 1000 THEN 'PREMIUM'
            WHEN preco_atual > 500 THEN 'MEDIO'
            ELSE 'BASICO'
        END AS faixa_preco,
        'CADASTRADO' AS status_cadastro
    FROM produtos_deduplicados
    WHERE ordem = 1
),

produtos_referenciados AS (
    SELECT DISTINCT
        nullif(trim(id_produto::text), '') AS id_produto
    FROM {{ ref('bronze_vendas') }}
    WHERE nullif(trim(id_produto::text), '') IS NOT NULL

    UNION

    SELECT DISTINCT
        nullif(trim(id_produto::text), '') AS id_produto
    FROM {{ ref('bronze_preco_competidores') }}
    WHERE nullif(trim(id_produto::text), '') IS NOT NULL
),

produtos_inferidos AS (
    SELECT
        r.id_produto,
        'Produto sem cadastro ' || r.id_produto AS nome_produto,
        'NAO_INFORMADO' AS categoria,
        'NAO_INFORMADO' AS marca,
        NULL::numeric(10,2) AS preco_atual,
        NULL::timestamp AS data_criacao,
        'NAO_INFORMADO' AS faixa_preco,
        'INFERIDO' AS status_cadastro
    FROM produtos_referenciados r
    LEFT JOIN produtos_cadastrados p
        ON r.id_produto = p.id_produto
    WHERE p.id_produto IS NULL
)

SELECT
    id_produto,
    nome_produto,
    categoria,
    marca,
    preco_atual,
    data_criacao,
    faixa_preco,
    status_cadastro
FROM produtos_cadastrados

UNION ALL

SELECT
    id_produto,
    nome_produto,
    categoria,
    marca,
    preco_atual,
    data_criacao,
    faixa_preco,
    status_cadastro
FROM produtos_inferidos
