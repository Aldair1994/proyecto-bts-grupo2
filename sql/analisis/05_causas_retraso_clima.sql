-- =====================================================================
-- 05_causas_retraso_clima.sql  --  Objetivo: causas de retraso, impacto del clima y la geografía
-- Solo SELECT. Esquema dw.
--
-- PRUEBAS RÁPIDAS (limitar a un año): reemplazar
--     f.fecha_id BETWEEN 20100101 AND 20201231
-- por
--     f.fecha_id BETWEEN 20190101 AND 20191231
--
-- REGLA DE UNIVERSO: BTS solo reporta las 5 causas (aerolínea, clima, NAS, seguridad, avión
--   tardío) cuando el vuelo llegó con retraso >= 15 min. Por eso la "participación de causas"
--   se calcula SOLO sobre vuelos operados con retraso_llegada >= 15 (retraso_llegada_15 = true).
--   Los nulos de causas fuera de ese universo son esperados, no un error.
--   Participación de una causa = minutos de esa causa / suma de minutos de las 5 causas * 100.
--   OJO: "clima" aquí es solo el WeatherDelay de BTS (clima extremo que impide operar). El clima
--   también aparece dentro de NAS (tráfico por clima) y avión tardío (efecto cascada), así que
--   subestima el impacto total del clima.
-- =====================================================================


-- 5.1 Participación de cada causa de retraso (periodo completo)
-- Pregunta: ¿qué causa explica más minutos de retraso? Universo: operados con retraso_llegada >= 15 min.
-- KPI: pct_causa_X_sobre_minutos_retraso_15 (KPI-5).
SELECT count(*) AS vuelos_retraso_15_o_mas,
       round(sum(f.retraso_llegada)::numeric / 1000000, 2) AS millones_min_retraso_llegada,
       round((100.0 * sum(f.retraso_aerolinea)    / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_aerolinea_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_clima)        / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_clima_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_nas)          / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_nas_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_seguridad)    / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_seguridad_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_avion_tardio) / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_avion_tardio_sobre_min_retraso_15
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND f.retraso_llegada_15
  AND NOT f.cancelado AND NOT f.desviado;


-- 5.2 Participación de causas por año (tendencia; 2020 aparte por COVID)
-- Pregunta: ¿cambió la mezcla de causas con el tiempo? Universo: operados con retraso >= 15 min del año.
SELECT f.fecha_id / 10000 AS anio,
       count(*) AS vuelos_retraso_15_o_mas,
       round((100.0 * sum(f.retraso_aerolinea)    / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_aerolinea_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_clima)        / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_clima_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_nas)          / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_nas_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_seguridad)    / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_seguridad_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_avion_tardio) / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_avion_tardio_sobre_min_retraso_15
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND f.retraso_llegada_15
  AND NOT f.cancelado AND NOT f.desviado
GROUP BY 1
ORDER BY 1;


-- 5.3 Causa DOMINANTE por vuelo (conteo de vuelos, no minutos)
-- Pregunta: ¿cuál es la causa principal en cada vuelo retrasado? Universo: operados con retraso >= 15
--   y al menos una causa informada. Empates: se asigna a la primera causa en el orden del CASE.
SELECT causa_principal,
       count(*) AS vuelos,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_sobre_vuelos_retraso_15_con_causa
FROM (
    SELECT CASE greatest(coalesce(f.retraso_aerolinea,0), coalesce(f.retraso_clima,0), coalesce(f.retraso_nas,0),
                         coalesce(f.retraso_seguridad,0), coalesce(f.retraso_avion_tardio,0))
                WHEN coalesce(f.retraso_aerolinea,0)    THEN 'aerolínea'
                WHEN coalesce(f.retraso_avion_tardio,0) THEN 'avión tardío'
                WHEN coalesce(f.retraso_nas,0)          THEN 'NAS'
                WHEN coalesce(f.retraso_clima,0)        THEN 'clima'
                ELSE 'seguridad' END AS causa_principal
    FROM dw.fact_flights f
    WHERE f.fecha_id BETWEEN 20100101 AND 20201231
      AND f.retraso_llegada_15
      AND NOT f.cancelado AND NOT f.desviado
      AND (f.retraso_aerolinea IS NOT NULL OR f.retraso_clima IS NOT NULL OR f.retraso_nas IS NOT NULL
           OR f.retraso_seguridad IS NOT NULL OR f.retraso_avion_tardio IS NOT NULL)
) x
GROUP BY causa_principal
ORDER BY vuelos DESC;


-- 5.4 Causas por aerolínea
-- Pregunta: ¿las aerolíneas se retrasan por motivos distintos? Universo: operados con retraso >= 15 min
--   de la aerolínea. Mínimo: 1000 vuelos con retraso >= 15 por aerolínea.
SELECT a.codigo AS aerolinea,
       count(*) AS vuelos_retraso_15_o_mas,
       round((100.0 * sum(f.retraso_aerolinea)    / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_aerolinea_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_clima)        / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_clima_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_nas)          / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_nas_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_avion_tardio) / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)), 0))::numeric, 2) AS pct_avion_tardio_sobre_min_retraso_15
FROM dw.fact_flights f
JOIN dw.dim_airline a USING (airline_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND f.retraso_llegada_15
  AND NOT f.cancelado AND NOT f.desviado
GROUP BY a.codigo
HAVING count(*) >= 1000
ORDER BY pct_aerolinea_sobre_min_retraso_15 DESC;


-- 5.5 Clima por mes del año (estacionalidad del clima, pre-COVID)
-- Pregunta: ¿en qué meses el clima pesa más? Dos universos, ambos en el alias:
--   * pct_retrasados_con_clima_sobre_retraso_15: de los operados con retraso >= 15 min, los que
--     tienen retraso_clima > 0.
--   * min_clima_por_vuelo_operado: minutos de retraso_clima (nulo = 0) / TODOS los operados del mes.
SELECT d.mes, d.nombre_mes,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS vuelos_operados,
       count(*) FILTER (WHERE f.retraso_llegada_15 AND NOT f.cancelado AND NOT f.desviado) AS vuelos_retraso_15_o_mas,
       round(100.0 * count(*) FILTER (WHERE f.retraso_clima > 0 AND f.retraso_llegada_15)
             / NULLIF(count(*) FILTER (WHERE f.retraso_llegada_15 AND NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_retrasados_con_clima_sobre_retraso_15,
       round((sum(coalesce(f.retraso_clima, 0)) FILTER (WHERE NOT f.cancelado AND NOT f.desviado)
              / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0))::numeric, 3) AS min_clima_por_vuelo_operado
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20200229
GROUP BY d.mes, d.nombre_mes
ORDER BY d.mes;


-- 5.6 Clima y geografía: retraso por clima según el ESTADO del aeropuerto de origen
-- Pregunta: ¿qué regiones sufren más retrasos por clima? Universo: operados que salen del estado;
--   min_clima_por_vuelo_operado = minutos de clima (nulo = 0) / todos los operados del estado.
-- Mínimo: 5000 operados por estado. Si no hay coordenadas del mapa, este cuadro sirve igual.
SELECT o.estado,
       count(*) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.retraso_clima > 0) / NULLIF(count(*), 0), 3) AS pct_con_retraso_clima_sobre_operados,
       round((sum(coalesce(f.retraso_clima, 0)) / NULLIF(count(*), 0))::numeric, 3)        AS min_clima_por_vuelo_operado,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo') / NULLIF(count(*), 0), 2) AS pct_a_tiempo_sobre_operados
FROM dw.fact_flights f
JOIN dw.dim_airport o ON o.airport_id = f.origin_airport_id
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
GROUP BY o.estado
HAVING count(*) >= 5000
ORDER BY min_clima_por_vuelo_operado DESC;


-- 5.7 Clima y geografía: aeropuertos de origen con más retraso por clima
-- Pregunta: ¿qué aeropuertos concentran los retrasos por clima? Universo: operados que salen del
--   aeropuerto. Mínimo: 5000 operados. (Es solo WeatherDelay de BTS; ver nota inicial.)
SELECT o.codigo_iata, o.nombre, o.estado,
       count(*) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.retraso_clima > 0) / NULLIF(count(*), 0), 3) AS pct_con_retraso_clima_sobre_operados,
       round((sum(coalesce(f.retraso_clima, 0)) / NULLIF(count(*), 0))::numeric, 3)        AS min_clima_por_vuelo_operado
FROM dw.fact_flights f
JOIN dw.dim_airport o ON o.airport_id = f.origin_airport_id
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
GROUP BY o.airport_id, o.codigo_iata, o.nombre, o.estado
HAVING count(*) >= 5000
ORDER BY min_clima_por_vuelo_operado DESC
LIMIT 30;


-- 5.8 Distancia y retraso (geografía de la ruta)
-- Pregunta: ¿los vuelos largos se retrasan más o menos? Universo: operados con distancia > 0.
--   Rangos en millas. KPI: pct_a_tiempo_sobre_operados por rango.
SELECT CASE WHEN f.distancia < 500  THEN '1) < 500 mi'
            WHEN f.distancia < 1000 THEN '2) 500-999 mi'
            WHEN f.distancia < 1500 THEN '3) 1000-1499 mi'
            WHEN f.distancia < 2500 THEN '4) 1500-2499 mi'
            ELSE                         '5) >= 2500 mi' END AS rango_distancia,
       count(*) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo') / NULLIF(count(*), 0), 2) AS pct_a_tiempo_sobre_operados,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_llegada))::numeric, 1) AS mediana_retraso_llegada_min,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_llegada - f.retraso_salida))::numeric, 1) AS mediana_cambio_en_vuelo_min
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
  AND f.distancia > 0
GROUP BY 1
ORDER BY 1;


-- 5.9 Chequeo de la regla: causas informadas fuera del universo >= 15 min (debe ser ~0)
-- Pregunta: ¿se respeta que las causas solo existen con retraso >= 15? Universo: todos los vuelos.
SELECT count(*) FILTER (WHERE f.retraso_llegada_15) AS retraso_15_o_mas,
       count(*) FILTER (WHERE f.retraso_llegada_15 AND f.retraso_clima IS NULL AND f.retraso_aerolinea IS NULL
                          AND f.retraso_nas IS NULL AND f.retraso_seguridad IS NULL
                          AND f.retraso_avion_tardio IS NULL) AS retraso_15_o_mas_sin_causas,
       count(*) FILTER (WHERE NOT coalesce(f.retraso_llegada_15, false)
                          AND (f.retraso_clima IS NOT NULL OR f.retraso_aerolinea IS NOT NULL
                               OR f.retraso_nas IS NOT NULL OR f.retraso_seguridad IS NOT NULL
                               OR f.retraso_avion_tardio IS NOT NULL)) AS causas_fuera_del_universo
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231;
