"""Correlaciones entre variables (sección 2.11 del informe) sobre la muestra de vuelos.

Universo: vuelos OPERADOS de la muestra de entrenamiento (cubeta < 50, es decir 5 % de cada año),
2010-01 a 2020-02 (sin COVID). Incluye retraso_salida, taxi_out y taxi_in: aquí son válidas para
describir los datos, pero están PROHIBIDAS en los modelos (fuga de información); la matriz muestra
por qué (retraso de salida y de llegada están casi perfectamente correlacionados).

Uso: .venv/bin/python modelos/correlaciones.py --datos data/modelos --salida modelos/resultados
Escribe correlaciones_pearson.csv, correlaciones_spearman.csv, correlacion_objetivo.csv,
correlaciones.png y correlaciones.md.
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import comun as C

VARIABLES = {
    "retraso_llegada": "Retraso de llegada (min)",
    "retraso_salida": "Retraso de salida (min) *",
    "taxi_out": "Taxi de salida (min) *",
    "taxi_in": "Taxi de llegada (min) *",
    "distancia": "Distancia (millas)",
    "tiempo_programado": "Duración programada (min)",
    "hora_salida": "Hora de salida programada",
    "hora_llegada": "Hora de llegada programada",
    "mes": "Mes",
    "dia_semana": "Día de la semana",
}
TEXTO, TEXTO_2 = "#191919", "#666666"


def mapa_calor(m: pd.DataFrame, titulo: str, ax):
    # Divergente: dos polos + gris neutro al centro (guía dataviz).
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("div", ["#ec4647", "#efefef", "#1b64be"])
    ax.imshow(m.to_numpy(), cmap=cmap, vmin=-1, vmax=1)
    etiquetas = [VARIABLES[c] for c in m.columns]
    ax.set_xticks(range(len(m)), etiquetas, rotation=45, ha="right", fontsize=8.5)
    ax.set_yticks(range(len(m)), etiquetas, fontsize=8.5)
    for i in range(len(m)):
        for j in range(len(m)):
            v = m.iat[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7.5,
                    color="#ffffff" if abs(v) > 0.6 else TEXTO)
    ax.set_title(titulo, fontsize=11, color=TEXTO, loc="left")
    for s in ax.spines.values():
        s.set_visible(False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", default="data/modelos")
    ap.add_argument("--salida", default="modelos/resultados")
    a = ap.parse_args()
    out = Path(a.salida)
    out.mkdir(parents=True, exist_ok=True)

    df = C.cargar_muestra(Path(a.datos))
    d = df[(df.cubeta < C.POR_MIL_ENTRENAMIENTO) & ~df.cancelado & ~df.desviado & (df.fecha_id <= 20200229)]
    d = d.dropna(subset=["retraso_llegada"])
    x = d[list(VARIABLES)].astype(float)
    pearson = x.corr(method="pearson")
    spearman = x.corr(method="spearman")
    pearson.to_csv(out / "correlaciones_pearson.csv")
    spearman.to_csv(out / "correlaciones_spearman.csv")

    # Correlación de cada variable con el objetivo de la pregunta 24 (punto-biserial = Pearson con 0/1).
    y = d.retraso_llegada_15.astype(float)
    obj = pd.DataFrame({
        "variable": [VARIABLES[c] for c in VARIABLES if c != "retraso_llegada"],
        "pearson_con_retraso_llegada_15": [x[c].corr(y) for c in VARIABLES if c != "retraso_llegada"],
        "spearman_con_retraso_llegada_15": [x[c].corr(y, method="spearman") for c in VARIABLES if c != "retraso_llegada"],
        "permitida_en_modelo": [c not in C.PROHIBIDAS for c in VARIABLES if c != "retraso_llegada"],
    }).sort_values("pearson_con_retraso_llegada_15", key=np.abs, ascending=False)
    obj.to_csv(out / "correlacion_objetivo.csv", index=False)

    fig, axs = plt.subplots(1, 2, figsize=(14, 6.4), gridspec_kw={"wspace": 0.55})
    mapa_calor(pearson, "Pearson (relación lineal)", axs[0])
    mapa_calor(spearman, "Spearman (relación monótona, robusta a atípicos)", axs[1])
    fig.suptitle(f"Correlación entre variables de vuelo — {len(d):,} vuelos operados (muestra 5 %), "
                 "2010-01 a 2020-02", x=0.01, ha="left", fontsize=12, color=TEXTO, y=0.95)
    fig.text(0.01, -0.2, "* Solo se conocen al despegar o después: válidas para describir, prohibidas en los "
             "modelos (fuga de información).\nRojo = correlación negativa, azul = positiva. "
             "Fuente: BTS, muestra de dw.fact_flights; cálculo propio.", fontsize=8.5, color=TEXTO_2)
    fig.savefig(out / "correlaciones.png", dpi=170, bbox_inches="tight")
    plt.close(fig)

    def tabla(m):
        cols = list(m.columns)
        filas = ["| | " + " | ".join(VARIABLES[c] for c in cols) + " |", "|---|" + "---:|" * len(cols)]
        for i in cols:
            filas.append(f"| {VARIABLES[i]} | " + " | ".join(f"{m.at[i, j]:.2f}" for j in cols) + " |")
        return "\n".join(filas)

    p_sal = pearson.at["retraso_salida", "retraso_llegada"]
    texto = [
        "# Correlaciones entre variables (informe 2.11)", "",
        f"- **Universo**: {len(d):,} vuelos operados con retraso de llegada informado, muestra del 5 % de cada "
        "año, 2010-01 a 2020-02 (sin COVID). Las variables con * se conocen al despegar o después: "
        "**prohibidas en los modelos**.",
        f"- Retraso de salida vs. retraso de llegada: Pearson **{p_sal:.2f}**. Usarlo en el modelo sería "
        "predecir el retraso con el propio retraso (fuga de información); por eso se excluye.", "",
        "## Correlación con el objetivo de la pregunta 24 (retraso de llegada >= 15 min)", "",
        "| Variable | Pearson | Spearman | ¿Permitida en el modelo? |", "|---|---:|---:|---|",
        *[f"| {r.variable} | {r.pearson_con_retraso_llegada_15:.3f} | {r.spearman_con_retraso_llegada_15:.3f} | "
          f"{'sí' if r.permitida_en_modelo else 'no (fuga)'} |" for r in obj.itertuples()], "",
        "## Pearson", "", tabla(pearson), "", "## Spearman", "", tabla(spearman), "",
        "Figura: `correlaciones.png`. Nota: mes, día y hora son cíclicos; una correlación lineal baja no "
        "descarta un efecto (ver los patrones por hora y mes en `docs/analisis/04_hallazgos.md` 5.2).",
    ]
    (out / "correlaciones.md").write_text("\n".join(texto) + "\n", encoding="utf-8")
    print(f"correlaciones sobre {len(d):,} vuelos -> {out}")


if __name__ == "__main__":
    main()
