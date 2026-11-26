-- =====================================================================
-- 06_cancelaciones.sql  --  Objetivo: cancelaciones y desvíos (pregunta 25 del modelo)
-- Solo SELECT. Esquema dw.
--
-- PRUEBAS RÁPIDAS (limitar a un año): reemplazar
--     f.fecha_id BETWEEN 20100101 AND 20201231
-- por
--     f.fecha_id BETWEEN 20190101 AND 20191231
--
-- Definiciones:
--   * pct_cancelados_sobre_programados = cancelados / TODOS los vuelos programados * 100
--     (los cancelados no son "operados", por eso el universo es otro que el de puntualidad).
--   * pct_desviados_sobre_programados  = desviados / programados * 100.
--   * Referencia del equipo: ~1.9 % en el periodo y ~6 % en 2020 (verificar con 6.1).
--   * Causa (dim_cancelacion): A aerolínea, B clima, C NAS, D seguridad. Universo: cancelados.
--   * Evento raro: para el modelo (03_plan_modelos.md) reportar precisión y recall, no solo accuracy.
-- =====================================================================


-- 6.1 Tasa de cancelación y desvío por año
-- Pregunta: ¿cómo evolucionó la cancelación? Universo: vuelos programados del año.
-- KPI: pct_cancelados_sobre_programados (KPI-3).
SELECT f.fecha_id / 10000 AS anio,
       count(*) AS vuelos_programados,
       count(*) FILTER (WHERE f.cancelado) AS cancelados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2) AS pct_cancelados_sobre_programados,
       round(100.0 * count(*) FILTER (WHERE f.desviado)  / NULLIF(count(*), 0), 3) AS pct_desviados_sobre_programados
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY 1
ORDER BY 1;


-- 6.2 Cancelaciones por causa y año
-- Pregunta: ¿por qué se cancelan los vuelos? Universo: vuelos cancelados del año.
-- Los cancelados sin código aparecen como 'sin causa informada' (también medido en 01_calidad.sql 1.5).
SELECT f.fecha_id / 10000 AS anio,
       coalesce(c.cancelacion_id::text, '-') AS codigo_causa,
       coalesce(c.descripcion, 'sin causa informada') AS causa,
       count(*) AS cancelados,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY f.fecha_id / 10000), 2) AS pct_causa_sobre_cancelados_del_anio
FROM dw.fact_flights f
LEFT JOIN dw.dim_cancelacion c USING (cancelacion_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND f.cancelado
GROUP BY 1, 2, 3
ORDER BY 1, cancelados DESC;


-- 6.3 Tasa de cancelación por aerolínea (con tipo)
-- Pregunta: ¿qué aerolíneas cancelan más? Universo: programados de la aerolínea. Mínimo: 5000 programados.
-- Tipo: lista temporal (ver 02_puntualidad_aerolineas.sql para los códigos dudosos).
WITH tipo_aerolinea (codigo, tipo) AS (  -- TODO: reemplazar por dw.dim_airline.tipo cuando exista
    VALUES ('AA','tradicional'),('AS','tradicional'),('CO','tradicional'),('DL','tradicional'),
           ('HA','tradicional'),('UA','tradicional'),('US','tradicional'),
           ('B6','bajo costo'),('F9','bajo costo'),('FL','bajo costo'),('G4','bajo costo'),
           ('NK','bajo costo'),('VX','bajo costo'),('WN','bajo costo'),
           ('9E','regional'),('EV','regional'),('MQ','regional'),('OH','regional'),('OO','regional'),
           ('YV','regional'),('YX','regional'),('XE','regional'),('CP','regional'),('ZW','regional'),
           ('QX','regional'),('AX','regional'),('C5','regional'),('G7','regional'),('9K','regional'),
           ('KS','regional')
)
SELECT coalesce(t.tipo, 'sin clasificar') AS tipo, a.codigo,
       count(*) AS vuelos_programados,
       count(*) FILTER (WHERE f.cancelado) AS cancelados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2) AS pct_cancelados_sobre_programados,
       round(100.0 * count(*) FILTER (WHERE f.cancelacion_id = 'B') / NULLIF(count(*) FILTER (WHERE f.cancelado), 0), 2) AS pct_clima_sobre_cancelados
FROM dw.fact_flights f
JOIN dw.dim_airline a USING (airline_id)
LEFT JOIN tipo_aerolinea t ON t.codigo = a.codigo
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY t.tipo, a.codigo
HAVING count(*) >= 5000
ORDER BY 1, pct_cancelados_sobre_programados DESC;


-- 6.4 Tasa de cancelación por aeropuerto de origen
-- Pregunta: ¿qué aeropuertos tienen más cancelaciones? Universo: programados que salen del aeropuerto.
-- Mínimo: params.min_programados (evita aeropuertos pequeños con tasas inestables).
WITH params AS (SELECT 5000 AS min_programados)
SELECT o.codigo_iata, o.nombre, o.estado,
       count(*) AS vuelos_programados,
       count(*) FILTER (WHERE f.cancelado) AS cancelados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2) AS pct_cancelados_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_airport o ON o.airport_id = f.origin_airport_id
CROSS JOIN params p
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY o.airport_id, o.codigo_iata, o.nombre, o.estado, p.min_programados
HAVING count(*) >= p.min_programados
ORDER BY pct_cancelados_sobre_programados DESC
LIMIT 30;


-- 6.5 Cancelaciones por mes del año (estacionalidad, pre-COVID) y causa clima
-- Pregunta: ¿en qué meses se cancela más (tormentas de invierno, huracanes)?
-- Universo: programados del mes (2010-01 a 2020-02).
SELECT d.mes, d.nombre_mes,
       count(*) AS vuelos_programados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2) AS pct_cancelados_sobre_programados,
       round(100.0 * count(*) FILTER (WHERE f.cancelacion_id = 'B') / NULLIF(count(*), 0), 2) AS pct_cancelados_por_clima_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20200229
GROUP BY d.mes, d.nombre_mes
ORDER BY d.mes;


-- 6.6 Cancelaciones por día de la semana y franja horaria (variables candidatas del modelo 25)
-- Pregunta: ¿hay patrones de cancelación por día/hora? Universo: programados (pre-COVID).
SELECT d.dia_semana, b.franja,
       count(*) AS vuelos_programados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2) AS pct_cancelados_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
LEFT JOIN dw.dim_bloque_horario b ON b.bloque_id = f.bloque_salida_id
WHERE f.fecha_id BETWEEN 20100101 AND 20200229
GROUP BY d.dia_semana, b.franja
ORDER BY d.dia_semana, b.franja;


-- 6.7 Días con más cancelaciones (eventos: tormentas, huracanes, COVID)
-- Pregunta: ¿qué días concentran las cancelaciones masivas? Universo: programados del día.
-- Solo días con >= 1000 programados (descarta días con muy pocos datos).
SELECT d.fecha, d.nombre_dia,
       count(*) AS vuelos_programados,
       count(*) FILTER (WHERE f.cancelado) AS cancelados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2) AS pct_cancelados_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY d.fecha, d.nombre_dia
HAVING count(*) >= 1000
ORDER BY pct_cancelados_sobre_programados DESC
LIMIT 20;


-- 6.8 Desviados: por año y aerolínea (evento aún más raro)
-- Pregunta: ¿cuántos vuelos se desvían? Universo: programados. Mínimo: 1000 programados por aerolínea-año.
SELECT f.fecha_id / 10000 AS anio, a.codigo AS aerolinea,
       count(*) AS vuelos_programados,
       count(*) FILTER (WHERE f.desviado) AS desviados,
       round(100.0 * count(*) FILTER (WHERE f.desviado) / NULLIF(count(*), 0), 3) AS pct_desviados_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_airline a USING (airline_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY 1, a.codigo
HAVING count(*) >= 1000
ORDER BY 1, pct_desviados_sobre_programados DESC;


-- 6.9 Balance de clases para el modelo 25 (cancelado vs. no cancelado) por año
-- Pregunta: ¿qué tan desbalanceado está el objetivo? Universo: vuelos programados del año.
-- Sirve para fijar la prevalencia en entrenamiento/validación/prueba (ver 03_plan_modelos.md).
SELECT f.fecha_id / 10000 AS anio,
       count(*) FILTER (WHERE f.cancelado)     AS clase_1_cancelado,
       count(*) FILTER (WHERE NOT f.cancelado) AS clase_0_no_cancelado,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 3) AS prevalencia_pct_sobre_programados,
       round(count(*) FILTER (WHERE NOT f.cancelado)::numeric
             / NULLIF(count(*) FILTER (WHERE f.cancelado), 0), 1) AS razon_no_cancelado_por_cancelado
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY 1
ORDER BY 1;
