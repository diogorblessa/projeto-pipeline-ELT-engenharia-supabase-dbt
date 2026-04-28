SELECT
    c.id_cliente,
    c.nome_cliente,
    c.estado,
    c.pais,
    c.data_cadastro
FROM {{ ref('silver_clientes') }} c
