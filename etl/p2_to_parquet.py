"""Paso 2 - Extrae del zip solo las columnas seleccionadas, les da tipo y guarda un Parquet por mes.

Uso:
    python etl/p2_to_parquet.py --start 2010 --end 2015 [--delete-zip]

--delete-zip borra cada zip después de convertirlo, para ahorrar espacio en disco.
El Parquet ocupa una fracción del CSV original porque guarda menos columnas y va comprimido.
"""

import argparse
import zipfile

import pandas as pd

from common import get_logger
from config import COLUMNS, PARQUET_DIR, YEAR_END, YEAR_START, months, parquet_path, zip_path

log = get_logger("p2_to_parquet")


def _hhmm(s: pd.Series) -> pd.Series:
    """Horas hhmm ('0730', '730', 730.0) -> entero 730. Vacíos -> NA."""
    return pd.to_numeric(s, errors="coerce").round().astype("Int16")


def _bool(s: pd.Series) -> pd.Series:
    """BTS codifica banderas como 0.00 / 1.00."""
    return pd.to_numeric(s, errors="coerce").map({0: False, 1: True}).astype("boolean")


def cast(df: pd.DataFrame) -> pd.DataFrame:
    out = {}
    for bts_name, (raw_name, kind) in COLUMNS.items():
        s = df[bts_name]
        if kind == "int":
            out[raw_name] = pd.to_numeric(s, errors="coerce").astype("Int32")
        elif kind == "float":
            out[raw_name] = pd.to_numeric(s, errors="coerce").astype("float32")
        elif kind == "bool":
            out[raw_name] = _bool(s)
        elif kind == "hhmm":
            out[raw_name] = _hhmm(s)
        elif kind == "date":
            out[raw_name] = pd.to_datetime(s, errors="coerce").dt.date
        else:  # str
            out[raw_name] = s.astype("string").str.strip().replace("", pd.NA)
    return pd.DataFrame(out)


def convert_month(year: int, month: int, delete_zip: bool = False) -> int | None:
    src = zip_path(year, month)
    dest = parquet_path(year, month)
    if dest.exists():
        log.info("%d-%02d ya convertido, se omite", year, month)
        return 0
    if not src.exists():
        log.warning("%d-%02d: no existe el zip %s", year, month, src.name)
        return None

    with zipfile.ZipFile(src) as z:
        csv_name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(csv_name) as fh:
            header = pd.read_csv(fh, nrows=0).columns
        missing = [c for c in COLUMNS if c not in header]
        if missing:
            raise KeyError(f"{src.name}: faltan columnas {missing}. Revisar COLUMNS en config.py")
        with z.open(csv_name) as fh:
            df = pd.read_csv(fh, usecols=list(COLUMNS), dtype=str, keep_default_na=True)

    df = cast(df)
    n_bad_dates = df["flight_date"].isna().sum()
    if n_bad_dates:
        log.warning("%d-%02d: %d filas sin fecha válida se descartan", year, month, n_bad_dates)
        df = df[df["flight_date"].notna()]

    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(dest, index=False, compression="zstd")
    log.info("%d-%02d: %d filas -> %s (%.1f MB)", year, month, len(df), dest.name, dest.stat().st_size / 1e6)

    if delete_zip:
        src.unlink()
    return len(df)


def main(start: int, end: int, delete_zip: bool = False) -> list[tuple[int, int]]:
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    failed = []
    for y, m in months(start, end):
        try:
            if convert_month(y, m, delete_zip) is None:
                failed.append((y, m))
        except Exception as exc:  # noqa: BLE001
            log.error("%d-%02d: %s", y, m, exc)
            failed.append((y, m))
    return failed


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=int, default=YEAR_START)
    p.add_argument("--end", type=int, default=YEAR_END)
    p.add_argument("--delete-zip", action="store_true")
    a = p.parse_args()
    raise SystemExit(1 if main(a.start, a.end, a.delete_zip) else 0)
