-- =====================================================================
-- 11_dim_airline.sql
-- Aerolíneas observadas en raw.flights + nombre desde la lookup de BTS.
-- =====================================================================

INSERT INTO dw.dim_airline (codigo, nombre, dot_id)
SELECT f.reporting_airline,
       a.description,
       max(f.dot_id_reporting_airline)
FROM raw.flights f
LEFT JOIN ref.airlines a ON a.code = f.reporting_airline
GROUP BY f.reporting_airline, a.description
ON CONFLICT (codigo) DO UPDATE SET
    nombre = COALESCE(EXCLUDED.nombre, dw.dim_airline.nombre),
    dot_id = COALESCE(EXCLUDED.dot_id, dw.dim_airline.dot_id);
