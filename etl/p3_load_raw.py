"""Paso 3 - Carga los Parquet mensuales en raw.flights con COPY (la vía más rápida en PostgreSQL).

Uso:
    python etl/p3_load_raw.py --start 2010 --end 2015 [--force]

Cada mes se carga en su propia transacción: primero borra ese mes y luego lo inserta,
así que repetir la carga nunca duplica filas. raw.load_log guarda qué meses ya están.
Sin --force, los meses que ya aparecen en raw.load_log se omiten.
"""

import argparse
import io

import pandas as pd

from common import connect, get_logger
from config import RAW_COLUMNS, YEAR_END, YEAR_START, months, parquet_path

log = get_logger("p3_load_raw")

CHUNK_ROWS = 200_000
COPY_SQL = f"COPY raw.flights ({', '.join(RAW_COLUMNS)}) FROM STDIN WITH (FORMAT csv)"


def already_loaded(conn) -> set[tuple[int, int]]:
    with conn.cursor() as cur:
        cur.execute("SELECT year, month FROM raw.load_log")
        return {(y, m) for y, m in cur.fetchall()}


def load_month(conn, year: int, month: int) -> int | None:
    src = parquet_path(year, month)
    if not src.exists():
        log.warning("%d-%02d: no existe %s", year, month, src.name)
        return None

    df = pd.read_parquet(src)[RAW_COLUMNS]
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(
            "DELETE FROM raw.flights WHERE flight_date >= make_date(%s, %s, 1) "
            "AND flight_date < make_date(%s, %s, 1) + interval '1 month'",
            (year, month, year, month),
        )
        with cur.copy(COPY_SQL) as copy:
            for i in range(0, len(df), CHUNK_ROWS):
                buf = io.StringIO()
                df.iloc[i:i + CHUNK_ROWS].to_csv(buf, index=False, header=False)
                copy.write(buf.getvalue())
        cur.execute(
            "INSERT INTO raw.load_log (year, month, source_file, rows_loaded) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (year, month) DO UPDATE SET source_file = EXCLUDED.source_file, "
            "rows_loaded = EXCLUDED.rows_loaded, loaded_at = now()",
            (year, month, src.name, len(df)),
        )
    log.info("%d-%02d: %d filas cargadas", year, month, len(df))
    return len(df)


def main(start: int, end: int, force: bool = False) -> list[tuple[int, int]]:
    failed = []
    # autocommit=True: cada mes corre en su propia transacción (conn.transaction())
    with connect(autocommit=True) as conn:
        done = set() if force else already_loaded(conn)
        for y, m in months(start, end):
            if (y, m) in done:
                log.info("%d-%02d ya está en la base, se omite (usar --force para recargar)", y, m)
                continue
            try:
                if load_month(conn, y, m) is None:
                    failed.append((y, m))
            except Exception as exc:  # noqa: BLE001
                log.error("%d-%02d: %s", y, m, exc)
                failed.append((y, m))
        conn.execute("ANALYZE raw.flights")
    return failed


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=int, default=YEAR_START)
    p.add_argument("--end", type=int, default=YEAR_END)
    p.add_argument("--force", action="store_true")
    a = p.parse_args()
    raise SystemExit(1 if main(a.start, a.end, a.force) else 0)
