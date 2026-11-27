-- =====================================================================
-- 01_calidad.sql  --  Informe de calidad de datos (sección 3.2, Data Understanding)
-- Solo SELECT. Esquema dw. Se corre sobre la base completa (~67 M de filas).
--
-- PRUEBAS RÁPIDAS (limitar a un año): en cada consulta reemplazar
--     f.fecha_id BETWEEN 20100101 AND 20201231
-- por
--     f.fecha_id BETWEEN 20190101 AND 20191231
-- (la tabla está particionada por fecha_id, así que Postgres solo lee ese año).
--
-- Definiciones usadas en todos los archivos de sql/analisis/:
--   * operado     = NOT cancelado AND NOT desviado
--   * programado  = todos los vuelos (cualquier estado)
-- =====================================================================


-- 1.1 Conteo de vuelos por año y mes (cobertura y detección de meses faltantes)
-- Pregunta: ¿la carga está completa? (esperado: ~67.2 M en 2010-2020, 132 meses)
-- Universo: todos los vuelos programados. KPI relacionado: volumen (vuelos_programados).
SELECT f.fecha_id / 10000            AS anio,
       (f.fecha_id / 100) % 100      AS mes,
       count(*)                      AS vuelos_programados,
       count(*) FILTER (WHERE f.cancelado)  AS cancelados,
       count(*) FILTER (WHERE f.desviado)   AS desviados,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS operados
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY 1, 2
ORDER BY 1, 2;


-- 1.2 Meses esperados sin ningún vuelo (huecos en la carga)
-- Pregunta: ¿falta algún mes del rango 2010-01 a 2020-12?
-- Universo: calendario dim_fecha vs. hechos. Resultado vacío = sin huecos.
SELECT d.anio, d.mes
FROM dw.dim_fecha d
WHERE d.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT EXISTS (SELECT 1 FROM dw.fact_flights f
                  WHERE f.fecha_id BETWEEN d.anio * 10000 + d.mes * 100 + 1
                                       AND d.anio * 10000 + d.mes * 100 + 31)
GROUP BY d.anio, d.mes
ORDER BY d.anio, d.mes;


-- 1.3 Días del calendario sin vuelos (más fino que el mes)
-- Pregunta: ¿hay días completos sin datos? Universo: días de dim_fecha. Resultado vacío = OK.
SELECT d.fecha, d.nombre_dia
FROM dw.dim_fecha d
LEFT JOIN (SELECT DISTINCT fecha_id FROM dw.fact_flights
           WHERE fecha_id BETWEEN 20100101 AND 20201231) x USING (fecha_id)
WHERE d.fecha_id BETWEEN 20100101 AND 20201231
  AND x.fecha_id IS NULL
ORDER BY d.fecha;


-- 1.4 Nulos por columna clave, por año (porcentaje sobre TODOS los vuelos del año)
-- Pregunta: ¿qué tan completas están las columnas? Ojo: muchos nulos son ESPERADOS
--   (cancelados sin horas reales; causas solo con retraso de llegada >= 15 min).
-- Universo de cada % = todos los vuelos programados del año. KPI: completitud.
SELECT f.fecha_id / 10000 AS anio,
       count(*) AS vuelos,
       round(100.0 * count(*) FILTER (WHERE f.bloque_salida_id IS NULL)   / NULLIF(count(*),0), 3) AS pct_nulo_bloque_salida,
       round(100.0 * count(*) FILTER (WHERE f.hora_salida_prog IS NULL)   / NULLIF(count(*),0), 3) AS pct_nulo_hora_salida_prog,
       round(100.0 * count(*) FILTER (WHERE f.hora_salida_real IS NULL)   / NULLIF(count(*),0), 3) AS pct_nulo_hora_salida_real,
       round(100.0 * count(*) FILTER (WHERE f.retraso_salida IS NULL)     / NULLIF(count(*),0), 3) AS pct_nulo_retraso_salida,
       round(100.0 * count(*) FILTER (WHERE f.retraso_llegada IS NULL)    / NULLIF(count(*),0), 3) AS pct_nulo_retraso_llegada,
       round(100.0 * count(*) FILTER (WHERE f.distancia IS NULL)          / NULLIF(count(*),0), 3) AS pct_nulo_distancia,
       round(100.0 * count(*) FILTER (WHERE f.tiempo_programado IS NULL)  / NULLIF(count(*),0), 3) AS pct_nulo_tiempo_programado,
       round(100.0 * count(*) FILTER (WHERE f.tiempo_real IS NULL)        / NULLIF(count(*),0), 3) AS pct_nulo_tiempo_real,
       round(100.0 * count(*) FILTER (WHERE f.matricula IS NULL)           / NULLIF(count(*),0), 3) AS pct_nulo_matricula,
       round(100.0 * count(*) FILTER (WHERE f.retraso_clima IS NULL)      / NULLIF(count(*),0), 3) AS pct_nulo_causa_clima
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY 1
ORDER BY 1;


-- 1.5 Nulos INESPERADOS (los que sí son un problema de calidad)
-- Pregunta: ¿hay datos faltantes donde BTS debería reportarlos?
-- Universo por columna (ver alias): operados, cancelados o vuelos con retraso de llegada >= 15 min.
SELECT f.fecha_id / 10000 AS anio,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado AND f.retraso_llegada IS NULL)  AS operados_sin_retraso_llegada,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado AND f.tiempo_real IS NULL)      AS operados_sin_tiempo_real,
       count(*) FILTER (WHERE NOT f.cancelado AND f.hora_salida_real IS NULL)                    AS no_cancelados_sin_hora_salida_real,
       count(*) FILTER (WHERE f.cancelado AND f.cancelacion_id IS NULL)                          AS cancelados_sin_causa,
       count(*) FILTER (WHERE NOT f.cancelado AND f.cancelacion_id IS NOT NULL)                  AS no_cancelados_con_causa_cancelacion,
       count(*) FILTER (WHERE f.retraso_llegada >= 15 AND NOT f.cancelado AND NOT f.desviado
                          AND f.retraso_aerolinea IS NULL AND f.retraso_clima IS NULL
                          AND f.retraso_nas IS NULL AND f.retraso_seguridad IS NULL
                          AND f.retraso_avion_tardio IS NULL)                                    AS retrasados_15_sin_ninguna_causa
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY 1
ORDER BY 1;


-- 1.6 Valores inválidos o extremos, por año
-- Pregunta: ¿cuántos registros tienen valores imposibles o atípicos?
-- Umbrales: retraso |x| > 1440 min (24 h) = extremo; distancia <= 0; tiempos programados <= 0.
-- Universo: todos los vuelos del año (los retrasos extremos, solo operados).
SELECT f.fecha_id / 10000 AS anio,
       count(*) FILTER (WHERE f.distancia <= 0)                                              AS distancia_menor_igual_0,
       count(*) FILTER (WHERE f.tiempo_programado <= 0)                                      AS tiempo_programado_menor_igual_0,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado AND f.tiempo_real <= 0)     AS tiempo_real_menor_igual_0,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado AND abs(f.retraso_llegada) > 1440) AS retraso_llegada_extremo_24h,
       count(*) FILTER (WHERE NOT f.cancelado AND abs(f.retraso_salida) > 1440)              AS retraso_salida_extremo_24h,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado AND f.retraso_llegada < -120) AS adelanto_mayor_2h,
       count(*) FILTER (WHERE f.origin_airport_id = f.destination_airport_id)                AS origen_igual_destino,
       count(*) FILTER (WHERE f.hora_salida_prog NOT BETWEEN 0 AND 2400
                           OR f.hora_llegada_prog NOT BETWEEN 0 AND 2400)                    AS hora_programada_fuera_de_rango
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY 1
ORDER BY 1;


-- 1.7 Distribución de retraso de llegada: percentiles (detección de atípicos)
-- Pregunta: ¿cómo se ve la cola de retrasos? Universo: operados con retraso_llegada no nulo.
-- Pesado con la base completa (percentile_cont ordena); para pruebas limitar a un año.
SELECT count(*)                                                        AS vuelos_operados,
       min(f.retraso_llegada)                                          AS minimo,
       percentile_cont(0.01) WITHIN GROUP (ORDER BY f.retraso_llegada) AS p01,
       percentile_cont(0.25) WITHIN GROUP (ORDER BY f.retraso_llegada) AS p25,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY f.retraso_llegada) AS mediana,
       percentile_cont(0.75) WITHIN GROUP (ORDER BY f.retraso_llegada) AS p75,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY f.retraso_llegada) AS p95,
       percentile_cont(0.99) WITHIN GROUP (ORDER BY f.retraso_llegada) AS p99,
       percentile_cont(0.999) WITHIN GROUP (ORDER BY f.retraso_llegada) AS p999,
       max(f.retraso_llegada)                                          AS maximo
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND NOT f.cancelado AND NOT f.desviado
  AND f.retraso_llegada IS NOT NULL;


-- 1.8 Códigos sin dimensión y dimensiones sin uso (integridad referencial)
-- Pregunta: ¿hay hechos huérfanos o dimensiones sin vuelos? Las FK deberían impedir huérfanos
--   (resultado 0); las dimensiones sin uso son informativas.
-- Universo: filas de dimensión / de hechos según la fila.
SELECT 'hechos con aerolinea sin dimension' AS revision, count(*) AS filas
FROM dw.fact_flights f LEFT JOIN dw.dim_airline a USING (airline_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20201231 AND a.airline_id IS NULL
UNION ALL
SELECT 'hechos con aeropuerto origen sin dimension', count(*)
FROM dw.fact_flights f LEFT JOIN dw.dim_airport o ON o.airport_id = f.origin_airport_id
WHERE f.fecha_id BETWEEN 20100101 AND 20201231 AND o.airport_id IS NULL
UNION ALL
SELECT 'hechos con aeropuerto destino sin dimension', count(*)
FROM dw.fact_flights f LEFT JOIN dw.dim_airport d ON d.airport_id = f.destination_airport_id
WHERE f.fecha_id BETWEEN 20100101 AND 20201231 AND d.airport_id IS NULL
UNION ALL
SELECT 'hechos con bloque horario nulo o sin dimension', count(*)
FROM dw.fact_flights f LEFT JOIN dw.dim_bloque_horario b ON b.bloque_id = f.bloque_salida_id
WHERE f.fecha_id BETWEEN 20100101 AND 20201231 AND b.bloque_id IS NULL
UNION ALL
SELECT 'aerolineas en dimension sin vuelos', count(*)
FROM dw.dim_airline a
WHERE NOT EXISTS (SELECT 1 FROM dw.fact_flights f WHERE f.airline_id = a.airline_id
                  AND f.fecha_id BETWEEN 20100101 AND 20201231)
UNION ALL
SELECT 'aeropuertos en dimension sin vuelos (origen ni destino)', count(*)
FROM dw.dim_airport p
WHERE NOT EXISTS (SELECT 1 FROM dw.fact_flights f WHERE f.origin_airport_id = p.airport_id
                  AND f.fecha_id BETWEEN 20100101 AND 20201231)
  AND NOT EXISTS (SELECT 1 FROM dw.fact_flights f WHERE f.destination_airport_id = p.airport_id
                  AND f.fecha_id BETWEEN 20100101 AND 20201231)
UNION ALL
SELECT 'aeropuertos sin coordenadas (latitud o longitud nula)  -> afecta el mapa', count(*)
FROM dw.dim_airport WHERE latitud IS NULL OR longitud IS NULL
UNION ALL
SELECT 'aeropuertos sin zona horaria', count(*)
FROM dw.dim_airport WHERE zona_horaria IS NULL;


-- 1.9 Coherencia de estado_vuelo vs. cancelado / desviado / categoria_retraso
-- Pregunta: ¿las reglas de negocio de 20_fact_flights.sql se cumplen?
-- Universo: todos los vuelos. Las filas "incoherentes" deberían ser 0.
SELECT f.estado_vuelo, f.cancelado, f.desviado,
       count(*) AS vuelos,
       count(*) FILTER (WHERE f.estado_vuelo = 'Cancelado' AND NOT f.cancelado
                           OR f.estado_vuelo <> 'Cancelado' AND f.cancelado
                           OR f.estado_vuelo = 'Desviado' AND (NOT f.desviado OR f.cancelado)
                           OR f.estado_vuelo IN ('A tiempo','Retrasado') AND (f.cancelado OR f.desviado)) AS incoherentes,
       count(*) FILTER (WHERE f.estado_vuelo = 'Retrasado' AND f.retraso_llegada < 15)       AS retrasado_con_menos_de_15,
       count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo'  AND f.retraso_llegada >= 15)      AS a_tiempo_con_15_o_mas,
       count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo'  AND f.retraso_llegada IS NULL)    AS a_tiempo_sin_retraso_llegada,
       count(*) FILTER (WHERE (f.cancelado OR f.desviado) AND f.categoria_retraso IS NOT NULL) AS no_operado_con_categoria
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;


-- 1.10 Coherencia de las causas de retraso
-- Pregunta: ¿las causas solo aparecen con retraso >= 15 min y suman ~ el retraso de llegada?
-- Universo: (a) vuelos con causa informada, (b) operados con retraso_llegada >= 15 min.
SELECT f.fecha_id / 10000 AS anio,
       count(*) FILTER (WHERE f.retraso_llegada < 15
                          AND coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0)
                            + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0) > 0) AS causas_con_retraso_menor_15,
       count(*) FILTER (WHERE f.retraso_llegada >= 15 AND NOT f.cancelado AND NOT f.desviado)            AS operados_retraso_15_o_mas,
       count(*) FILTER (WHERE f.retraso_llegada >= 15 AND NOT f.cancelado AND NOT f.desviado
                          AND abs(coalesce(f.retraso_aerolinea,0) + coalesce(f.retraso_clima,0) + coalesce(f.retraso_nas,0)
                                + coalesce(f.retraso_seguridad,0) + coalesce(f.retraso_avion_tardio,0)
                                - f.retraso_llegada) > 1)                                               AS suma_causas_distinta_de_retraso_llegada
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY 1
ORDER BY 1;


-- 1.11 Posibles duplicados (mismo vuelo registrado más de una vez)
-- Pregunta: ¿hay duplicados? Llave natural: fecha, aerolínea, número de vuelo, origen, destino, hora programada.
-- Universo: todos los vuelos. COSTOSO (agrupa 67 M de filas): correrlo por año.
-- Para elegir el año cambiar las dos fechas del WHERE.
SELECT f.fecha_id, f.airline_id, f.numero_vuelo, f.origin_airport_id,
       f.destination_airport_id, f.hora_salida_prog, count(*) AS repeticiones
FROM dw.fact_flights f
WHERE f.fecha_id BETWEEN 20190101 AND 20191231
GROUP BY 1, 2, 3, 4, 5, 6
HAVING count(*) > 1
ORDER BY repeticiones DESC
LIMIT 50;


-- 1.12 Cobertura de aerolíneas por año (¿desde/hasta cuándo opera cada código?)
-- Pregunta: ¿qué aerolíneas existen en cada año? Sirve para los avisos de comparación 2010 vs 2020
--   (Spirit desde 2015; Allegiant y Republic desde 2018; fusiones CO, FL, US, VX).
-- Universo: todos los vuelos programados de cada aerolínea-año.
SELECT a.codigo, a.nombre,
       min(f.fecha_id) AS primer_fecha_id, max(f.fecha_id) AS ultimo_fecha_id,
       count(*) AS vuelos_programados,
       count(DISTINCT f.fecha_id / 10000) AS anios_con_datos
FROM dw.fact_flights f
JOIN dw.dim_airline a USING (airline_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY a.codigo, a.nombre
ORDER BY a.codigo;
