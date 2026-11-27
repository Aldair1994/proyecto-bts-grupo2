#!/usr/bin/env python3
"""Perfilado y calidad de datos sobre los zip mensuales de datos_raw/ (reglas R01-R12).
Genera tablas/q_*.csv que alimentan el Informe de Calidad de Datos.

Uso:  python calidad/perfilado_calidad.py [--raw data/raw_zip] [--out docs/calidad] [--muestra N]
(sirve con los zip de BTS originales o con los que baja etl/p1_download.py, bts_ontime_AAAA_MM.zip)
Requiere: pandas.
Salida extra: q_resumen_2020_vs_resto.csv y q_volumen_mensual.csv para analizar la pandemia aparte."""
import argparse
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from diccionario import COLUMNAS

RAIZ = Path(__file__).resolve().parent.parent
CLAVE = ["FlightDate", "Reporting_Airline", "Flight_Number_Reporting_Airline", "Origin", "Dest", "CRSDepTime"]
HORAS = ["CRSDepTime", "DepTime", "CRSArrTime", "ArrTime"]
CAUSAS = ["CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay"]


def leer(zpath):
    with zipfile.ZipFile(zpath) as z:
        nombre = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        with z.open(nombre) as f:
            return pd.read_csv(f, usecols=COLUMNAS, low_memory=False)


def perfilar(df, archivo):
    n = len(df)
    c = df["Cancelled"] == 1
    d = df["Diverted"] == 1
    normal = ~c & ~d
    r = {"archivo": archivo, "anio": int(archivo.split("_")[-2]), "mes": int(archivo.split("_")[-1].split(".")[0]), "filas": n}
    r["R01_duplicados_clave"] = int(df.duplicated(CLAVE, keep="first").sum())
    r["R02_nulos_obligatorios"] = int(df[["FlightDate", "Reporting_Airline", "Origin", "Dest", "Cancelled", "Diverted"]].isna().any(axis=1).sum())
    r["R03_flags_invalidos"] = int((~df["Cancelled"].isin([0, 1]) | ~df["Diverted"].isin([0, 1])).sum())
    r["R04_hora_fuera_rango"] = int(sum(((df[h] < 0) | (df[h] > 2400) | (df[h] % 100 > 59)).sum() for h in HORAS))
    r["R05_distancia_no_positiva"] = int((df["Distance"] <= 0).sum())
    r["R06_cancelado_con_horas"] = int((c & (df["DepTime"].notna() | df["ArrTime"].notna())).sum())
    r["R06_cancelado_sin_codigo"] = int((c & df["CancellationCode"].isna()).sum())
    r["R07_normal_sin_retraso"] = int((normal & (df["ArrDelay"].isna() | df["DepDelay"].isna())).sum())
    r["R08_ardel15_incoherente"] = int((normal & ((df["ArrDelay"] >= 15).astype(float) != df["ArrDel15"])).sum())
    tarde = normal & (df["ArrDelay"] >= 15)
    dif = (df.loc[tarde, CAUSAS].sum(axis=1) - df.loc[tarde, "ArrDelay"]).abs()
    r["R09_causas_no_suman"] = int((dif > 1).sum())
    r["R11_retraso_atipico"] = int(((df["ArrDelay"] < -120) | (df["ArrDelay"] > 1440)).sum())
    r["cancelados"], r["desviados"] = int(c.sum()), int(d.sum())
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(RAIZ / "data" / "raw_zip"), help="carpeta con los zip mensuales")
    ap.add_argument("--out", default=str(RAIZ / "docs" / "calidad"), help="carpeta de salida de las tablas q_*.csv")
    ap.add_argument("--muestra", type=int, default=0)
    a = ap.parse_args()
    RAW, OUT = Path(a.raw), Path(a.out)
    OUT.mkdir(parents=True, exist_ok=True)
    zips = sorted(RAW.glob("*.zip"))
    if a.muestra:
        zips = zips[: a.muestra]
    if not zips:
        raise SystemExit(f"No hay zip en {RAW}. Correr primero etl/p1_download.py")
    perfiles, nulos, diarios = [], [], []
    for z in zips:
        df = leer(z)
        perfiles.append(perfilar(df, z.name))
        nu = df.isna().sum().rename(z.name)
        nulos.append(nu)
        diarios.append(df.groupby("FlightDate").agg(vuelos=("Flights", "sum"), cancelados=("Cancelled", "sum"),
                                                    desviados=("Diverted", "sum"), retraso_llegada_prom=("ArrDelay", "mean")))
        print("ok", z.name, len(df))
    p = pd.DataFrame(perfiles)
    p.to_csv(OUT / "q_reglas_por_archivo.csv", index=False)
    # 2020 (pandemia) se perfila aparte del resto del periodo
    num = p.drop(columns="archivo").assign(periodo=np.where(p["anio"] == 2020, "2020", "2010-2019"))
    num.drop(columns=["anio", "mes"]).groupby("periodo").sum().T.to_csv(OUT / "q_resumen_2020_vs_resto.csv")
    p[["anio", "mes", "filas", "cancelados", "desviados"]].to_csv(OUT / "q_volumen_mensual.csv", index=False)
    dia = pd.concat(diarios)
    dia["pct_cancelado"] = (dia["cancelados"] / dia["vuelos"] * 100).round(2)
    dia.to_csv(OUT / "q_cancelaciones_diarias.csv")   # sirve para confirmar las fechas de docs/eventos_externos.csv
    tot = p.drop(columns=["archivo", "anio", "mes"]).sum()
    resumen = tot.rename("total").to_frame()
    resumen["pct_de_filas"] = (resumen["total"] / tot["filas"] * 100).round(4)
    resumen.to_csv(OUT / "q_resumen_reglas.csv")
    nul = pd.concat(nulos, axis=1).sum(axis=1).rename("nulos").to_frame()
    nul["pct"] = (nul["nulos"] / tot["filas"] * 100).round(3)
    nul.to_csv(OUT / "q_nulos_por_columna.csv")
    print(resumen)


if __name__ == "__main__":
    main()
