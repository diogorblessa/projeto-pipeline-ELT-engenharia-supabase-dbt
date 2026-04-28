WITH datas_unificadas AS (
    SELECT
        v.data_da_venda AS data
    FROM {{ ref('silver_vendas') }} v

    UNION

    SELECT
        pc.data_da_coleta AS data
    FROM {{ ref('silver_preco_competidores') }} pc
),

datas_validas AS (
    SELECT DISTINCT
        data
    FROM datas_unificadas
    WHERE data IS NOT NULL
)

SELECT
    data,
    EXTRACT(YEAR FROM data::timestamp) AS ano,
    EXTRACT(MONTH FROM data::timestamp) AS mes,
    EXTRACT(DAY FROM data::timestamp) AS dia,
    EXTRACT(DOW FROM data::timestamp) AS dia_semana,
    CASE EXTRACT(DOW FROM data::timestamp)
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda'
        WHEN 2 THEN 'Terca'
        WHEN 3 THEN 'Quarta'
        WHEN 4 THEN 'Quinta'
        WHEN 5 THEN 'Sexta'
        WHEN 6 THEN 'Sabado'
    END AS dia_semana_nome
FROM datas_validas
ORDER BY data
