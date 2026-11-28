-- =====================================================================
-- modelos/muestra.sql  --  Muestra de vuelos para correlaciones (2.11) y modelos (preguntas 24 y 25)
-- Solo SELECT. La ejecuta modelos/extraer_muestra.py UNA VEZ POR AÑO, reemplazando
-- {desde}, {hasta} y {por_mil} (enteros validados en Python).
--
-- Muestreo determinista: cubeta = hash(flight_id) módulo 1000 (0..999). Se guardan los
-- vuelos con cubeta < {por_mil}. Como la cubeta no depende del año ni del resultado del
-- vuelo, la muestra es aleatoria simple dentro de cada año y se repite igual cada vez.
-- Cubeta < 50 es un subconjunto de cubeta < 150: el script de entrenamiento usa cubeta < 50
-- en todos los años de entrenamiento (misma tasa) y cubeta < 150 en validación y prueba.
--
-- Columnas:
--   * Permitidas en los modelos (se conocen antes del despegue, docs/analisis/03_plan_modelos.md §3).
--   * Objetivos: retraso_llegada_15 (pregunta 24), cancelado (pregunta 25); desviado define el universo.
--   * SOLO PARA CORRELACIONES (prohibidas en los modelos por fuga, §4): retraso_salida,
--     retraso_llegada, taxi_out, taxi_in. modelos/comun.py impide usarlas como variables.
-- =====================================================================
SELECT f.flight_id,
       mod(hashint8(f.flight_id)::bigint + 2147483648, 1000)::smallint AS cubeta,
       f.fecha_id,
       d.anio, d.mes, d.dia_semana, d.es_feriado, d.es_fin_semana, d.periodo_covid,
       f.bloque_salida_id                 AS hora_salida,
       f.hora_llegada_prog,
       a.codigo                           AS aerolinea,
       a.tipo_aerolinea,
       o.codigo_iata                      AS origen,
       o.estado                           AS estado_origen,
       de.codigo_iata                     AS destino,
       de.estado                          AS estado_destino,
       f.distancia,
       f.tiempo_programado,
       f.cancelado,
       f.desviado,
       f.retraso_llegada_15,
       f.retraso_salida,
       f.retraso_llegada,
       f.taxi_out,
       f.taxi_in
FROM dw.fact_flights f
JOIN dw.dim_fecha   d  USING (fecha_id)
JOIN dw.dim_airline a  USING (airline_id)
JOIN dw.dim_airport o  ON o.airport_id  = f.origin_airport_id
JOIN dw.dim_airport de ON de.airport_id = f.destination_airport_id
WHERE f.fecha_id BETWEEN {desde} AND {hasta}
  AND mod(hashint8(f.flight_id)::bigint + 2147483648, 1000) < {por_mil}
