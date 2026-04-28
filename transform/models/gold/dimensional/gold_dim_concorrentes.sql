SELECT DISTINCT
    md5(lower(trim(pc.nome_concorrente))) AS concorrente_key,
    pc.nome_concorrente
FROM {{ ref('silver_preco_competidores') }} pc
WHERE pc.nome_concorrente IS NOT NULL
