SELECT
    p.id_produto,
    p.nome_produto,
    p.categoria,
    p.marca,
    p.preco_atual,
    p.faixa_preco,
    p.status_cadastro,
    p.data_criacao
FROM {{ ref('silver_produtos') }} p
