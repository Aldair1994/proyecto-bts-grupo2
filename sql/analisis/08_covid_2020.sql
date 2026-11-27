-- =====================================================================
-- 08_covid_2020.sql  --  Objetivo: efecto COVID-19 en 2020 (tratado aparte)
-- Solo SELECT. Esquema dw.
--
-- PRUEBAS RÁPIDAS: este archivo ya solo lee 2019-2020 (fecha_id 20190101..20201231), así que no
--   hace falta limitarlo más. Para correr más rápido, restringir a un mes (p. ej. BETWEEN 20200301 AND 20200331).
--
-- Definiciones:
--   * dim_fecha.periodo_covid = true desde 2020-03-01 (supuesto del equipo, documentado).
--   * Comparación justa: cada mes/semana de 2020 se compara con el MISMO mes de 2019 (misma estacionalidad).
--   * Universos: puntualidad = operados; cancelación = programados; variación de volumen = programados.
--   * AVISO: en abril-mayo de 2020 volaban muy pocos vuelos y casi solo los más rentables; el % de
--     puntualidad sube por ese cambio de composición, no necesariamente por una mejor operación.
--   * Aerolíneas: Spirit (NK) solo desde 2015; Allegiant (G4) y Republic (YX) desde 2018; las fusiones
--     (CO, FL, US, VX) ya no aparecen en 2019-2020 como códigos propios (salvo VX hasta 2018).
-- =====================================================================


-- 8.1 Mes a mes: 2019 vs. 2020 (volumen, cancelación y puntualidad)
-- Pregunta: ¿cuánto cayó el tráfico y cuánto subió la cancelación mes a mes?
-- Universo: programados (volumen, cancelación) y operados (puntualidad) de cada mes.
-- KPI: variación_vuelos_pct_vs_2019 (KPI-7), pct_cancelados_sobre_programados (KPI-3), KPI-1.
WITH mensual AS (
    SELECT (f.fecha_id / 10000) AS anio, (f.fecha_id / 100) % 100 AS mes,
           count(*) AS programados,
           count(*) FILTER (WHERE f.cancelado) AS cancelados,
           count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS operados,
           count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo') AS a_tiempo
    FROM dw.fact_flights f
    WHERE f.fecha_id BETWEEN 20190101 AND 20201231
    GROUP BY 1, 2
)
SELECT m20.mes,
       m19.programados AS vuelos_programados_2019,
       m20.programados AS vuelos_programados_2020,
       round(100.0 * (m20.programados - m19.programados) / NULLIF(m19.programados, 0), 1) AS variacion_vuelos_pct_vs_2019,
       round(100.0 * m19.cancelados / NULLIF(m19.programados, 0), 2) AS pct_cancelados_sobre_programados_2019,
       round(100.0 * m20.cancelados / NULLIF(m20.programados, 0), 2) AS pct_cancelados_sobre_programados_2020,
       round(100.0 * m19.a_tiempo / NULLIF(m19.operados, 0), 2)      AS pct_a_tiempo_sobre_operados_2019,
       round(100.0 * m20.a_tiempo / NULLIF(m20.operados, 0), 2)      AS pct_a_tiempo_sobre_operados_2020
FROM mensual m20
LEFT JOIN mensual m19 ON m19.mes = m20.mes AND m19.anio = 2019
WHERE m20.anio = 2020
ORDER BY m20.mes;


-- 8.2 Antes vs. durante COVID, sobre los mismos meses de ambos años
-- Pregunta: comparación limpia: ene-feb (antes del corte) y mar-dic (periodo_covid) de 2020 contra
--   los mismos meses de 2019. Universo: programados / operados de cada grupo de meses.
SELECT d.anio,
       CASE WHEN d.mes <= 2 THEN 'ene-feb' ELSE 'mar-dic' END AS tramo,
       bool_or(d.periodo_covid) AS periodo_covid,
       count(*) AS vuelos_programados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2) AS pct_cancelados_sobre_programados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_a_tiempo_sobre_operados,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_llegada)
              FILTER (WHERE NOT f.cancelado AND NOT f.desviado))::numeric, 1) AS mediana_retraso_llegada_min,
       round((avg(f.distancia))::numeric, 0) AS distancia_promedio_millas
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20190101 AND 20201231
GROUP BY d.anio, 2
ORDER BY d.anio, 2;


-- 8.3 Curva semanal 2020 vs. 2019 (la caída y la recuperación)
-- Pregunta: ¿cómo cayó y se recuperó el tráfico semana a semana? Universo: programados por semana ISO.
-- Semanas ISO con AÑO ISO (extract(isoyear)), no el año calendario: el 30-31 dic 2019 pertenecen a la
--   semana ISO 1 de 2020 y el 31 dic 2018 a la semana 1 de 2019. Por eso el rango de fechas arranca en
--   20181231. La semana 53 de 2020 termina el 3 ene 2021 (fuera de los datos): sale incompleta.
WITH semanal AS (
    SELECT extract(isoyear FROM d.fecha)::int AS anio_iso, d.semana_iso, count(*) AS programados,
           count(*) FILTER (WHERE f.cancelado) AS cancelados
    FROM dw.fact_flights f
    JOIN dw.dim_fecha d USING (fecha_id)
    WHERE f.fecha_id BETWEEN 20181231 AND 20201231
    GROUP BY extract(isoyear FROM d.fecha)::int, d.semana_iso
)
SELECT s20.semana_iso,
       s19.programados AS vuelos_programados_2019,
       s20.programados AS vuelos_programados_2020,
       round(100.0 * s20.programados / NULLIF(s19.programados, 0), 1) AS vuelos_2020_como_pct_de_2019,
       round(100.0 * s20.cancelados / NULLIF(s20.programados, 0), 2)  AS pct_cancelados_sobre_programados_2020
FROM semanal s20
LEFT JOIN semanal s19 ON s19.semana_iso = s20.semana_iso AND s19.anio_iso = 2019
WHERE s20.anio_iso = 2020
ORDER BY s20.semana_iso;


-- 8.4 Por aerolínea: mar-dic 2019 vs. mar-dic 2020 (con tipo)
-- Pregunta: ¿quién resistió mejor? Universo: operados y programados de mar-dic de cada año.
-- Mínimo: 1000 programados por aerolínea en cada año. Tipo = lista temporal.
WITH tipo_aerolinea (codigo, tipo) AS (  -- TODO: reemplazar por dw.dim_airline.tipo cuando exista
    VALUES ('AA','tradicional'),('AS','tradicional'),('CO','tradicional'),('DL','tradicional'),
           ('HA','tradicional'),('UA','tradicional'),('US','tradicional'),
           ('B6','bajo costo'),('F9','bajo costo'),('FL','bajo costo'),('G4','bajo costo'),
           ('NK','bajo costo'),('VX','bajo costo'),('WN','bajo costo'),
           ('9E','regional'),('EV','regional'),('MQ','regional'),('OH','regional'),('OO','regional'),
           ('YV','regional'),('YX','regional'),('XE','regional'),('CP','regional'),('ZW','regional'),
           ('QX','regional'),('AX','regional'),('C5','regional'),('G7','regional'),('9K','regional'),
           ('KS','regional')
),
base AS (
    SELECT a.codigo, f.fecha_id / 10000 AS anio,
           count(*) AS programados,
           count(*) FILTER (WHERE f.cancelado) AS cancelados,
           count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS operados,
           count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo') AS a_tiempo
    FROM dw.fact_flights f
    JOIN dw.dim_airline a USING (airline_id)
    WHERE f.fecha_id BETWEEN 20190301 AND 20191231
       OR f.fecha_id BETWEEN 20200301 AND 20201231
    GROUP BY a.codigo, f.fecha_id / 10000
)
SELECT coalesce(t.tipo, 'sin clasificar') AS tipo, b19.codigo,
       b19.programados AS vuelos_programados_mar_dic_2019,
       b20.programados AS vuelos_programados_mar_dic_2020,
       round(100.0 * (b20.programados - b19.programados) / NULLIF(b19.programados, 0), 1) AS variacion_vuelos_pct,
       round(100.0 * b19.cancelados / NULLIF(b19.programados, 0), 2) AS pct_cancelados_sobre_programados_2019,
       round(100.0 * b20.cancelados / NULLIF(b20.programados, 0), 2) AS pct_cancelados_sobre_programados_2020,
       round(100.0 * b19.a_tiempo / NULLIF(b19.operados, 0), 2)      AS pct_a_tiempo_sobre_operados_2019,
       round(100.0 * b20.a_tiempo / NULLIF(b20.operados, 0), 2)      AS pct_a_tiempo_sobre_operados_2020
FROM base b19
JOIN base b20 ON b20.codigo = b19.codigo AND b20.anio = 2020
LEFT JOIN tipo_aerolinea t ON t.codigo = b19.codigo
WHERE b19.anio = 2019
  AND b19.programados >= 1000 AND b20.programados >= 1000
ORDER BY 1, variacion_vuelos_pct;


-- 8.5 Por aeropuerto de origen: caída de vuelos mar-dic 2020 vs. mar-dic 2019
-- Pregunta: ¿qué aeropuertos perdieron más tráfico? Universo: programados que salen del aeropuerto.
-- Mínimo: 5000 programados en mar-dic 2019 (aeropuertos con volumen comparable).
WITH base AS (
    SELECT f.origin_airport_id, f.fecha_id / 10000 AS anio, count(*) AS programados,
           count(*) FILTER (WHERE f.cancelado) AS cancelados
    FROM dw.fact_flights f
    WHERE f.fecha_id BETWEEN 20190301 AND 20191231
       OR f.fecha_id BETWEEN 20200301 AND 20201231
    GROUP BY f.origin_airport_id, f.fecha_id / 10000
)
SELECT o.codigo_iata, o.nombre, o.estado,
       b19.programados AS vuelos_programados_mar_dic_2019,
       b20.programados AS vuelos_programados_mar_dic_2020,
       round(100.0 * (b20.programados - b19.programados) / NULLIF(b19.programados, 0), 1) AS variacion_vuelos_pct,
       round(100.0 * b20.cancelados / NULLIF(b20.programados, 0), 2) AS pct_cancelados_sobre_programados_2020
FROM base b19
JOIN base b20 ON b20.origin_airport_id = b19.origin_airport_id AND b20.anio = 2020
JOIN dw.dim_airport o ON o.airport_id = b19.origin_airport_id
WHERE b19.anio = 2019 AND b19.programados >= 5000
ORDER BY variacion_vuelos_pct
LIMIT 30;


-- 8.6 Causas de retraso y de cancelación: mar-dic 2019 vs. mar-dic 2020
-- Pregunta: ¿cambió el motivo de los retrasos y cancelaciones? Universos (en el alias): minutos de
--   operados con retraso >= 15; cancelados por causa.
SELECT d.anio,
       round((100.0 * sum(f.retraso_aerolinea)    FILTER (WHERE f.retraso_llegada_15 AND NOT f.cancelado AND NOT f.desviado)
              / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0))
                       FILTER (WHERE f.retraso_llegada_15 AND NOT f.cancelado AND NOT f.desviado), 0))::numeric, 2) AS pct_aerolinea_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_clima)        FILTER (WHERE f.retraso_llegada_15 AND NOT f.cancelado AND NOT f.desviado)
              / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0))
                       FILTER (WHERE f.retraso_llegada_15 AND NOT f.cancelado AND NOT f.desviado), 0))::numeric, 2) AS pct_clima_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_nas)          FILTER (WHERE f.retraso_llegada_15 AND NOT f.cancelado AND NOT f.desviado)
              / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0))
                       FILTER (WHERE f.retraso_llegada_15 AND NOT f.cancelado AND NOT f.desviado), 0))::numeric, 2) AS pct_nas_sobre_min_retraso_15,
       round((100.0 * sum(f.retraso_avion_tardio) FILTER (WHERE f.retraso_llegada_15 AND NOT f.cancelado AND NOT f.desviado)
              / NULLIF(sum(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0) + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0))
                       FILTER (WHERE f.retraso_llegada_15 AND NOT f.cancelado AND NOT f.desviado), 0))::numeric, 2) AS pct_avion_tardio_sobre_min_retraso_15,
       round(100.0 * count(*) FILTER (WHERE f.cancelacion_id = 'A') / NULLIF(count(*) FILTER (WHERE f.cancelado), 0), 2) AS pct_causa_aerolinea_sobre_cancelados,
       round(100.0 * count(*) FILTER (WHERE f.cancelacion_id = 'B') / NULLIF(count(*) FILTER (WHERE f.cancelado), 0), 2) AS pct_causa_clima_sobre_cancelados,
       round(100.0 * count(*) FILTER (WHERE f.cancelacion_id = 'C') / NULLIF(count(*) FILTER (WHERE f.cancelado), 0), 2) AS pct_causa_nas_sobre_cancelados,
       round(100.0 * count(*) FILTER (WHERE f.cancelacion_id = 'D') / NULLIF(count(*) FILTER (WHERE f.cancelado), 0), 2) AS pct_causa_seguridad_sobre_cancelados
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20190301 AND 20191231
   OR f.fecha_id BETWEEN 20200301 AND 20201231
GROUP BY d.anio
ORDER BY d.anio;


-- 8.7 Efecto del cambio de composición: distancia y tipo de vuelo en 2020 vs. 2019
-- Pregunta: ¿los vuelos de 2020 son "distintos" (más largos, otros horarios)? Esto explica parte del
--   cambio en puntualidad. Universo: operados de mar-dic de cada año, por franja horaria.
SELECT d.anio, b.franja,
       count(*) AS vuelos_operados,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY d.anio), 2) AS pct_del_anio_sobre_operados_mar_dic,
       round(avg(f.distancia)::numeric, 0) AS distancia_promedio_millas,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo') / NULLIF(count(*), 0), 2) AS pct_a_tiempo_sobre_operados
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
JOIN dw.dim_bloque_horario b ON b.bloque_id = f.bloque_salida_id
WHERE (f.fecha_id BETWEEN 20190301 AND 20191231 OR f.fecha_id BETWEEN 20200301 AND 20201231)
  AND NOT f.cancelado AND NOT f.desviado
GROUP BY d.anio, b.franja
ORDER BY d.anio, b.franja;
