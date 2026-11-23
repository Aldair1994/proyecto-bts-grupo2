-- =====================================================================
-- 01_raw_flights.sql
-- Tabla de vuelos crudos, particionada por año (RANGE sobre flight_date).
-- Grupo 2: 2010-2020 -> 11 particiones + una DEFAULT para fechas fuera de rango.
-- Los nombres siguen las columnas de BTS en snake_case (ver docs/columnas.md).
-- =====================================================================

CREATE TABLE IF NOT EXISTS raw.flights (
    -- Time Period
    year                         smallint    NOT NULL,
    quarter                      smallint    NOT NULL,
    month                        smallint    NOT NULL,
    day_of_month                 smallint    NOT NULL,
    day_of_week                  smallint    NOT NULL,   -- 1 = lunes ... 7 = domingo (convención BTS)
    flight_date                  date        NOT NULL,

    -- Airline
    reporting_airline            varchar(3)  NOT NULL,
    dot_id_reporting_airline     integer,
    tail_number                  varchar(10),
    flight_number                integer,

    -- Origin and Destination
    origin_airport_id            integer     NOT NULL,
    origin                       varchar(5),
    origin_city_name             varchar(100),
    origin_state                 varchar(2),
    dest_airport_id              integer     NOT NULL,
    dest                         varchar(5),
    dest_city_name               varchar(100),
    dest_state                   varchar(2),

    -- Departure Performance (horas en formato hhmm, hora local del aeropuerto)
    crs_dep_time                 smallint,
    dep_time                     smallint,
    dep_delay                    real,       -- minutos; negativo = salió antes
    dep_del15                    boolean,
    dep_time_blk                 varchar(9), -- ej. '0600-0659'
    taxi_out                     real,

    -- Arrival Performance
    crs_arr_time                 smallint,
    arr_time                     smallint,
    arr_delay                    real,
    arr_del15                    boolean,
    taxi_in                      real,

    -- Cancellations and Diversions
    cancelled                    boolean     NOT NULL,
    cancellation_code            char(1),    -- A aerolínea, B clima, C NAS, D seguridad
    diverted                     boolean     NOT NULL,
    div_airport_landings         smallint,
    div_reached_dest             boolean,

    -- Flight Summaries
    crs_elapsed_time             real,
    actual_elapsed_time          real,
    air_time                     real,
    distance                     real,

    -- Cause of Delay (minutos; solo se reportan cuando arr_delay >= 15)
    carrier_delay                real,
    weather_delay                real,
    nas_delay                    real,
    security_delay               real,
    late_aircraft_delay          real,

    -- Gate Return Information at Origin Airport
    first_dep_time               smallint,
    total_add_g_time             real,
    longest_add_g_time           real
) PARTITION BY RANGE (flight_date);

-- Una partición por año del rango del grupo
DO $$
DECLARE
    y int;
BEGIN
    FOR y IN 2010..2020 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS raw.flights_%s PARTITION OF raw.flights
                 FOR VALUES FROM (%L) TO (%L)',
            y, make_date(y, 1, 1), make_date(y + 1, 1, 1));
    END LOOP;
END $$;

CREATE TABLE IF NOT EXISTS raw.flights_default PARTITION OF raw.flights DEFAULT;

-- Índices útiles para construir las dimensiones y para reprocesar un mes.
-- (Se crean en la tabla padre y PostgreSQL los propaga a cada partición.)
CREATE INDEX IF NOT EXISTS ix_raw_flights_date    ON raw.flights (flight_date);
CREATE INDEX IF NOT EXISTS ix_raw_flights_airline ON raw.flights (reporting_airline);

-- Bitácora de cargas: permite saber qué meses ya están en la base y recargar sin duplicar.
CREATE TABLE IF NOT EXISTS raw.load_log (
    year          smallint    NOT NULL,
    month         smallint    NOT NULL,
    source_file   text        NOT NULL,
    rows_loaded   integer     NOT NULL,
    loaded_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (year, month)
);
