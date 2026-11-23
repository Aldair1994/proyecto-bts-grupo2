"""Paso 1 - Descarga los zips mensuales de On-Time Performance desde BTS.

Uso:
    python etl/p1_download.py --start 2010 --end 2015

- Salta los meses que ya están descargados y son zips válidos.
- Descarga primero a un archivo .part y lo renombra al terminar, así una descarga
  interrumpida nunca queda como si estuviera completa.
- Reintenta 3 veces con espera creciente.
"""

import argparse
import time
import zipfile

import requests

from common import get_logger
from config import BTS_MONTH_URL, YEAR_END, YEAR_START, ZIP_DIR, months, zip_path

log = get_logger("p1_download")


def is_valid_zip(path) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            return z.testzip() is None
    except (zipfile.BadZipFile, FileNotFoundError):
        return False


def download_month(year: int, month: int, retries: int = 3) -> bool:
    dest = zip_path(year, month)
    if dest.exists() and is_valid_zip(dest):
        log.info("%d-%02d ya descargado, se omite", year, month)
        return True

    url = BTS_MONTH_URL.format(year=year, month=month)
    tmp = dest.with_suffix(".part")
    for attempt in range(1, retries + 1):
        try:
            log.info("Descargando %d-%02d (intento %d)", year, month, attempt)
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(tmp, "wb") as fh:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        fh.write(chunk)
            if not is_valid_zip(tmp):
                raise ValueError("el archivo descargado no es un zip válido")
            tmp.replace(dest)
            log.info("%d-%02d listo (%.1f MB)", year, month, dest.stat().st_size / 1e6)
            return True
        except Exception as exc:  # noqa: BLE001 - se registra y se reintenta
            log.warning("Fallo en %d-%02d: %s", year, month, exc)
            tmp.unlink(missing_ok=True)
            time.sleep(10 * attempt)
    log.error("No se pudo descargar %d-%02d después de %d intentos", year, month, retries)
    return False


def main(start: int, end: int) -> list[tuple[int, int]]:
    ZIP_DIR.mkdir(parents=True, exist_ok=True)
    failed = [(y, m) for y, m in months(start, end) if not download_month(y, m)]
    if failed:
        log.error("Meses con error: %s", ", ".join(f"{y}-{m:02d}" for y, m in failed))
    return failed


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=int, default=YEAR_START)
    p.add_argument("--end", type=int, default=YEAR_END)
    a = p.parse_args()
    raise SystemExit(1 if main(a.start, a.end) else 0)
