-- =====================================================================
-- 07_programado_vs_real.sql  --  Programado vs. real y distribución de retrasos (dashboard)
-- Solo SELECT. Esquema dw.
--
-- PRUEBAS RÁPIDAS (limitar a un año): reemplazar
--     f.fecha_id BETWEEN 20100101 AND 20201231
-- por
--     f.fecha_id BETWEEN 20190101 AND 20191231
--
-- Definiciones:
--   * Universo de todo el archivo: vuelos operados (NOT cancelado AND NOT desviado), porque los
--     cancelados no tienen horas reales y los desviados no tienen retraso de llegada.
--   * Duración programada = tiempo_programado (CRSElapsedTime); real = tiempo_real (ActualElapsedTime),
--     ambos en minutos. diferencia_real_menos_programado > 0 = el vuelo duró más de lo planeado.
--   * Horas hhmm (hora_salida_prog / hora_salida_real) son hora LOCAL de cada aeropuerto.
-- =====================================================================


-- 7.1 Duración programada vs. real por año y mes (gráfico de líneas del dashboard)
-- Pregunta: ¿cuánto se desvía la duración real de la programada? Universo: operados con ambos tiempos > 0.
-- KPI: diferencia_real_menos_programado_min (KPI-6, mediana).
SELECT f.fecha_id / 10000 AS anio, (f.fecha_id / 100) % 100 AS mes,
       count(*) AS vuelos_operados,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.tiempo_programado))::numeric, 1) AS mediana_tiempo_programado_min,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.tiempo_real))::numeric, 1)       AS mediana_tiempo_real_min,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.tiempo_real - f.tiempo_programado))::numeric, 1) AS mediana_diferencia_real_menos_programado_min,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_llegada))::numeric, 1)   AS mediana_retraso_llegada_min
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
  AND f.tiempo_programado > 0 AND f.tiempo_real > 0
GROUP BY 1, 2
ORDER BY 1, 2;


-- 7.2 Hora programada vs. real de salida y llegada por bloque horario
-- Pregunta: ¿a qué horas la salida real se aleja más de la programada? (descriptivo; NO es variable del modelo)
-- Universo: operados con retraso_salida y retraso_llegada no nulos, por bloque de salida programada.
SELECT b.bloque_id, b.etiqueta,
       count(*) AS vuelos_operados,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_salida))::numeric, 1)  AS mediana_retraso_salida_min,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_llegada))::numeric, 1) AS mediana_retraso_llegada_min,
       round((percentile_cont(0.9) WITHIN GROUP (ORDER BY f.retraso_llegada))::numeric, 1) AS p90_retraso_llegada_min,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo') / NULLIF(count(*), 0), 2) AS pct_a_tiempo_sobre_operados
FROM dw.fact_flights f
JOIN dw.dim_bloque_horario b ON b.bloque_id = f.bloque_salida_id
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
  AND f.retraso_salida IS NOT NULL AND f.retraso_llegada IS NOT NULL
GROUP BY b.bloque_id, b.etiqueta
ORDER BY b.bloque_id;


-- 7.3 Duración programada vs. real por rango de distancia
-- Pregunta: ¿las aerolíneas "acolchonan" los horarios? (real < programado = holgura en el itinerario)
-- Universo: operados con tiempos > 0 y distancia > 0.
SELECT CASE WHEN f.distancia < 500  THEN '1) < 500 mi'
            WHEN f.distancia < 1000 THEN '2) 500-999 mi'
            WHEN f.distancia < 1500 THEN '3) 1000-1499 mi'
            WHEN f.distancia < 2500 THEN '4) 1500-2499 mi'
            ELSE                         '5) >= 2500 mi' END AS rango_distancia,
       count(*) AS vuelos_operados,
       round(avg(f.tiempo_programado)::numeric, 1) AS prom_tiempo_programado_min,
       round(avg(f.tiempo_real)::numeric, 1)       AS prom_tiempo_real_min,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.tiempo_real - f.tiempo_programado))::numeric, 1) AS mediana_diferencia_real_menos_programado_min,
       round(100.0 * count(*) FILTER (WHERE f.tiempo_real > f.tiempo_programado) / NULLIF(count(*), 0), 2)   AS pct_mas_largos_que_programado_sobre_operados
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
  AND f.tiempo_programado > 0 AND f.tiempo_real > 0 AND f.distancia > 0
GROUP BY 1
ORDER BY 1;


-- 7.4 Duración programada vs. real por aerolínea
-- Pregunta: ¿qué aerolíneas cumplen mejor sus tiempos programados? Universo: operados con tiempos > 0.
-- Mínimo: 5000 operados por aerolínea.
SELECT a.codigo AS aerolinea,
       count(*) AS vuelos_operados,
       round(avg(f.tiempo_programado)::numeric, 1) AS prom_tiempo_programado_min,
       round(avg(f.tiempo_real)::numeric, 1)       AS prom_tiempo_real_min,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.tiempo_real - f.tiempo_programado))::numeric, 1) AS mediana_diferencia_real_menos_programado_min,
       round(100.0 * count(*) FILTER (WHERE f.tiempo_real > f.tiempo_programado) / NULLIF(count(*), 0), 2)   AS pct_mas_largos_que_programado_sobre_operados
FROM dw.fact_flights f
JOIN dw.dim_airline a USING (airline_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
  AND f.tiempo_programado > 0 AND f.tiempo_real > 0
GROUP BY a.codigo
HAVING count(*) >= 5000
ORDER BY mediana_diferencia_real_menos_programado_min DESC;


-- 7.5 Histograma de retraso de llegada (distribución de retrasos del dashboard)
-- Pregunta: ¿cómo se distribuyen los retrasos? Universo: operados con retraso_llegada no nulo.
-- Cubetas de 15 min; los extremos se agrupan (< -60 y >= 240 minutos) para que el gráfico sea legible.
SELECT least(greatest(floor(f.retraso_llegada / 15.0) * 15, -60), 240)::int AS cubeta_inicio_min,
       count(*) AS vuelos_operados,
       round(100.0 * count(*) / sum(count(*)) OVER (), 3) AS pct_sobre_operados
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
  AND f.retraso_llegada IS NOT NULL
GROUP BY 1
ORDER BY 1;


-- 7.6 Distribución por categoría de retraso (A tiempo / Leve / Moderado / Severo / Extremo) y año
-- Pregunta: ¿cambió la gravedad de los retrasos? Universo: operados con categoria_retraso no nula.
-- OJO: aquí 'A tiempo' (categoria_retraso) significa retraso de llegada <= 0 min; NO es el KPI-1
--   (estado_vuelo = 'A tiempo', llegada < 15 min).
SELECT f.fecha_id / 10000 AS anio, f.categoria_retraso,
       count(*) AS vuelos_operados,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY f.fecha_id / 10000), 2) AS pct_sobre_operados_del_anio
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND f.categoria_retraso IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, min(CASE f.categoria_retraso WHEN 'A tiempo' THEN 1 WHEN 'Leve' THEN 2 WHEN 'Moderado' THEN 3
                                         WHEN 'Severo' THEN 4 ELSE 5 END);


-- 7.7 Percentiles del retraso de llegada por año (cola de la distribución)
-- Pregunta: ¿empeoró la cola de retrasos? Universo: operados con retraso_llegada no nulo.
SELECT f.fecha_id / 10000 AS anio,
       count(*) AS vuelos_operados,
       round((percentile_cont(0.50) WITHIN GROUP (ORDER BY f.retraso_llegada))::numeric, 1) AS mediana_min,
       round((percentile_cont(0.75) WITHIN GROUP (ORDER BY f.retraso_llegada))::numeric, 1) AS p75_min,
       round((percentile_cont(0.90) WITHIN GROUP (ORDER BY f.retraso_llegada))::numeric, 1) AS p90_min,
       round((percentile_cont(0.95) WITHIN GROUP (ORDER BY f.retraso_llegada))::numeric, 1) AS p95_min,
       round((percentile_cont(0.99) WITHIN GROUP (ORDER BY f.retraso_llegada))::numeric, 1) AS p99_min
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
  AND f.retraso_llegada IS NOT NULL
GROUP BY 1
ORDER BY 1;


-- 7.8 Rutas con mayor desviación entre duración real y programada
-- Pregunta: ¿qué rutas se alargan más respecto a lo programado? Universo: operados de la ruta con
--   tiempos > 0. Mínimo: 2000 operados por ruta.
SELECT o.codigo_iata AS origen, d.codigo_iata AS destino,
       count(*) AS vuelos_operados,
       round(avg(f.tiempo_programado)::numeric, 1) AS prom_tiempo_programado_min,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.tiempo_real - f.tiempo_programado))::numeric, 1) AS mediana_diferencia_real_menos_programado_min
FROM dw.fact_flights f
JOIN dw.dim_airport o ON o.airport_id = f.origin_airport_id
JOIN dw.dim_airport d ON d.airport_id = f.destination_airport_id
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
  AND f.tiempo_programado > 0 AND f.tiempo_real > 0
GROUP BY o.airport_id, o.codigo_iata, d.airport_id, d.codigo_iata
HAVING count(*) >= 2000
ORDER BY mediana_diferencia_real_menos_programado_min DESC
LIMIT 30;
