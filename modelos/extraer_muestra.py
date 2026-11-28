"""Extrae la muestra de vuelos de dw.fact_flights (modelos/muestra.sql), un archivo Parquet por año.

Muestra: 5 % de cada año 2010-2017 (entrenamiento) y 15 % de 2018-2020 (validación, prueba y
robustez). Ver modelos/README.md. Conexión por variables de entorno de libpq (PGHOST, PGPORT,
PGDATABASE, PGUSER, PGPASSWORD), normalmente por túnel SSH:

    ssh -N -C -L 15432:localhost:5432 ubuntu@100.55.222.111      # otra terminal
    PGHOST=localhost PGPORT=15432 PGDATABASE=bts PGUSER=bts_admin PGPASSWORD=... \\
        .venv/bin/python modelos/extraer_muestra.py --salida data/modelos

Prueba rápida (100 filas de un año): --anios 2019 --limite 100  -> prueba_2019.parquet (no se usa
en los modelos ni toca extraccion.json).
Los años ya extraídos se saltan (borrar el Parquet para repetirlo).
"""
import argparse
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import psycopg

import comun as C

SQL = (Path(__file__).parent / "muestra.sql").read_text(encoding="utf-8")
TIPOS = {
    "flight_id": "int64", "cubeta": "int16", "fecha_id": "int32", "anio": "int16", "mes": "int8",
    "dia_semana": "int8", "hora_salida": "Int8", "hora_llegada_prog": "Int16",
    "aerolinea": "string", "tipo_aerolinea": "string", "origen": "string", "estado_origen": "string",
    "destino": "string", "estado_destino": "string", "distancia": "float32",
    "tiempo_programado": "float32", "retraso_salida": "float32", "retraso_llegada": "float32",
    "taxi_out": "float32", "taxi_in": "float32",
}
BOOLEANAS = ["es_feriado", "es_fin_semana", "periodo_covid", "cancelado", "desviado", "retraso_llegada_15"]


def consulta(anio: int, por_mil: int, limite: int | None) -> str:
    anio, por_mil = int(anio), int(por_mil)          # enteros: no hay inyección posible
    if not (2010 <= anio <= 2020 and 0 < por_mil <= 1000):
        raise ValueError("año o tasa fuera de rango")
    q = SQL.format(desde=anio * 10000 + 101, hasta=anio * 10000 + 1231, por_mil=por_mil)
    q = "\n".join(l for l in q.splitlines() if not l.lstrip().startswith("--"))
    return q + (f"\nLIMIT {int(limite)}" if limite else "")


def a_dataframe(texto_csv: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(texto_csv), dtype={k: v for k, v in TIPOS.items()
                                                    if v in ("string",)}, keep_default_na=False,
                     na_values=[""])   # solo el vacío es nulo (COPY csv); "NA" puede ser un código real
    for c in BOOLEANAS:
        df[c] = df[c].map({"t": True, "f": False}).astype("boolean")
    for c, t in TIPOS.items():
        if t != "string":
            df[c] = df[c].astype(t)
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", default="data/modelos")
    ap.add_argument("--anios", type=int, nargs="+", default=list(range(2010, 2021)))
    ap.add_argument("--limite", type=int, help="solo para probar la conexión y la consulta")
    a = ap.parse_args()
    out = Path(a.salida)
    out.mkdir(parents=True, exist_ok=True)
    bitacora = out / "extraccion.json"
    registro = json.loads(bitacora.read_text()) if bitacora.exists() else {"anios": {}}
    registro["consulta"] = "modelos/muestra.sql"

    def guardar_bitacora():
        # Se escribe después de cada año: si la extracción se corta, lo ya bajado queda registrado.
        if not a.limite:
            bitacora.write_text(json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8")

    def resumen(df, por_mil, seg):
        return {"por_mil": por_mil, "filas": len(df), "segundos": round(seg, 1),
                "pct_cancelados": round(100 * df.cancelado.mean(), 3),
                "pct_retraso_15_sobre_operados": round(
                    100 * df.loc[~df.cancelado & ~df.desviado, "retraso_llegada_15"].mean(), 3),
                "fecha_extraccion": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    with psycopg.connect(application_name="bts_muestra_modelos") as con:
        con.execute("SET statement_timeout = 0")
        for anio in a.anios:
            por_mil = C.POR_MIL_ENTRENAMIENTO if anio <= 2017 else C.POR_MIL_EVALUACION
            # Una prueba con --limite NUNCA se guarda como muestra_AAAA.parquet (entrenar.py lee
            # muestra_*.parquet y la corrida completa saltaría el archivo truncado).
            destino = out / (f"prueba_{anio}.parquet" if a.limite else f"muestra_{anio}.parquet")
            if destino.exists() and not a.limite:
                if str(anio) not in registro["anios"]:
                    registro["anios"][str(anio)] = resumen(pd.read_parquet(destino), por_mil, 0) | {
                        "nota": "registrado desde el Parquet existente"}
                    guardar_bitacora()
                print(f"{anio}: ya existe {destino.name}, se salta")
                continue
            t0 = time.time()
            buf = io.BytesIO()
            with con.cursor() as cur:
                with cur.copy(f"COPY ({consulta(anio, por_mil, a.limite)}) TO STDOUT WITH (FORMAT csv, HEADER true)") as cp:
                    for bloque in cp:
                        buf.write(bloque)
            df = a_dataframe(buf.getvalue())
            temporal = destino.with_suffix(".parquet.tmp")
            df.to_parquet(temporal, index=False)
            temporal.replace(destino)          # el Parquet aparece completo o no aparece
            info = resumen(df, por_mil, time.time() - t0)
            if not a.limite:
                registro["anios"][str(anio)] = info
                guardar_bitacora()
            print(f"{anio}: {len(df):,} filas ({por_mil} por mil) en {info['segundos']:.0f} s -> {destino.name}; "
                  f"cancelados {info['pct_cancelados']} %, retraso>=15 {info['pct_retraso_15_sobre_operados']} %")

if __name__ == "__main__":
    main()
