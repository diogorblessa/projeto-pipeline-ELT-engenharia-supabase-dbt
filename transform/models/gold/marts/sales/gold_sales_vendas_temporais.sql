SELECT
    f.data_venda,
    d.ano AS ano_venda,
    d.mes AS mes_venda,
    d.dia AS dia_venda,
    d.dia_semana_nome AS dia_da_semana,
    f.hora_venda,
    SUM(f.receita_total) AS receita_total,
    SUM(f.quantidade) AS quantidade_total,
    COUNT(DISTINCT f.id_venda) AS total_vendas,
    COUNT(DISTINCT f.id_cliente) AS total_clientes_unicos,
    AVG(f.receita_total) AS ticket_medio
FROM {{ ref('gold_fct_vendas') }} f
LEFT JOIN {{ ref('gold_dim_datas') }} d
    ON f.data_venda = d.data
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY data_venda DESC, f.hora_venda
