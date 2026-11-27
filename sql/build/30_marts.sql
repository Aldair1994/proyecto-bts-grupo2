-- =====================================================================
-- 30_marts.sql
-- Capa de consumo para el dashboard (esquema mart): vistas materializadas
-- resumidas a partir de dw.fact_flights. Pasan de 67 millones de filas a unas
-- pocas miles, así que Power BI las puede IMPORTAR y responde al instante.
--
-- Reglas (iguales a docs/analisis/01_preguntas_kpis.md):
--   * programado = todos los vuelos; operado = NOT cancelado AND NOT desviado
--   * las vistas guardan CONTEOS y SUMAS, no porcentajes ni promedios: así se
--     pueden sumar por cualquier filtro sin error. Los porcentajes se calculan en
--     el dashboard dividiendo sumas (medidas DAX en docs/marts.md).
--     NUNCA promediar un porcentaje ya calculado.
--   * periodo_covid = mes >= 2020-03 (mismo supuesto que dw.dim_fecha)
--
-- Se ejecuta con etl/p6_build_marts.py (paso "marts" del pipeline). Idempotente:
-- borra y recrea cada vista.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS mart;
COMMENT ON SCHEMA mart IS 'Vistas materializadas resumidas para el dashboard (se recrean con el paso marts)';

-- ---------------------------------------------------------------------
-- 1. Puntualidad, cancelaciones y causas por MES y AEROLÍNEA
--    Responde: ranking de aerolíneas, evolución por año, tipo de aerolínea,
--    causas de retraso y de cancelación, COVID.
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mart.puntualidad_mensual_aerolinea;
CREATE MATERIALIZED VIEW mart.puntualidad_mensual_aerolinea AS
SELECT
    d.anio * 100 + d.mes                                          AS mes_id,
    make_date(d.anio, d.mes, 1)                                   AS fecha_mes,
    d.anio, d.mes, d.nombre_mes, d.trimestre, d.temporada,
    make_date(d.anio, d.mes, 1) >= DATE '2020-03-01'              AS periodo_covid,
    a.airline_id,
    a.codigo                                                      AS aerolinea_codigo,
    a.nombre                                                      AS aerolinea_nombre,
    a.tipo_aerolinea,
    -- Volumen y estado
    count(*)                                                      AS vuelos_programados,
    count(*) FILTER (WHERE f.cancelado)                           AS vuelos_cancelados,
    count(*) FILTER (WHERE f.desviado)                            AS vuelos_desviados,
    count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado)    AS vuelos_operados,
    count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')           AS vuelos_a_tiempo,
    count(*) FILTER (WHERE f.estado_vuelo = 'Retrasado')          AS vuelos_retrasados,
    count(*) FILTER (WHERE f.estado_vuelo = 'Sin dato')           AS vuelos_sin_dato,
    -- Cancelaciones por causa
    count(*) FILTER (WHERE f.cancelacion_id = 'A')                AS cancel_aerolinea,
    count(*) FILTER (WHERE f.cancelacion_id = 'B')                AS cancel_clima,
    count(*) FILTER (WHERE f.cancelacion_id = 'C')                AS cancel_nas,
    count(*) FILTER (WHERE f.cancelacion_id = 'D')                AS cancel_seguridad,
    -- Gravedad del retraso de llegada (vuelos operados con dato)
    count(*) FILTER (WHERE f.categoria_retraso IN ('Sin retraso', 'A tiempo')) AS cat_sin_retraso,
    count(*) FILTER (WHERE f.categoria_retraso = 'Leve')          AS cat_leve,
    count(*) FILTER (WHERE f.categoria_retraso = 'Moderado')      AS cat_moderado,
    count(*) FILTER (WHERE f.categoria_retraso = 'Severo')        AS cat_severo,
    count(*) FILTER (WHERE f.categoria_retraso = 'Extremo')       AS cat_extremo,
    -- Minutos (sumas + conteos para promediar correctamente)
    sum(f.retraso_llegada) FILTER (WHERE NOT f.cancelado AND NOT f.desviado)   AS suma_retraso_llegada_min,
    count(f.retraso_llegada) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS n_retraso_llegada,
    sum(f.retraso_salida) FILTER (WHERE NOT f.cancelado)                       AS suma_retraso_salida_min,
    count(f.retraso_salida) FILTER (WHERE NOT f.cancelado)                     AS n_retraso_salida,
    -- Causas del retraso (solo existen cuando la llegada se retrasó 15 min o más)
    count(*) FILTER (WHERE f.retraso_llegada_15 AND NOT f.cancelado AND NOT f.desviado) AS vuelos_con_causa,
    coalesce(sum(f.retraso_aerolinea), 0)                         AS min_causa_aerolinea,
    coalesce(sum(f.retraso_clima), 0)                             AS min_causa_clima,
    coalesce(sum(f.retraso_nas), 0)                               AS min_causa_nas,
    coalesce(sum(f.retraso_seguridad), 0)                         AS min_causa_seguridad,
    coalesce(sum(f.retraso_avion_tardio), 0)                      AS min_causa_avion_tardio,
    -- Operación
    sum(f.taxi_out)                                               AS suma_taxi_out_min,
    count(f.taxi_out)                                             AS n_taxi_out,
    sum(f.tiempo_programado) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS suma_tiempo_programado_min,
    sum(f.tiempo_real)       FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS suma_tiempo_real_min,
    count(f.tiempo_real)     FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS n_tiempo_real,
    sum(f.distancia)                                              AS distancia_total_millas
FROM dw.fact_flights f
JOIN dw.dim_fecha   d USING (fecha_id)
JOIN dw.dim_airline a USING (airline_id)
GROUP BY d.anio, d.mes, d.nombre_mes, d.trimestre, d.temporada,
         a.airline_id, a.codigo, a.nombre, a.tipo_aerolinea;

-- ---------------------------------------------------------------------
-- 2. Desempeño por MES y AEROPUERTO, en dos roles:
--    'Origen'  -> salidas (retraso de salida, taxi-out)
--    'Destino' -> llegadas (puntualidad de llegada, taxi-in)
--    Responde: aeropuertos con más retrasos, congestión, mapa por estado.
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mart.aeropuerto_mensual;
CREATE MATERIALIZED VIEW mart.aeropuerto_mensual AS
WITH base AS (
    SELECT f.fecha_id, 'Origen'::varchar(7) AS rol, f.origin_airport_id AS airport_id,
           f.cancelado, f.desviado, f.estado_vuelo,
           f.retraso_salida_15 AS retrasado_15, f.retraso_salida AS retraso_min,
           f.taxi_out AS taxi_min, f.retraso_clima, f.retraso_nas
    FROM dw.fact_flights f
    UNION ALL
    SELECT f.fecha_id, 'Destino', f.destination_airport_id,
           f.cancelado, f.desviado, f.estado_vuelo,
           f.retraso_llegada_15, f.retraso_llegada,
           f.taxi_in, f.retraso_clima, f.retraso_nas
    FROM dw.fact_flights f
)
SELECT
    d.anio * 100 + d.mes                                          AS mes_id,
    make_date(d.anio, d.mes, 1)                                   AS fecha_mes,
    d.anio, d.mes, d.temporada,
    make_date(d.anio, d.mes, 1) >= DATE '2020-03-01'              AS periodo_covid,
    b.rol,
    ap.airport_id, ap.codigo_iata, ap.nombre AS aeropuerto_nombre,
    ap.ciudad, ap.estado, ap.latitud, ap.longitud,
    count(*)                                                      AS vuelos_programados,
    count(*) FILTER (WHERE b.cancelado)                           AS vuelos_cancelados,
    count(*) FILTER (WHERE b.desviado)                            AS vuelos_desviados,
    count(*) FILTER (WHERE NOT b.cancelado AND NOT b.desviado)    AS vuelos_operados,
    count(*) FILTER (WHERE b.estado_vuelo = 'A tiempo')           AS vuelos_a_tiempo,
    -- En 'Origen' es la salida con 15+ min de retraso; en 'Destino', la llegada
    count(*) FILTER (WHERE b.retrasado_15 AND NOT b.cancelado AND NOT b.desviado) AS vuelos_retrasados_15,
    count(b.retrasado_15) FILTER (WHERE NOT b.cancelado AND NOT b.desviado)       AS n_con_dato_15,
    sum(b.retraso_min) FILTER (WHERE NOT b.cancelado AND NOT b.desviado)          AS suma_retraso_min,
    count(b.retraso_min) FILTER (WHERE NOT b.cancelado AND NOT b.desviado)        AS n_retraso,
    sum(b.taxi_min)                                               AS suma_taxi_min,
    count(b.taxi_min)                                             AS n_taxi,
    coalesce(sum(b.retraso_clima), 0)                             AS min_causa_clima,
    coalesce(sum(b.retraso_nas), 0)                               AS min_causa_nas
FROM base b
JOIN dw.dim_fecha   d  USING (fecha_id)
JOIN dw.dim_airport ap ON ap.airport_id = b.airport_id
GROUP BY d.anio, d.mes, d.temporada, b.rol,
         ap.airport_id, ap.codigo_iata, ap.nombre, ap.ciudad, ap.estado, ap.latitud, ap.longitud;

-- ---------------------------------------------------------------------
-- 3. Patrón por DÍA DE LA SEMANA y HORA programada de salida (por mes)
--    Responde: qué día conviene volar, a qué hora salir, retraso acumulado en el día.
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mart.patron_dia_hora;
CREATE MATERIALIZED VIEW mart.patron_dia_hora AS
SELECT
    d.anio * 100 + d.mes                                          AS mes_id,
    d.anio, d.mes, d.temporada,
    make_date(d.anio, d.mes, 1) >= DATE '2020-03-01'              AS periodo_covid,
    d.dia_semana, d.nombre_dia, d.es_fin_semana,
    b.bloque_id, b.etiqueta AS bloque_horario, b.franja,
    count(*)                                                      AS vuelos_programados,
    count(*) FILTER (WHERE f.cancelado)                           AS vuelos_cancelados,
    count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado)    AS vuelos_operados,
    count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')           AS vuelos_a_tiempo,
    count(*) FILTER (WHERE f.retraso_salida_15 AND NOT f.cancelado) AS salidas_retrasadas_15,
    count(f.retraso_salida_15) FILTER (WHERE NOT f.cancelado)     AS n_salida_con_dato,
    sum(f.retraso_llegada) FILTER (WHERE NOT f.cancelado AND NOT f.desviado)   AS suma_retraso_llegada_min,
    count(f.retraso_llegada) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS n_retraso_llegada,
    coalesce(sum(f.retraso_avion_tardio), 0)                      AS min_causa_avion_tardio
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
LEFT JOIN dw.dim_bloque_horario b ON b.bloque_id = f.bloque_salida_id
GROUP BY d.anio, d.mes, d.temporada, d.dia_semana, d.nombre_dia, d.es_fin_semana,
         b.bloque_id, b.etiqueta, b.franja;

-- ---------------------------------------------------------------------
-- 4. Serie DIARIA
--    Responde: feriados, caída y recuperación por COVID, días con más cancelaciones
--    (cruza con docs/eventos_externos.csv: Sandy, cierre de gobierno, etc.).
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mart.serie_diaria;
CREATE MATERIALIZED VIEW mart.serie_diaria AS
SELECT
    d.fecha_id, d.fecha, d.anio, d.mes, d.nombre_dia, d.es_fin_semana,
    d.es_feriado, d.nombre_feriado, d.temporada, d.periodo_covid,
    count(*)                                                      AS vuelos_programados,
    count(*) FILTER (WHERE f.cancelado)                           AS vuelos_cancelados,
    count(*) FILTER (WHERE f.desviado)                            AS vuelos_desviados,
    count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado)    AS vuelos_operados,
    count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')           AS vuelos_a_tiempo,
    count(*) FILTER (WHERE f.cancelacion_id = 'B')                AS cancel_clima,
    sum(f.retraso_llegada) FILTER (WHERE NOT f.cancelado AND NOT f.desviado)   AS suma_retraso_llegada_min,
    count(f.retraso_llegada) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS n_retraso_llegada
FROM dw.fact_flights f
JOIN dw.dim_fecha d USING (fecha_id)
GROUP BY d.fecha_id, d.fecha, d.anio, d.mes, d.nombre_dia, d.es_fin_semana,
         d.es_feriado, d.nombre_feriado, d.temporada, d.periodo_covid;

-- ---------------------------------------------------------------------
-- 5. RUTAS por año (origen -> destino)
--    Responde: rutas más transitadas y su puntualidad, distancia vs. retraso.
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mart.rutas_anual;
CREATE MATERIALIZED VIEW mart.rutas_anual AS
SELECT
    d.anio,
    o.codigo_iata || '-' || de.codigo_iata                        AS ruta,
    o.airport_id  AS origen_airport_id,  o.codigo_iata  AS origen_iata,
    o.ciudad      AS origen_ciudad,      o.estado       AS origen_estado,
    de.airport_id AS destino_airport_id, de.codigo_iata AS destino_iata,
    de.ciudad     AS destino_ciudad,     de.estado      AS destino_estado,
    count(*)                                                      AS vuelos_programados,
    count(*) FILTER (WHERE f.cancelado)                           AS vuelos_cancelados,
    count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado)    AS vuelos_operados,
    count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')           AS vuelos_a_tiempo,
    sum(f.retraso_llegada) FILTER (WHERE NOT f.cancelado AND NOT f.desviado)   AS suma_retraso_llegada_min,
    count(f.retraso_llegada) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS n_retraso_llegada,
    avg(f.distancia)                                              AS distancia_millas
FROM dw.fact_flights f
JOIN dw.dim_fecha   d  USING (fecha_id)
JOIN dw.dim_airport o  ON o.airport_id  = f.origin_airport_id
JOIN dw.dim_airport de ON de.airport_id = f.destination_airport_id
GROUP BY d.anio, o.airport_id, o.codigo_iata, o.ciudad, o.estado,
         de.airport_id, de.codigo_iata, de.ciudad, de.estado;

CREATE INDEX IF NOT EXISTS ix_rutas_anual_anio ON mart.rutas_anual (anio);
