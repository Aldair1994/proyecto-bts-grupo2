-- =====================================================================
-- sql/quality/checks.sql
-- Controles de calidad (reglas R01 a R13) sobre raw.flights. Los valores "esperado"
-- salen de la corrida de calidad sobre los 132 zip de BTS (docs/calidad/).
-- Uso: docker compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -f /app/sql/quality/checks.sql
--      (o pegarlo en DBeaver). Es solo lectura: no modifica nada.
-- NOTA: escrito contra el esquema de sql/init/01_raw_flights.sql; no se ha corrido todavia
-- contra una base cargada.
-- =====================================================================

-- 1. Conciliacion de filas por anio (R12) en tres puntos: lo que traen los zip (esperado),
--    lo que registro la carga (raw.load_log) y lo que hay en raw.flights.
--    meses_log debe ser 12 y las tres cifras de filas deben coincidir.
WITH esperado(anio, filas) AS (VALUES
    (2010, 6450117),
    (2011, 6085281),
    (2012, 6096762),
    (2013, 6369482),
    (2014, 5819811),
    (2015, 5819079),
    (2016, 5617658),
    (2017, 5674621),
    (2018, 7206195),
    (2019, 7422037),
    (2020, 4688354)
),
bitacora AS (
    SELECT year AS anio, count(*) AS meses, sum(rows_loaded) AS filas
    FROM raw.load_log GROUP BY year
),
cargado AS (
    SELECT extract(year FROM flight_date)::int AS anio, count(*) AS filas
    FROM raw.flights GROUP BY 1
)
SELECT e.anio,
       e.filas               AS esperado,
       coalesce(b.meses, 0)  AS meses_log,
       coalesce(b.filas, 0)  AS filas_log,
       coalesce(c.filas, 0)  AS filas_raw,
       CASE WHEN b.meses = 12 AND b.filas = e.filas AND c.filas = e.filas
            THEN 'OK' ELSE 'REVISAR' END AS estado
FROM esperado e
LEFT JOIN bitacora b USING (anio)
LEFT JOIN cargado  c USING (anio)
ORDER BY e.anio;
-- Total esperado: 67,249,397

-- 2. Reglas de calidad: lo encontrado contra lo esperado segun la fuente
WITH normal AS (
    SELECT * FROM raw.flights WHERE NOT cancelled AND NOT diverted
),
resultado AS (
    SELECT 'R01 duplicados de la clave natural' AS regla,
           (SELECT count(*) FROM raw.flights)
         - (SELECT count(*) FROM (SELECT DISTINCT flight_date, reporting_airline, flight_number, origin, dest, crs_dep_time
                                  FROM raw.flights) d) AS encontrado,
           4::bigint AS esperado
    UNION ALL SELECT 'R04 horas fuera de rango (0000-2400, minutos 00-59)',
           (SELECT sum((CASE WHEN h < 0 OR h > 2400 OR h % 100 > 59 THEN 1 ELSE 0 END))
            FROM raw.flights, LATERAL (VALUES (crs_dep_time), (dep_time), (crs_arr_time), (arr_time)) v(h)), 0
    UNION ALL SELECT 'R05 distancia no positiva',
           (SELECT count(*) FROM raw.flights WHERE distance <= 0), 0
    UNION ALL SELECT 'R06 cancelados con hora de salida o llegada (se conservan, solo se marcan)',
           (SELECT count(*) FROM raw.flights WHERE cancelled AND (dep_time IS NOT NULL OR arr_time IS NOT NULL)), 39234
    UNION ALL SELECT 'R06 cancelados sin codigo de cancelacion',
           (SELECT count(*) FROM raw.flights WHERE cancelled AND cancellation_code IS NULL), 0
    UNION ALL SELECT 'R07 vuelos normales sin retraso de salida o llegada',
           (SELECT count(*) FROM normal WHERE arr_delay IS NULL OR dep_delay IS NULL), 969
    UNION ALL SELECT 'R08 arr_del15 incoherente con arr_delay',
           (SELECT count(*) FROM normal
            WHERE coalesce((arr_delay >= 15)::int, 0) <> coalesce(arr_del15::int, -1)), 352
    UNION ALL SELECT 'R09 causas que no suman el retraso de llegada (tolerancia 1 min)',
           (SELECT count(*) FROM normal
            WHERE arr_delay >= 15
              AND abs(coalesce(carrier_delay,0) + coalesce(weather_delay,0) + coalesce(nas_delay,0)
                      + coalesce(security_delay,0) + coalesce(late_aircraft_delay,0) - arr_delay) > 1), 2
    UNION ALL SELECT 'R10 aerolineas sin descripcion en ref.airlines',
           (SELECT count(*) FROM raw.flights f WHERE NOT EXISTS (SELECT 1 FROM ref.airlines a WHERE a.code = f.reporting_airline)), 0
    UNION ALL SELECT 'R10 aeropuertos de origen o destino sin descripcion en ref.airports',
           (SELECT count(*) FROM raw.flights f
            WHERE NOT EXISTS (SELECT 1 FROM ref.airports a WHERE a.airport_id = f.origin_airport_id)
               OR NOT EXISTS (SELECT 1 FROM ref.airports a WHERE a.airport_id = f.dest_airport_id)), 0
    UNION ALL SELECT 'R11 retrasos atipicos (menos de -120 o mas de 1440 min; se marcan, no se borran)',
           (SELECT count(*) FROM raw.flights WHERE arr_delay < -120 OR arr_delay > 1440), 635
    UNION ALL SELECT 'Cancelados (control de totales)',
           (SELECT count(*) FROM raw.flights WHERE cancelled), 1302027
    UNION ALL SELECT 'Desviados (control de totales)',
           (SELECT count(*) FROM raw.flights WHERE diverted), 156836
)
SELECT regla, encontrado, esperado,
       CASE WHEN encontrado = esperado THEN 'OK' ELSE 'REVISAR' END AS estado
FROM resultado;

-- 3. Modelo estrella: la tabla de hechos debe tener las mismas filas que raw
SELECT (SELECT count(*) FROM raw.flights)  AS filas_raw,
       (SELECT count(*) FROM dw.fact_flights) AS filas_fact,
       (SELECT count(*) FROM raw.flights) - (SELECT count(*) FROM dw.fact_flights) AS diferencia;
