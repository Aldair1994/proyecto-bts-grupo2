-- =====================================================================
-- 03_aeropuertos.sql  --  Objetivo: aeropuertos con mayor incidencia de retrasos + mapa
-- Solo SELECT. Esquema dw.
--
-- PRUEBAS RÁPIDAS (limitar a un año): reemplazar
--     f.fecha_id BETWEEN 20100101 AND 20201231
-- por
--     f.fecha_id BETWEEN 20190101 AND 20191231
--
-- Definiciones:
--   * operado = NOT cancelado AND NOT desviado
--   * Aeropuerto de ORIGEN: se mide la salida (retraso_salida_15 = salida con >= 15 min de retraso).
--   * Aeropuerto de DESTINO: se mide la llegada (estado_vuelo = 'A tiempo').
--   * Mínimo de volumen (params.min_operados): un aeropuerto con 20 vuelos puede tener 100 % de
--     retrasos por azar; el ranking solo incluye aeropuertos con al menos ese número de vuelos
--     operados en el periodo. Se compara además dentro de "grandes" (top por volumen).
--   * COORDENADAS: dim_airport.latitud/longitud pueden ser NULL (pendiente de cargar).
--     Las consultas de mapa funcionan igual: devuelven NULL en esas columnas y la consulta 3.4
--     cuenta cuántos aeropuertos quedarían sin pintar. Mientras tanto usar 3.5 (por estado).
-- =====================================================================


-- 3.1 Ranking de aeropuertos de ORIGEN por retraso en la salida
-- Pregunta: ¿qué aeropuertos tienen más salidas retrasadas? Universo: vuelos operados que salen de
--   ese aeropuerto, con retraso_salida_15 no nulo. Mínimo: params.min_operados.
-- KPI: pct_salida_retrasada_15_sobre_operados (KPI-4).
WITH params AS (SELECT 5000 AS min_operados)
SELECT o.codigo_iata, o.nombre, o.ciudad, o.estado,
       count(*) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.retraso_salida_15)
             / NULLIF(count(*) FILTER (WHERE f.retraso_salida_15 IS NOT NULL), 0), 2) AS pct_salida_retrasada_15_sobre_operados,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_salida))::numeric, 1) AS mediana_retraso_salida_min,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.taxi_out))::numeric, 1)       AS mediana_taxi_out_min,
       rank() OVER (ORDER BY 100.0 * count(*) FILTER (WHERE f.retraso_salida_15)
                    / NULLIF(count(*) FILTER (WHERE f.retraso_salida_15 IS NOT NULL), 0) DESC) AS posicion_mas_retrasado
FROM dw.fact_flights f
JOIN dw.dim_airport o ON o.airport_id = f.origin_airport_id
CROSS JOIN params p
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
GROUP BY o.airport_id, o.codigo_iata, o.nombre, o.ciudad, o.estado, p.min_operados
HAVING count(*) >= p.min_operados
ORDER BY posicion_mas_retrasado
LIMIT 50;


-- 3.2 Ranking de aeropuertos de DESTINO por puntualidad de llegada
-- Pregunta: ¿a qué aeropuertos se llega con más retraso? Universo: operados que llegan a ese
--   aeropuerto. Mínimo: params.min_operados. KPI: pct_a_tiempo_sobre_operados (KPI-1).
WITH params AS (SELECT 5000 AS min_operados)
SELECT d.codigo_iata, d.nombre, d.estado,
       count(*) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo') / NULLIF(count(*), 0), 2) AS pct_a_tiempo_sobre_operados,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_llegada))::numeric, 1)         AS mediana_retraso_llegada_min,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.taxi_in))::numeric, 1)                 AS mediana_taxi_in_min
FROM dw.fact_flights f
JOIN dw.dim_airport d ON d.airport_id = f.destination_airport_id
CROSS JOIN params p
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
GROUP BY d.airport_id, d.codigo_iata, d.nombre, d.estado, p.min_operados
HAVING count(*) >= p.min_operados
ORDER BY pct_a_tiempo_sobre_operados ASC
LIMIT 50;


-- 3.3 Aeropuertos más grandes (top por volumen) y su puntualidad: comparación justa entre "hubs"
-- Pregunta: entre los N aeropuertos con más vuelos de salida, ¿cuáles son más y menos puntuales?
-- Universo: operados que salen de cada aeropuerto. N = params.top_n.
WITH params AS (SELECT 30 AS top_n),
base AS (
    SELECT o.codigo_iata, o.nombre, o.estado,
           count(*) AS vuelos_operados,
           count(*) FILTER (WHERE f.retraso_llegada_15) AS llegadas_retrasadas,
           count(*) FILTER (WHERE f.retraso_salida_15)  AS salidas_retrasadas,
           count(*) FILTER (WHERE f.retraso_llegada_15 IS NOT NULL) AS con_llegada,
           count(*) FILTER (WHERE f.retraso_salida_15 IS NOT NULL)  AS con_salida
    FROM dw.fact_flights f
    JOIN dw.dim_airport o ON o.airport_id = f.origin_airport_id
    WHERE f.fecha_id BETWEEN 20100101 AND 20201231
      AND NOT f.cancelado AND NOT f.desviado
    GROUP BY o.airport_id, o.codigo_iata, o.nombre, o.estado
),
grandes AS (SELECT *, rank() OVER (ORDER BY vuelos_operados DESC) AS posicion_volumen FROM base)
SELECT g.posicion_volumen, g.codigo_iata, g.nombre, g.estado, g.vuelos_operados,
       round(100.0 * g.salidas_retrasadas  / NULLIF(g.con_salida, 0), 2)  AS pct_salida_retrasada_15_sobre_operados,
       round(100.0 * g.llegadas_retrasadas / NULLIF(g.con_llegada, 0), 2) AS pct_llegada_retrasada_15_sobre_operados_desde_origen
FROM grandes g CROSS JOIN params p
WHERE g.posicion_volumen <= p.top_n
ORDER BY g.posicion_volumen;


-- 3.4 Datos para el MAPA por aeropuerto (origen)
-- Pregunta: mapa geográfico de puntualidad (requisito del dashboard). Universo: operados que
--   salen de cada aeropuerto. Funciona con coordenadas NULL: esos aeropuertos devuelven latitud y
--   longitud nulas (el mapa no los puede pintar; ver columna sin_coordenadas y la nota arriba).
-- Mínimo de volumen: params.min_operados.
WITH params AS (SELECT 1000 AS min_operados)
SELECT o.codigo_iata, o.nombre, o.ciudad, o.estado,
       o.latitud, o.longitud,
       (o.latitud IS NULL OR o.longitud IS NULL) AS sin_coordenadas,
       count(*) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.retraso_salida_15)
             / NULLIF(count(*) FILTER (WHERE f.retraso_salida_15 IS NOT NULL), 0), 2) AS pct_salida_retrasada_15_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo') / NULLIF(count(*), 0), 2) AS pct_a_tiempo_sobre_operados_desde_origen
FROM dw.fact_flights f
JOIN dw.dim_airport o ON o.airport_id = f.origin_airport_id
CROSS JOIN params p
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
GROUP BY o.airport_id, o.codigo_iata, o.nombre, o.ciudad, o.estado, o.latitud, o.longitud, p.min_operados
HAVING count(*) >= p.min_operados
ORDER BY vuelos_operados DESC;


-- 3.5 Alternativa al mapa sin coordenadas: puntualidad por ESTADO del aeropuerto de origen
-- Pregunta: ¿qué estados concentran más retrasos? (mapa de coropletas por estado: no requiere lat/long)
-- Universo: operados que salen de aeropuertos del estado. Mínimo: 5000 operados.
SELECT o.estado,
       count(*) AS vuelos_operados,
       count(DISTINCT o.airport_id) AS aeropuertos,
       round(100.0 * count(*) FILTER (WHERE f.retraso_salida_15)
             / NULLIF(count(*) FILTER (WHERE f.retraso_salida_15 IS NOT NULL), 0), 2) AS pct_salida_retrasada_15_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo') / NULLIF(count(*), 0), 2) AS pct_a_tiempo_sobre_operados_desde_origen
FROM dw.fact_flights f
JOIN dw.dim_airport o ON o.airport_id = f.origin_airport_id
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
GROUP BY o.estado
HAVING count(*) >= 5000
ORDER BY pct_salida_retrasada_15_sobre_operados DESC;


-- 3.6 Cobertura de coordenadas (cuántos vuelos quedarían fuera del mapa)
-- Pregunta: ¿qué porcentaje del tráfico está en aeropuertos sin coordenadas?
-- Universo: todos los vuelos programados por aeropuerto de origen.
SELECT count(*) AS vuelos_programados,
       count(*) FILTER (WHERE o.latitud IS NULL OR o.longitud IS NULL) AS vuelos_origen_sin_coordenadas,
       round(100.0 * count(*) FILTER (WHERE o.latitud IS NULL OR o.longitud IS NULL)
             / NULLIF(count(*), 0), 2) AS pct_vuelos_sin_coordenadas_sobre_programados,
       count(DISTINCT o.airport_id) FILTER (WHERE o.latitud IS NULL OR o.longitud IS NULL) AS aeropuertos_sin_coordenadas
FROM dw.fact_flights f
JOIN dw.dim_airport o ON o.airport_id = f.origin_airport_id
WHERE f.fecha_id BETWEEN 20100101 AND 20201231;


-- 3.7 Rutas (origen-destino) con peor puntualidad
-- Pregunta: ¿qué rutas se retrasan más? Universo: operados de la ruta (dirigida origen->destino).
-- Mínimo: params.min_operados vuelos operados por ruta (evita rutas casi sin tráfico).
-- KPI: pct_a_tiempo_sobre_operados. Útil para el análisis de geografía/distancia.
WITH params AS (SELECT 2000 AS min_operados)
SELECT o.codigo_iata AS origen, d.codigo_iata AS destino,
       round(avg(f.distancia)::numeric, 0) AS distancia_prom_millas,
       count(*) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo') / NULLIF(count(*), 0), 2) AS pct_a_tiempo_sobre_operados,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_llegada))::numeric, 1) AS mediana_retraso_llegada_min
FROM dw.fact_flights f
JOIN dw.dim_airport o ON o.airport_id = f.origin_airport_id
JOIN dw.dim_airport d ON d.airport_id = f.destination_airport_id
CROSS JOIN params p
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
GROUP BY o.airport_id, o.codigo_iata, d.airport_id, d.codigo_iata, p.min_operados
HAVING count(*) >= p.min_operados
ORDER BY pct_a_tiempo_sobre_operados ASC
LIMIT 30;
