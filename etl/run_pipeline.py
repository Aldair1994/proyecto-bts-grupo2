"""Orquestador del pipeline completo (cada paso también se puede correr por separado).

Uso:
    python etl/run_pipeline.py --start 2010 --end 2015
    python etl/run_pipeline.py --start 2016 --end 2020 --steps download parquet load
    python etl/run_pipeline.py --steps reference star

Pasos, en orden:
    download   p1_download.py        zips mensuales de BTS -> data/raw_zip/
    parquet    p2_to_parquet.py      columnas seleccionadas -> data/parquet/
    load       p3_load_raw.py        Parquet -> raw.flights (COPY)
    reference  p4_load_reference.py  lookups de BTS + feriados -> ref.*
    star       p5_build_star.py      raw + ref -> dw.* (modelo estrella)
"""

import argparse
import sys

import p1_download
import p2_to_parquet
import p3_load_raw
import p4_load_reference
import p5_build_star
from common import get_logger
from config import YEAR_END, YEAR_START

log = get_logger("pipeline")
ALL_STEPS = ["download", "parquet", "load", "reference", "star"]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", type=int, default=YEAR_START)
    p.add_argument("--end", type=int, default=YEAR_END)
    p.add_argument("--steps", nargs="+", choices=ALL_STEPS, default=ALL_STEPS)
    p.add_argument("--keep-zip", action="store_true", help="no borrar los zips después de convertirlos")
    a = p.parse_args()

    log.info("Inicio del pipeline: años %d-%d, pasos %s", a.start, a.end, a.steps)
    problems = []
    if "download" in a.steps:
        problems += p1_download.main(a.start, a.end)
    if "parquet" in a.steps:
        problems += p2_to_parquet.main(a.start, a.end, delete_zip=not a.keep_zip)
    if "load" in a.steps:
        problems += p3_load_raw.main(a.start, a.end)
    if "reference" in a.steps:
        p4_load_reference.main()
    if "star" in a.steps:
        p5_build_star.main(a.start, a.end)

    if problems:
        pend = sorted(set(problems))
        muestra = ", ".join(f"{y}-{m:02d}" for y, m in pend[:12])
        log.error("Terminó con %d meses pendientes: %s%s", len(pend), muestra, " ..." if len(pend) > 12 else "")
        return 1
    log.info("Pipeline terminado sin errores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
