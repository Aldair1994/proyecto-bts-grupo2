"""Paso 5 - Construye el modelo estrella (dw.*) a partir de raw.flights y ref.*.

Uso:
    python etl/p5_build_star.py [--start 2010 --end 2020]

Orden: dim_fecha -> dim_airline -> dim_airport -> fact_flights (un año a la vez).
Todo es idempotente: volver a correrlo reemplaza los datos del año, no los duplica.
"""

import argparse

import psycopg

from common import connect, get_logger
from config import SQL_DIR, YEAR_END, YEAR_START

log = get_logger("p5_build_star")

BUILD = SQL_DIR / "build"
DIMENSIONS = ["10_dim_fecha.sql", "11_dim_airline.sql", "12_dim_airport.sql"]
FACT = "20_fact_flights.sql"


def run_sql(conn, filename: str, params: dict | None = None) -> None:
    sql = (BUILD / filename).read_text(encoding="utf-8")
    # ClientCursor permite varios comandos en un solo execute con parámetros
    with psycopg.ClientCursor(conn) as cur:
        cur.execute(sql, params)


def years_with_data(conn, start: int, end: int) -> list[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT year FROM raw.load_log WHERE year BETWEEN %s AND %s ORDER BY 1", (start, end))
        return [r[0] for r in cur.fetchall()]


def main(start: int, end: int) -> None:
    with connect() as conn:
        for f in DIMENSIONS:
            log.info("Ejecutando %s", f)
            run_sql(conn, f)
            conn.commit()

        for year in years_with_data(conn, start, end):
            log.info("Cargando fact_flights %d", year)
            run_sql(conn, FACT, {"anio": year})
            conn.commit()

        conn.execute("ANALYZE dw.fact_flights")
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.anio, count(*) AS vuelos,
                       round(100.0 * avg((f.estado_vuelo = 'A tiempo')::int), 1) AS pct_a_tiempo
                FROM dw.fact_flights f JOIN dw.dim_fecha d USING (fecha_id)
                GROUP BY d.anio ORDER BY d.anio""")
            for anio, vuelos, pct in cur.fetchall():
                log.info("Resumen %s: %s vuelos, %s%% a tiempo", anio, f"{vuelos:,}", pct)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=int, default=YEAR_START)
    p.add_argument("--end", type=int, default=YEAR_END)
    a = p.parse_args()
    main(a.start, a.end)
