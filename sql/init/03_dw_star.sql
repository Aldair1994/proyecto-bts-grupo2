-- =====================================================================
-- 03_dw_star.sql
-- Modelo dimensional en estrella (sección 3.4 del enunciado).
-- Tabla de hechos: dw.fact_flights (un registro = un vuelo), particionada por año.
-- Dimensiones: dim_airline, dim_airport (rol origen y destino), dim_fecha,
--              dim_bloque_horario, dim_cancelacion.
-- Se llenan con sql/build/*.sql (ejecutados por etl/04_build_star.py).
-- =====================================================================

-- ---------------------------------------------------------------------
-- Dimensiones
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dw.dim_airline (
    airline_id      serial       PRIMARY KEY,
    codigo          varchar(3)   NOT NULL UNIQUE,   -- Reporting_Airline (código único de BTS)
    nombre          text,                            -- nombre común (catálogo) o lookup L_UNIQUE_CARRIERS
    dot_id          integer,
    tipo_aerolinea  varchar(12),                     -- Tradicional, Bajo costo, Regional (docs/catalogo_aerolineas.csv)
    anio_inicio     smallint,                        -- primer año con datos en 2010-2020
    anio_fin        smallint                         -- último año con datos en 2010-2020
);

CREATE TABLE IF NOT EXISTS dw.dim_airport (
    airport_id      integer      PRIMARY KEY,        -- AirportID de BTS (estable en el tiempo)
    codigo_iata     varchar(5),                      -- código más reciente observado
    nombre          text,
    ciudad          text,
    estado          text,
    latitud         double precision,
    longitud        double precision,
    zona_horaria    text
);

CREATE TABLE IF NOT EXISTS dw.dim_fecha (
    fecha_id        integer      PRIMARY KEY,        -- formato AAAAMMDD
    fecha           date         NOT NULL UNIQUE,
    anio            smallint     NOT NULL,
    trimestre       smallint     NOT NULL,
    mes             smallint     NOT NULL,
    nombre_mes      varchar(12)  NOT NULL,
    semana_iso      smallint     NOT NULL,
    dia_mes         smallint     NOT NULL,
    dia_semana      smallint     NOT NULL,           -- 1 = lunes ... 7 = domingo
    nombre_dia      varchar(10)  NOT NULL,
    es_fin_semana   boolean      NOT NULL,
    es_feriado      boolean      NOT NULL,
    nombre_feriado  text,
    temporada       varchar(10)  NOT NULL,           -- invierno, primavera, verano, otoño (hemisferio norte)
    periodo_covid   boolean      NOT NULL            -- true desde 2020-03-01 (supuesto documentado)
);

CREATE TABLE IF NOT EXISTS dw.dim_bloque_horario (
    bloque_id       smallint     PRIMARY KEY,        -- hora de inicio 0..23
    etiqueta        varchar(9)   NOT NULL,           -- '0600-0659'
    franja          varchar(12)  NOT NULL            -- Madrugada, Mañana, Tarde, Noche
);

CREATE TABLE IF NOT EXISTS dw.dim_cancelacion (
    cancelacion_id  char(1)      PRIMARY KEY,
    descripcion     text         NOT NULL
);

-- ---------------------------------------------------------------------
-- Tabla de hechos
-- ---------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS dw.fact_flights_seq;

CREATE TABLE IF NOT EXISTS dw.fact_flights (
    flight_id               bigint      NOT NULL DEFAULT nextval('dw.fact_flights_seq'),
    fecha_id                integer     NOT NULL REFERENCES dw.dim_fecha (fecha_id),
    airline_id              integer     NOT NULL REFERENCES dw.dim_airline (airline_id),
    origin_airport_id       integer     NOT NULL REFERENCES dw.dim_airport (airport_id),
    destination_airport_id  integer     NOT NULL REFERENCES dw.dim_airport (airport_id),
    bloque_salida_id        smallint             REFERENCES dw.dim_bloque_horario (bloque_id),
    cancelacion_id          char(1)              REFERENCES dw.dim_cancelacion (cancelacion_id),

    -- Atributos degenerados del vuelo
    numero_vuelo            integer,
    matricula               varchar(10),

    -- Horarios programado vs. real (hhmm, hora local)
    hora_salida_prog        smallint,
    hora_salida_real        smallint,
    hora_llegada_prog       smallint,
    hora_llegada_real       smallint,

    -- Medidas de desempeño (minutos)
    retraso_salida          real,
    retraso_llegada         real,
    retraso_total           real,       -- minutos de retraso positivo en llegada (ver docs)
    categoria_retraso       varchar(12),
    retraso_salida_15       boolean,
    retraso_llegada_15      boolean,
    taxi_out                real,
    taxi_in                 real,

    -- Estado del vuelo
    cancelado               boolean     NOT NULL,
    desviado                boolean     NOT NULL,
    estado_vuelo            varchar(10) NOT NULL,   -- A tiempo, Retrasado, Cancelado, Desviado

    -- Resumen del vuelo
    distancia               real,
    tiempo_programado       real,
    tiempo_real             real,
    tiempo_aire             real,

    -- Causas del retraso (minutos)
    retraso_aerolinea       real,
    retraso_clima           real,
    retraso_nas             real,
    retraso_seguridad       real,
    retraso_avion_tardio    real,

    -- Regreso a puerta en origen
    tiempo_extra_puerta     real,

    PRIMARY KEY (flight_id, fecha_id)
) PARTITION BY RANGE (fecha_id);

DO $$
DECLARE
    y int;
BEGIN
    FOR y IN 2010..2020 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS dw.fact_flights_%s PARTITION OF dw.fact_flights
                 FOR VALUES FROM (%s) TO (%s)',
            y, y * 10000 + 101, (y + 1) * 10000 + 101);
    END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS ix_fact_airline ON dw.fact_flights (airline_id);
CREATE INDEX IF NOT EXISTS ix_fact_origin  ON dw.fact_flights (origin_airport_id);
CREATE INDEX IF NOT EXISTS ix_fact_dest    ON dw.fact_flights (destination_airport_id);
CREATE INDEX IF NOT EXISTS ix_fact_fecha   ON dw.fact_flights (fecha_id);

-- ---------------------------------------------------------------------
-- Dimensiones pequeñas y fijas: se llenan aquí mismo
-- ---------------------------------------------------------------------
INSERT INTO dw.dim_cancelacion (cancelacion_id, descripcion) VALUES
    ('A', 'Aerolínea'),
    ('B', 'Clima'),
    ('C', 'Sistema Nacional de Aviación (NAS)'),
    ('D', 'Seguridad')
ON CONFLICT DO NOTHING;

INSERT INTO dw.dim_bloque_horario (bloque_id, etiqueta, franja)
SELECT h,
       lpad(h::text, 2, '0') || '00-' || lpad(h::text, 2, '0') || '59',
       CASE WHEN h < 6  THEN 'Madrugada'
            WHEN h < 12 THEN 'Mañana'
            WHEN h < 18 THEN 'Tarde'
            ELSE 'Noche' END
FROM generate_series(0, 23) AS h
ON CONFLICT DO NOTHING;
