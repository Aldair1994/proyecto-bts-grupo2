-- =====================================================================
-- 00_schemas.sql
-- Capas de la base:
--   raw : datos tal como vienen de BTS (solo columnas seleccionadas y tipadas)
--   ref : tablas de referencia externas (lookups de BTS, feriados)
--   dw  : modelo estrella (dimensiones + tabla de hechos) para análisis y dashboard
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS ref;
CREATE SCHEMA IF NOT EXISTS dw;

COMMENT ON SCHEMA raw IS 'Datos On-Time Performance de BTS, sin transformar salvo tipado y selección de columnas';
COMMENT ON SCHEMA ref IS 'Tablas de referencia: lookups de BTS (Get Lookup Table) y feriados de EE. UU.';
COMMENT ON SCHEMA dw  IS 'Modelo dimensional en estrella para análisis y dashboard';
