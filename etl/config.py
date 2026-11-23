"""Configuración compartida del pipeline: rutas, URLs y columnas seleccionadas de BTS."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Rango del grupo (Grupo 2: 2010-2020)
# ---------------------------------------------------------------------------
YEAR_START = 2010
YEAR_END = 2020

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ZIP_DIR = DATA_DIR / "raw_zip"          # zips mensuales descargados de BTS
PARQUET_DIR = DATA_DIR / "parquet"      # un Parquet por mes, solo columnas seleccionadas
LOOKUP_DIR = DATA_DIR / "lookups"       # tablas "Get Lookup Table" de BTS
LOG_DIR = DATA_DIR / "logs"
SQL_DIR = ROOT / "sql"

# ---------------------------------------------------------------------------
# Fuentes
# ---------------------------------------------------------------------------
# Archivos mensuales "prezipped" de la tabla Reporting Carrier On-Time Performance.
# Traen todas las columnas; aquí solo conservamos las de COLUMNS.
BTS_MONTH_URL = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)

# Lookups ("Get Lookup Table" en la página de BTS)
BTS_LOOKUP_URL = "https://www.transtats.bts.gov/Download_Lookup.asp?Y11x72={name}"
LOOKUPS = {
    "airlines": "L_UNIQUE_CARRIERS",   # código Reporting_Airline -> nombre
    "airports": "L_AIRPORT_ID",        # AirportID -> 'Ciudad, ST: Nombre'
}

# ---------------------------------------------------------------------------
# Columnas seleccionadas: nombre en BTS -> (nombre en raw.flights, tipo)
# Tipos: int, float, bool, str, date, hhmm (hora en formato hhmm)
# La justificación de cada columna está en docs/columnas.md
# ---------------------------------------------------------------------------
COLUMNS = {
    # Time Period
    "Year":                            ("year", "int"),
    "Quarter":                         ("quarter", "int"),
    "Month":                           ("month", "int"),
    "DayofMonth":                      ("day_of_month", "int"),
    "DayOfWeek":                       ("day_of_week", "int"),
    "FlightDate":                      ("flight_date", "date"),
    # Airline
    "Reporting_Airline":               ("reporting_airline", "str"),
    "DOT_ID_Reporting_Airline":        ("dot_id_reporting_airline", "int"),
    "Tail_Number":                     ("tail_number", "str"),
    "Flight_Number_Reporting_Airline": ("flight_number", "int"),
    # Origin and Destination
    "OriginAirportID":                 ("origin_airport_id", "int"),
    "Origin":                          ("origin", "str"),
    "OriginCityName":                  ("origin_city_name", "str"),
    "OriginState":                     ("origin_state", "str"),
    "DestAirportID":                   ("dest_airport_id", "int"),
    "Dest":                            ("dest", "str"),
    "DestCityName":                    ("dest_city_name", "str"),
    "DestState":                       ("dest_state", "str"),
    # Departure Performance
    "CRSDepTime":                      ("crs_dep_time", "hhmm"),
    "DepTime":                         ("dep_time", "hhmm"),
    "DepDelay":                        ("dep_delay", "float"),
    "DepDel15":                        ("dep_del15", "bool"),
    "DepTimeBlk":                      ("dep_time_blk", "str"),
    "TaxiOut":                         ("taxi_out", "float"),
    # Arrival Performance
    "CRSArrTime":                      ("crs_arr_time", "hhmm"),
    "ArrTime":                         ("arr_time", "hhmm"),
    "ArrDelay":                        ("arr_delay", "float"),
    "ArrDel15":                        ("arr_del15", "bool"),
    "TaxiIn":                          ("taxi_in", "float"),
    # Cancellations and Diversions
    "Cancelled":                       ("cancelled", "bool"),
    "CancellationCode":                ("cancellation_code", "str"),
    "Diverted":                        ("diverted", "bool"),
    "DivAirportLandings":              ("div_airport_landings", "int"),
    "DivReachedDest":                  ("div_reached_dest", "bool"),
    # Flight Summaries
    "CRSElapsedTime":                  ("crs_elapsed_time", "float"),
    "ActualElapsedTime":               ("actual_elapsed_time", "float"),
    "AirTime":                         ("air_time", "float"),
    "Distance":                        ("distance", "float"),
    # Cause of Delay
    "CarrierDelay":                    ("carrier_delay", "float"),
    "WeatherDelay":                    ("weather_delay", "float"),
    "NASDelay":                        ("nas_delay", "float"),
    "SecurityDelay":                   ("security_delay", "float"),
    "LateAircraftDelay":               ("late_aircraft_delay", "float"),
    # Gate Return Information at Origin Airport
    "FirstDepTime":                    ("first_dep_time", "hhmm"),
    "TotalAddGTime":                   ("total_add_g_time", "float"),
    "LongestAddGTime":                 ("longest_add_g_time", "float"),
}

RAW_COLUMNS = [raw for raw, _ in COLUMNS.values()]


def months(year_start: int, year_end: int):
    """Genera (año, mes) para todo el rango, inclusive."""
    for y in range(year_start, year_end + 1):
        for m in range(1, 13):
            yield y, m


def zip_path(year: int, month: int) -> Path:
    return ZIP_DIR / f"bts_ontime_{year}_{month:02d}.zip"


def parquet_path(year: int, month: int) -> Path:
    return PARQUET_DIR / str(year) / f"flights_{year}_{month:02d}.parquet"
