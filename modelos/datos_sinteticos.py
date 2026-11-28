"""Genera una muestra SINTÉTICA con las mismas columnas que modelos/extraer_muestra.py,
para probar correlaciones.py y entrenar.py sin el servidor. Los números no significan nada.

Uso: .venv/bin/python modelos/datos_sinteticos.py --salida /tmp/muestra_sintetica --filas 300000
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import comun as C

AEROLINEAS = {"WN": "Bajo costo", "DL": "Tradicional", "AA": "Tradicional", "OO": "Regional",
              "UA": "Tradicional", "B6": "Bajo costo", "MQ": "Regional", "HA": "Tradicional"}
AEROPUERTOS = [(f"A{i:02d}", ["CA", "TX", "NY", "IL", "FL", "HI", "CO", "GA"][i % 8]) for i in range(60)]


def generar(filas: int, semilla: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    # Cada año aporta lo que aportaría la extracción real: 5 % hasta 2017, 15 % desde 2018.
    peso = np.array([1.0] * 8 + [3.0] * 3)
    anio = rng.choice(np.arange(2010, 2021), filas, p=peso / peso.sum())
    tope = np.where(anio <= 2017, C.POR_MIL_ENTRENAMIENTO, C.POR_MIL_EVALUACION)
    cubeta = (rng.random(filas) * tope).astype(int)
    mes = rng.integers(1, 13, filas)
    dia = rng.integers(1, 29, filas)
    fecha = pd.to_datetime(dict(year=anio, month=mes, day=dia))
    hora = rng.choice(np.arange(5, 24), filas)
    aer = rng.choice(list(AEROLINEAS), filas)
    io, idd = rng.integers(0, 60, filas), rng.integers(0, 60, filas)
    dist = rng.gamma(2.0, 400, filas).round()
    covid = (anio == 2020) & (mes >= 3)

    # Señales: más retraso de tarde, en verano/diciembre, en ciertos aeropuertos y aerolíneas.
    logit = (-2.2 + 0.07 * (hora - 5) + 0.3 * np.isin(mes, [6, 7, 12]) + 0.4 * (io % 7 == 0)
             + 0.3 * np.isin(aer, ["B6", "MQ"]) - 0.4 * (aer == "HA") - 1.0 * covid
             + rng.normal(0, 0.6, filas))
    retraso15 = rng.random(filas) < 1 / (1 + np.exp(-logit))
    lc = -4.3 + 0.8 * np.isin(mes, [1, 2]) + 0.5 * (io % 11 == 0) + 0.3 * (aer == "OO") + 2.0 * covid
    cancelado = rng.random(filas) < 1 / (1 + np.exp(-lc))
    desviado = ~cancelado & (rng.random(filas) < 0.0025)
    ret_sal = np.where(retraso15, rng.gamma(2, 25, filas), rng.normal(-3, 6, filas))
    ret_lle = ret_sal + rng.normal(-5, 8, filas)
    df = pd.DataFrame({
        "flight_id": np.arange(filas), "cubeta": cubeta, "fecha_id": fecha.dt.strftime("%Y%m%d").astype(int),
        "anio": anio, "mes": mes, "dia_semana": fecha.dt.day_of_week + 1,
        "es_feriado": rng.random(filas) < 0.03, "es_fin_semana": fecha.dt.day_of_week >= 5,
        "periodo_covid": covid, "hora_salida": hora,
        "hora_llegada_prog": ((hora + (dist / 450).astype(int) + 1) % 24) * 100 + rng.integers(0, 60, filas),
        "aerolinea": aer, "tipo_aerolinea": [AEROLINEAS[a] for a in aer],
        "origen": [AEROPUERTOS[i][0] for i in io], "estado_origen": [AEROPUERTOS[i][1] for i in io],
        "destino": [AEROPUERTOS[i][0] for i in idd], "estado_destino": [AEROPUERTOS[i][1] for i in idd],
        "distancia": dist, "tiempo_programado": (dist / 7.5 + 30).round(),
        "cancelado": cancelado, "desviado": desviado,
        "retraso_llegada_15": pd.array(np.where(cancelado | desviado, None, retraso15), dtype="boolean"),
        "retraso_salida": np.where(cancelado, np.nan, ret_sal.round()),
        "retraso_llegada": np.where(cancelado | desviado, np.nan, ret_lle.round()),
        "taxi_out": np.where(cancelado, np.nan, rng.gamma(3, 5, filas).round()),
        "taxi_in": np.where(cancelado | desviado, np.nan, rng.gamma(2, 4, filas).round()),
    })
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", required=True)
    ap.add_argument("--filas", type=int, default=300_000)
    a = ap.parse_args()
    out = Path(a.salida)
    out.mkdir(parents=True, exist_ok=True)
    df = generar(a.filas)
    for anio, g in df.groupby("anio"):
        g.to_parquet(out / f"muestra_{anio}.parquet", index=False)
    print(f"{len(df):,} filas sintéticas en {out}")


if __name__ == "__main__":
    main()
