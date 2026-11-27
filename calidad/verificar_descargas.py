#!/usr/bin/env python3
"""Verifica los zip descargados contra docs/manifiesto_fuente.csv (SHA-256 por mes).

Uso (desde la raiz del repo, en el servidor o en cualquier maquina):
    python3 calidad/verificar_descargas.py
    python3 calidad/verificar_descargas.py --raw /ruta/zips --reporte verificacion.csv

Reconoce los nombres del pipeline (bts_ontime_AAAA_MM.zip) y los originales de BTS.
Solo usa la libreria estandar y no modifica ningun zip.

Estados por mes:
    OK           el hash coincide con el manifiesto
    DISTINTO     el zip abre bien pero su contenido difiere (BTS pudo republicar el mes)
    CORRUPTO     el zip no abre o esta incompleto: volver a descargarlo
    FALTA        no esta en la carpeta
Termina con codigo 0 solo si los meses pedidos estan en OK.
"""
import argparse
import csv
import hashlib
import re
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NOMBRE = re.compile(r"(?:bts_ontime|1987_present)_(\d{4})_(\d{1,2})\.zip$")


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def zip_sano(ruta):
    try:
        with zipfile.ZipFile(ruta) as z:
            return z.testzip() is None
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=RAIZ / "data" / "raw_zip")
    ap.add_argument("--manifiesto", type=Path, default=RAIZ / "docs" / "manifiesto_fuente.csv")
    ap.add_argument("--start", type=int, default=2010)
    ap.add_argument("--end", type=int, default=2020)
    ap.add_argument("--reporte", type=Path, help="guarda el resultado por mes en un CSV")
    a = ap.parse_args()

    with open(a.manifiesto, encoding="utf-8-sig", newline="") as f:
        esperado = {(int(r["anio"]), int(r["mes"])): r for r in csv.DictReader(f)
                    if a.start <= int(r["anio"]) <= a.end}
    if not esperado:
        sys.exit("El manifiesto no tiene meses en el rango pedido.")
    if not a.raw.is_dir():
        sys.exit(f"No existe la carpeta de zips: {a.raw}")

    encontrados = {}
    for ruta in sorted(a.raw.glob("*.zip")):
        m = NOMBRE.search(ruta.name)
        if m:
            encontrados[(int(m[1]), int(m[2]))] = ruta

    filas = []
    for (anio, mes), r in sorted(esperado.items()):
        ruta = encontrados.get((anio, mes))
        hash_local, tam = "", ""
        if ruta is None:
            estado = "FALTA"
        else:
            hash_local, tam = sha256(ruta), ruta.stat().st_size
            if hash_local == r["sha256"]:
                estado = "OK"
            else:
                estado = "DISTINTO" if zip_sano(ruta) else "CORRUPTO"
        filas.append({"anio": anio, "mes": mes, "estado": estado,
                      "archivo": ruta.name if ruta else "",
                      "bytes_esperados": r["bytes"], "bytes_locales": tam,
                      "sha256_esperado": r["sha256"], "sha256_local": hash_local})
        if estado != "OK":
            print(f"{anio}-{mes:02d}  {estado}")

    if a.reporte:
        with open(a.reporte, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)

    conteo = {e: sum(x["estado"] == e for x in filas) for e in ("OK", "DISTINTO", "CORRUPTO", "FALTA")}
    print(f"Meses revisados: {len(filas)} | " + " | ".join(f"{k}: {v}" for k, v in conteo.items()))
    sys.exit(0 if conteo["OK"] == len(filas) else 1)


if __name__ == "__main__":
    main()
