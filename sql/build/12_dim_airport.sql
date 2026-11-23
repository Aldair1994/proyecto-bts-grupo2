-- =====================================================================
-- 12_dim_airport.sql
-- Aeropuertos observados (como origen o destino). El código IATA de un AirportID
-- puede cambiar en el tiempo; se toma el más reciente. Nombre, ciudad y estado
-- salen de la lookup L_AIRPORT_ID ('Ciudad, ST: Nombre'); si no está, de raw.
-- =====================================================================

WITH observados AS (
    SELECT origin_airport_id AS airport_id, origin AS iata, origin_city_name AS ciudad_estado,
           origin_state AS estado, flight_date
    FROM raw.flights
    UNION ALL
    SELECT dest_airport_id, dest, dest_city_name, dest_state, flight_date
    FROM raw.flights
),
mas_reciente AS (
    SELECT DISTINCT ON (airport_id)
           airport_id, iata, ciudad_estado, estado
    FROM observados
    ORDER BY airport_id, flight_date DESC
)
INSERT INTO dw.dim_airport (airport_id, codigo_iata, nombre, ciudad, estado,
                            latitud, longitud, zona_horaria)
SELECT m.airport_id,
       m.iata,
       COALESCE(split_part(r.description, ': ', 2), m.iata),
       COALESCE(NULLIF(split_part(split_part(r.description, ': ', 1), ', ', 1), ''),
                split_part(m.ciudad_estado, ', ', 1)),
       COALESCE(m.estado, NULLIF(split_part(split_part(r.description, ': ', 1), ', ', 2), '')),
       c.latitude,
       c.longitude,
       c.timezone
FROM mas_reciente m
LEFT JOIN ref.airports       r ON r.airport_id = m.airport_id
LEFT JOIN ref.airport_coords c ON c.iata_code  = m.iata
ON CONFLICT (airport_id) DO UPDATE SET
    codigo_iata  = EXCLUDED.codigo_iata,
    nombre       = EXCLUDED.nombre,
    ciudad       = EXCLUDED.ciudad,
    estado       = EXCLUDED.estado,
    latitud      = COALESCE(EXCLUDED.latitud,  dw.dim_airport.latitud),
    longitud     = COALESCE(EXCLUDED.longitud, dw.dim_airport.longitud),
    zona_horaria = COALESCE(EXCLUDED.zona_horaria, dw.dim_airport.zona_horaria);
