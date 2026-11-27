-- =====================================================================
-- 11_dim_airline.sql
-- Aerolíneas observadas en raw.flights.
-- Nombre: se usa nombre_comun del catálogo del Data Administrator, porque la lookup de
-- BTS asigna el nombre del dueño ACTUAL del código (p. ej. XE aparece como "JSX" y
-- EV como "aha!"). Si una aerolínea no está en el catálogo, se usa la lookup.
-- =====================================================================

-- Migración para bases creadas antes de integrar el catálogo (no hace nada si ya existe)
CREATE TABLE IF NOT EXISTS ref.airline_catalog (
    reporting_airline     varchar(3) PRIMARY KEY,
    nombre_comun          text       NOT NULL,
    tipo_aerolinea        varchar(12) NOT NULL,
    anio_inicio_en_datos  smallint,
    anio_fin_en_datos     smallint,
    vuelos_2010_2020      bigint,
    nota                  text
);
ALTER TABLE dw.dim_airline ADD COLUMN IF NOT EXISTS tipo_aerolinea varchar(12);
ALTER TABLE dw.dim_airline ADD COLUMN IF NOT EXISTS anio_inicio    smallint;
ALTER TABLE dw.dim_airline ADD COLUMN IF NOT EXISTS anio_fin       smallint;

WITH observadas AS (
    SELECT reporting_airline,
           max(dot_id_reporting_airline) AS dot_id,
           min(year) AS anio_inicio,
           max(year) AS anio_fin
    FROM raw.flights
    GROUP BY reporting_airline
)
INSERT INTO dw.dim_airline (codigo, nombre, dot_id, tipo_aerolinea, anio_inicio, anio_fin)
SELECT o.reporting_airline,
       COALESCE(c.nombre_comun, a.description),
       o.dot_id,
       c.tipo_aerolinea,
       o.anio_inicio,
       o.anio_fin
FROM observadas o
LEFT JOIN ref.airline_catalog c ON c.reporting_airline = o.reporting_airline
LEFT JOIN ref.airlines        a ON a.code = o.reporting_airline
ON CONFLICT (codigo) DO UPDATE SET
    nombre         = COALESCE(EXCLUDED.nombre, dw.dim_airline.nombre),
    dot_id         = COALESCE(EXCLUDED.dot_id, dw.dim_airline.dot_id),
    tipo_aerolinea = EXCLUDED.tipo_aerolinea,
    anio_inicio    = EXCLUDED.anio_inicio,
    anio_fin       = EXCLUDED.anio_fin;
