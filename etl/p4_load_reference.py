"""Paso 4 - Carga las tablas de referencia: lookups de BTS, feriados y (opcional) coordenadas.

Uso:
    python etl/p4_load_reference.py

- Lookups: si data/lookups/L_UNIQUE_CARRIERS.csv o L_AIRPORT_ID.csv ya existen, se usan.
  Si no, se intentan descargar de BTS. Si la descarga falla, bajarlas a mano con el botón
  "Get Lookup Table" de la página de BTS y guardarlas en data/lookups/ con ese nombre.
- Feriados federales de EE. UU. 2010-2020 con la librería holidays.
- Coordenadas (opcional, para el mapa): si existe data/lookups/airport_coords.csv con
  columnas iata_code, latitude, longitude, timezone, se carga en ref.airport_coords.
"""

import io

import holidays
import pandas as pd
import requests

from common import connect, get_logger
from config import BTS_LOOKUP_URL, LOOKUP_DIR, LOOKUPS, YEAR_END, YEAR_START

log = get_logger("p4_load_reference")


def get_lookup(name: str) -> pd.DataFrame:
    path = LOOKUP_DIR / f"{name}.csv"
    if not path.exists():
        log.info("Descargando lookup %s", name)
        r = requests.get(BTS_LOOKUP_URL.format(name=name), timeout=60)
        r.raise_for_status()
        LOOKUP_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    return df[["code", "description"]].dropna()


def copy_df(cur, table: str, df: pd.DataFrame) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False)
    with cur.copy(f"COPY {table} ({', '.join(df.columns)}) FROM STDIN WITH (FORMAT csv)") as cp:
        cp.write(buf.getvalue())


def main() -> None:
    airlines = get_lookup(LOOKUPS["airlines"])
    airports = get_lookup(LOOKUPS["airports"]).rename(columns={"code": "airport_id"})
    airports = airports[airports["airport_id"].str.isdigit()]

    us_hol = holidays.US(years=range(YEAR_START, YEAR_END + 1))
    hol = pd.DataFrame(sorted(us_hol.items()), columns=["holiday_date", "name"])

    coords_path = LOOKUP_DIR / "airport_coords.csv"

    with connect() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE ref.airlines, ref.airports, ref.us_holidays")
        copy_df(cur, "ref.airlines", airlines)
        copy_df(cur, "ref.airports", airports)
        copy_df(cur, "ref.us_holidays", hol)
        log.info("Lookups: %d aerolíneas, %d aeropuertos, %d feriados", len(airlines), len(airports), len(hol))

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
