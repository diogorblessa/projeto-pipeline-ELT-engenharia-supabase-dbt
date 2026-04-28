SELECT
    v.id_venda,
    v.id_cliente,
    v.id_produto,
    v.data_da_venda AS data_venda,
    v.canal_venda,
    v.quantidade,
    v.preco_unitario,
    v.receita_total,
    v.hora_venda
FROM {{ ref('silver_vendas') }} v
