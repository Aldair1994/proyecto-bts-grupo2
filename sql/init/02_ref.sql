-- =====================================================================
-- 02_ref.sql
-- Tablas de referencia que se llenan con etl/03_load_reference.py
-- =====================================================================

-- BTS "Get Lookup Table" de Reporting_Airline (L_UNIQUE_CARRIERS)
CREATE TABLE IF NOT EXISTS ref.airlines (
    code         varchar(10) PRIMARY KEY,
    description  text        NOT NULL
);

-- BTS "Get Lookup Table" de OriginAirportID / DestAirportID (L_AIRPORT_ID)
-- description viene como 'Ciudad, ST: Nombre del aeropuerto'
CREATE TABLE IF NOT EXISTS ref.airports (
    airport_id   integer PRIMARY KEY,
    description  text    NOT NULL
);

-- Coordenadas de aeropuertos (opcional, para el mapa del dashboard).
-- Se puede llenar después con la lista de aeropuertos de la FAA u OurAirports.
CREATE TABLE IF NOT EXISTS ref.airport_coords (
    iata_code    varchar(5) PRIMARY KEY,
    latitude     double precision,
    longitude    double precision,
    timezone     text
);

-- Feriados federales de EE. UU. (generados con la librería holidays)
CREATE TABLE IF NOT EXISTS ref.us_holidays (
    holiday_date date PRIMARY KEY,
    name         text NOT NULL
);
