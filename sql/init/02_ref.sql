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

-- Catálogo de aerolíneas armado por el Data Administrator (docs/catalogo_aerolineas.csv):
-- nombre común, tipo (Tradicional / Bajo costo / Regional) y años con datos.
CREATE TABLE IF NOT EXISTS ref.airline_catalog (
    reporting_airline     varchar(3) PRIMARY KEY,
    nombre_comun          text       NOT NULL,
    tipo_aerolinea        varchar(12) NOT NULL,
    anio_inicio_en_datos  smallint,
    anio_fin_en_datos     smallint,
    vuelos_2010_2020      bigint,
    nota                  text
);
