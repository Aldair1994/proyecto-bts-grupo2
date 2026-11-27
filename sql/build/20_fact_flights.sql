-- =====================================================================
-- 20_fact_flights.sql
-- Carga la tabla de hechos para UN año. etl/04_build_star.py lo ejecuta año por año
-- pasando el parámetro %(anio)s. Primero vacía la partición del año, así que se puede
-- volver a correr sin duplicar.
--
-- Reglas de negocio (documentar en el informe de Data Preparation):
--   * estado_vuelo: Cancelado > Desviado > Sin dato > Retrasado (arr_del15) > A tiempo.
--     "A tiempo" sigue el criterio oficial de BTS: llegada con menos de 15 min de retraso.
--     "Sin dato": vuelo operado sin arr_del15 registrado (352 vuelos en 2010-2020, regla R08 de calidad);
--     no se cuenta como a tiempo ni como retrasado.
--   * retraso_total: minutos de retraso positivo en la llegada (el retraso de llegada
--     ya acumula el de salida, por eso no se suman ambos).
--   * categoria_retraso: Sin retraso (<=0), Leve (1-14), Moderado (15-59),
--     Severo (60-179), Extremo (>=180). NULL si el vuelo se canceló o se desvió.
--     Se llama 'Sin retraso' (y no 'A tiempo') para no confundirla con estado_vuelo.
--   * bloque_salida_id: hora programada de salida (crs_dep_time / 100); 2400 -> 0.
-- =====================================================================

DELETE FROM dw.fact_flights
WHERE fecha_id >= %(anio)s * 10000 + 101
  AND fecha_id <  (%(anio)s + 1) * 10000 + 101;

INSERT INTO dw.fact_flights (
    fecha_id, airline_id, origin_airport_id, destination_airport_id,
    bloque_salida_id, cancelacion_id, numero_vuelo, matricula,
    hora_salida_prog, hora_salida_real, hora_llegada_prog, hora_llegada_real,
    retraso_salida, retraso_llegada, retraso_total, categoria_retraso,
    retraso_salida_15, retraso_llegada_15, taxi_out, taxi_in,
    cancelado, desviado, estado_vuelo,
    distancia, tiempo_programado, tiempo_real, tiempo_aire,
    retraso_aerolinea, retraso_clima, retraso_nas, retraso_seguridad, retraso_avion_tardio,
    tiempo_extra_puerta)
SELECT
    to_char(f.flight_date, 'YYYYMMDD')::int,
    a.airline_id,
    f.origin_airport_id,
    f.dest_airport_id,
    mod(f.crs_dep_time / 100, 24),
    f.cancellation_code,
    f.flight_number,
    f.tail_number,
    f.crs_dep_time, f.dep_time, f.crs_arr_time, f.arr_time,
    f.dep_delay,
    f.arr_delay,
    CASE WHEN f.cancelled OR f.diverted THEN NULL ELSE greatest(f.arr_delay, 0) END,
    CASE WHEN f.cancelled OR f.diverted OR f.arr_delay IS NULL THEN NULL
         WHEN f.arr_delay <= 0   THEN 'Sin retraso'
         WHEN f.arr_delay < 15   THEN 'Leve'
         WHEN f.arr_delay < 60   THEN 'Moderado'
         WHEN f.arr_delay < 180  THEN 'Severo'
         ELSE 'Extremo' END,
    f.dep_del15,
    f.arr_del15,
    f.taxi_out, f.taxi_in,
    f.cancelled,
    f.diverted,
    CASE WHEN f.cancelled THEN 'Cancelado'
         WHEN f.diverted  THEN 'Desviado'
         WHEN f.arr_del15 IS NULL THEN 'Sin dato'
         WHEN f.arr_del15 THEN 'Retrasado'
         ELSE 'A tiempo' END,
    f.distance, f.crs_elapsed_time, f.actual_elapsed_time, f.air_time,
    f.carrier_delay, f.weather_delay, f.nas_delay, f.security_delay, f.late_aircraft_delay,
    f.total_add_g_time
FROM raw.flights f
JOIN dw.dim_airline a ON a.codigo = f.reporting_airline
WHERE f.flight_date >= make_date(%(anio)s, 1, 1)
  AND f.flight_date <  make_date(%(anio)s + 1, 1, 1);
