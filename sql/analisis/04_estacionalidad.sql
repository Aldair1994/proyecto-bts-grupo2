-- =====================================================================
-- 04_estacionalidad.sql  --  Objetivo: patrones estacionales (mes, día, hora, feriados, temporada)
-- Solo SELECT. Esquema dw.
--
-- PRUEBAS RÁPIDAS (limitar a un año): reemplazar
--     f.fecha_id BETWEEN 20100101 AND 20200229
-- por
--     f.fecha_id BETWEEN 20190101 AND 20191231
--
-- Decisión: los patrones estacionales se calculan con 2010-01 a 2020-02 (antes de COVID,
--   dim_fecha.periodo_covid = false), porque marzo-diciembre de 2020 distorsiona la
--   estacionalidad (ver 08_covid_2020.sql). Para la serie completa usar 4.1.
-- Definiciones: operado = NOT cancelado AND NOT desviado;
--   pct_a_tiempo_sobre_operados = 'A tiempo' / operados * 100.
-- =====================================================================


-- 4.1 Serie mensual completa 2010-2020 (para el gráfico de tendencia; 2020 marcado aparte)
-- Pregunta: ¿cómo evolucionan vuelos y puntualidad mes a mes? Universo: operados del mes (puntualidad)
--   y programados (cancelación). periodo_covid = true desde 2020-03-01: tratarlo aparte.
-- Nota: periodo_covid es true desde 2020-03-01, así que marzo de 2020 ya es entero COVID; ningún
--   mes mezcla días de ambos periodos (bool_or y bool_and coinciden en todos los meses).
SELECT d.anio, d.mes,
       bool_or(d.periodo_covid) AS periodo_covid,
       count(*) AS vuelos_programados,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_a_tiempo_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2)       AS pct_cancelados_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY d.anio, d.mes
ORDER BY d.anio, d.mes;


-- 4.2 Estacionalidad por mes del año (promedio de todos los años pre-COVID)
-- Pregunta: ¿qué meses son los peores/mejores? Universo: operados de ese mes (todos los años 2010 a feb-2020).
-- Nota: enero y febrero incluyen 11 años y marzo-diciembre 10 (2010-2019): son comparables en %.
SELECT d.mes, d.nombre_mes,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_a_tiempo_sobre_operados,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_llegada)
              FILTER (WHERE NOT f.cancelado AND NOT f.desviado))::numeric, 1) AS mediana_retraso_llegada_min,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2) AS pct_cancelados_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20200229
GROUP BY d.mes, d.nombre_mes
ORDER BY d.mes;


-- 4.3 Por temporada
-- Pregunta: ¿invierno, primavera, verano u otoño? Universo: operados de la temporada (pre-COVID).
SELECT d.temporada,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_a_tiempo_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2)       AS pct_cancelados_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20200229
GROUP BY d.temporada
ORDER BY pct_a_tiempo_sobre_operados;


-- 4.4 Por día de la semana
-- Pregunta: ¿qué días de la semana hay más retrasos? Universo: operados de ese día (pre-COVID).
SELECT d.dia_semana, d.nombre_dia,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_a_tiempo_sobre_operados,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_llegada)
              FILTER (WHERE NOT f.cancelado AND NOT f.desviado))::numeric, 1) AS mediana_retraso_llegada_min
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20200229
GROUP BY d.dia_semana, d.nombre_dia
ORDER BY d.dia_semana;


-- 4.5 Por bloque horario de salida programada (hora 0-23) y franja
-- Pregunta: ¿a qué hora del día se acumulan los retrasos? (efecto cascada durante el día)
-- Universo: operados cuya salida programada cae en ese bloque (pre-COVID).
SELECT b.bloque_id, b.etiqueta, b.franja,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_a_tiempo_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2)       AS pct_cancelados_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_bloque_horario b ON b.bloque_id = f.bloque_salida_id
WHERE f.fecha_id BETWEEN 20100101 AND 20200229
GROUP BY b.bloque_id, b.etiqueta, b.franja
ORDER BY b.bloque_id;


-- 4.6 Mapa de calor: día de la semana x franja horaria
-- Pregunta: ¿qué combinación día-franja es la peor? Universo: operados (pre-COVID).
SELECT d.dia_semana, d.nombre_dia, b.franja,
       count(*) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo') / NULLIF(count(*), 0), 2) AS pct_a_tiempo_sobre_operados
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
JOIN dw.dim_bloque_horario b ON b.bloque_id = f.bloque_salida_id
WHERE f.fecha_id BETWEEN 20100101 AND 20200229
  AND NOT f.cancelado AND NOT f.desviado
GROUP BY d.dia_semana, d.nombre_dia, b.franja
ORDER BY d.dia_semana, b.franja;


-- 4.7 Feriados vs. días normales
-- Pregunta: ¿los feriados y fines de semana tienen más retrasos o cancelaciones?
-- Universo: operados (puntualidad) y programados (cancelación), pre-COVID.
SELECT d.es_feriado, d.es_fin_semana,
       count(DISTINCT d.fecha_id) AS dias,
       count(*) AS vuelos_programados,
       round(count(*)::numeric / NULLIF(count(DISTINCT d.fecha_id), 0), 0) AS vuelos_por_dia,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_a_tiempo_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2)       AS pct_cancelados_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20200229
GROUP BY d.es_feriado, d.es_fin_semana
ORDER BY d.es_feriado, d.es_fin_semana;


-- 4.8 Detalle por feriado (nombre)
-- Pregunta: ¿qué feriados son los peores? Universo: operados en días con feriado (pre-COVID).
-- Mínimo: 5000 operados por feriado (descarta nombres con pocos días). Depende de ref.us_holidays.
SELECT d.nombre_feriado,
       count(DISTINCT d.fecha_id) AS dias,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_a_tiempo_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2)       AS pct_cancelados_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20200229
  AND d.es_feriado
GROUP BY d.nombre_feriado
HAVING count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) >= 5000
ORDER BY pct_a_tiempo_sobre_operados;


-- 4.9 Volumen por semana ISO (demanda)
-- Pregunta: ¿cuándo se concentra la demanda? Universo: vuelos programados (pre-COVID); promedio por año.
SELECT d.semana_iso,
       count(*) AS vuelos_programados,
       round(count(*)::numeric / NULLIF(count(DISTINCT d.anio), 0), 0) AS vuelos_promedio_por_anio
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20200229
GROUP BY d.semana_iso
ORDER BY d.semana_iso;
