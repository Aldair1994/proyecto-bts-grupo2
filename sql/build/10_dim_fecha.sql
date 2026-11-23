-- =====================================================================
-- 10_dim_fecha.sql
-- Calendario completo 2010-01-01 .. 2020-12-31, con feriados de ref.us_holidays.
-- Idempotente: se puede volver a correr sin duplicar.
-- =====================================================================

INSERT INTO dw.dim_fecha (
    fecha_id, fecha, anio, trimestre, mes, nombre_mes, semana_iso, dia_mes,
    dia_semana, nombre_dia, es_fin_semana, es_feriado, nombre_feriado,
    temporada, periodo_covid)
SELECT
    to_char(d, 'YYYYMMDD')::int,
    d::date,
    extract(year    FROM d)::smallint,
    extract(quarter FROM d)::smallint,
    extract(month   FROM d)::smallint,
    (ARRAY['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio',
           'Agosto','Septiembre','Octubre','Noviembre','Diciembre'])[extract(month FROM d)],
    extract(week    FROM d)::smallint,
    extract(day     FROM d)::smallint,
    extract(isodow  FROM d)::smallint,
    (ARRAY['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'])[extract(isodow FROM d)],
    extract(isodow FROM d) IN (6, 7),
    h.holiday_date IS NOT NULL,
    h.name,
    CASE WHEN extract(month FROM d) IN (12, 1, 2) THEN 'Invierno'
         WHEN extract(month FROM d) IN (3, 4, 5)  THEN 'Primavera'
         WHEN extract(month FROM d) IN (6, 7, 8)  THEN 'Verano'
         ELSE 'Otoño' END,
    d >= DATE '2020-03-01'
FROM generate_series(DATE '2010-01-01', DATE '2020-12-31', INTERVAL '1 day') AS d
LEFT JOIN ref.us_holidays h ON h.holiday_date = d::date
ON CONFLICT (fecha_id) DO UPDATE SET
    es_feriado     = EXCLUDED.es_feriado,
    nombre_feriado = EXCLUDED.nombre_feriado;
