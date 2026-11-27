"""Paso 4 - Carga las tablas de referencia: lookups de BTS, feriados y (opcional) coordenadas.

Uso:
    python etl/p4_load_reference.py

- Lookups: si data/lookups/L_UNIQUE_CARRIERS.csv o L_AIRPORT_ID.csv ya existen, se usan.
  Si no, se intentan descargar de BTS. Si la descarga falla, bajarlas a mano con el botón
  "Get Lookup Table" de la página de BTS y guardarlas en data/lookups/ con ese nombre.
- Feriados federales de EE. UU. 2010-2020 con la librería holidays.
- Catálogo de aerolíneas del Data Administrator (docs/catalogo_aerolineas.csv):
  nombre común y tipo (Tradicional / Bajo costo / Regional) -> ref.airline_catalog.
- Coordenadas (opcional, para el mapa): si existe data/lookups/airport_coords.csv con
  columnas iata_code, latitude, longitude, timezone, se carga en ref.airport_coords.
"""

import io

import holidays
import pandas as pd
import requests

from common import connect, get_logger
from config import BTS_LOOKUP_URL, LOOKUP_DIR, LOOKUPS, ROOT, YEAR_END, YEAR_START

log = get_logger("p4_load_reference")


def _looks_like_lookup(content: bytes) -> bool:
    """Una lookup válida de BTS es un CSV cuya primera línea es Code,Description."""
    first_line = content.lstrip(b"\xef\xbb\xbf").split(b"\n", 1)[0].lower()
    return b"code" in first_line and b"description" in first_line


def get_lookup(name: str) -> pd.DataFrame | None:
    """Devuelve la lookup como DataFrame (code, description), o None si no está disponible.

    Si no hay archivo local, intenta descargarlo. Si BTS no devuelve un CSV válido
    (por ejemplo una página HTML), NO se guarda nada y se continúa sin esa lookup:
    las dimensiones se construyen igual, usando los códigos y ciudades de raw.flights.
    """
    path = LOOKUP_DIR / f"{name}.csv"
    if path.exists() and not _looks_like_lookup(path.read_bytes()):
        log.warning("%s no es un CSV válido (descarga fallida anterior); se borra", path.name)
        path.unlink()

    if not path.exists():
        log.info("Descargando lookup %s", name)
        try:
            r = requests.get(BTS_LOOKUP_URL.format(name=name), timeout=60)
            r.raise_for_status()
            if not _looks_like_lookup(r.content):
                raise ValueError("BTS no devolvió un CSV")
            LOOKUP_DIR.mkdir(parents=True, exist_ok=True)
            path.write_bytes(r.content)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "No se pudo descargar %s (%s). Bájala a mano con 'Get Lookup Table' en la página "
                "de BTS y guárdala como data/lookups/%s.csv. Se continúa sin ella.",
                name, exc, name)
            return None

    # Las lookups de BTS vienen en Windows-1252 (nombres con acentos, p. ej. aeropuertos
    # de Puerto Rico o México); si no son UTF-8 válido se leen con cp1252.
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, dtype=str, encoding="cp1252")
    df.columns = [c.strip().lower() for c in df.columns]
    return df[["code", "description"]].dropna()


def copy_df(cur, table: str, df: pd.DataFrame) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False)
    with cur.copy(f"COPY {table} ({', '.join(df.columns)}) FROM STDIN WITH (FORMAT csv)") as cp:
        cp.write(buf.getvalue())


def main() -> None:
    empty = pd.DataFrame(columns=["code", "description"])
    airlines = get_lookup(LOOKUPS["airlines"])
    airlines = empty if airlines is None else airlines
    airports = get_lookup(LOOKUPS["airports"])
    airports = (empty if airports is None else airports).rename(columns={"code": "airport_id"})
    airports = airports[airports["airport_id"].str.isdigit()]

    us_hol = holidays.US(years=range(YEAR_START, YEAR_END + 1))
    hol = pd.DataFrame(sorted(us_hol.items()), columns=["holiday_date", "name"])

    coords_path = LOOKUP_DIR / "airport_coords.csv"
    catalog_path = ROOT / "docs" / "catalogo_aerolineas.csv"

    with connect() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE ref.airlines, ref.airports, ref.us_holidays")
        copy_df(cur, "ref.airlines", airlines)
        copy_df(cur, "ref.airports", airports)
        copy_df(cur, "ref.us_holidays", hol)
        log.info("Lookups: %d aerolíneas, %d aeropuertos, %d feriados", len(airlines), len(airports), len(hol))

        cur.execute("""
            CREATE TABLE IF NOT EXISTS ref.airline_catalog (
                reporting_airline varchar(3) PRIMARY KEY, nombre_comun text NOT NULL,
                tipo_aerolinea varchar(12) NOT NULL, anio_inicio_en_datos smallint,
                anio_fin_en_datos smallint, vuelos_2010_2020 bigint, nota text)""")
        cur.execute("TRUNCATE ref.airline_catalog")
        if catalog_path.exists():
            cat = pd.read_csv(catalog_path, dtype=str, encoding="utf-8-sig")
            cols = ["reporting_airline", "nombre_comun", "tipo_aerolinea", "anio_inicio_en_datos",
                    "anio_fin_en_datos", "vuelos_2010_2020", "nota"]
            copy_df(cur, "ref.airline_catalog", cat[cols])
            log.info("Catálogo de aerolíneas: %d aerolíneas", len(cat))
        else:
            log.warning("No existe %s: dim_airline quedará sin tipo de aerolínea", catalog_path)

        if coords_path.exists():
            coords = pd.read_csv(coords_path, dtype={"iata_code": str})
            coords = coords[["iata_code", "latitude", "longitude", "timezone"]].drop_duplicates("iata_code")
            cur.execute("TRUNCATE ref.airport_coords")
            copy_df(cur, "ref.airport_coords", coords)
            log.info("Coordenadas: %d aeropuertos", len(coords))
        else:
            log.info("Sin airport_coords.csv: dim_airport quedará sin latitud/longitud por ahora")
        conn.commit()


if __name__ == "__main__":
    main()
