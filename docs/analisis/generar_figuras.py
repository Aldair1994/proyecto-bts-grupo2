#!/usr/bin/env python
"""Genera las figuras F01-F16 del informe CRISP-DM (BTS 2010-2020).

Uso (desde la raiz del repo):
    .venv/bin/python docs/analisis/generar_figuras.py sql/analisis/resultados/20261127_completo

Entradas: CSV de resultados (sql/analisis/resultados/...) y docs/mart_serie_diaria.csv.
Salida: PNG en docs/analisis/figuras/. Una funcion por figura.
Convenciones: % a tiempo = llegada con < 15 min de retraso, sobre vuelos operados;
% cancelados sobre programados. COVID = franja sombreada desde 2020-03-01.
"""
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import Patch, Rectangle

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "analisis" / "figuras"
MART_DIARIA = ROOT / "docs" / "mart_serie_diaria.csv"
DPI = 170
FUENTE = "Fuente: BTS, cálculo propio"

# Paleta categorica por defecto (skill dataviz, modo claro), en orden fijo.
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac", "#008a17", "#6a4ce2", "#ec4647")
INK, INK2, GRID, COVID_C = "#191919", "#666666", "#e3e3e3", "#d9d9d9"
SEQ = ["#cce3fd", "#9dc8f7", "#6aabf1", "#338ced", "#2370cd", "#1757ac", "#0e3d7e"]
SEQ_CMAP = LinearSegmentedColormap.from_list("azul", SEQ)

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": "#999999", "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
    "axes.axisbelow": True, "legend.frameon": False, "figure.facecolor": "white",
})

COVID_INI = pd.Timestamp("2020-03-01")
NOTA_COVID = "Franja gris: COVID, desde 2020-03-01"


# ---------------------------------------------------------------- utilidades
def leer(res: Path, nombre: str) -> pd.DataFrame:
    return pd.read_csv(res / f"{nombre}.csv")


def titulos(fig, titulo, subtitulo):
    h = fig.get_figheight()
    fig.suptitle(titulo, x=0.01, ha="left", va="top", fontsize=14, fontweight="bold", y=1 - 0.12 / h)
    fig.text(0.01, 1 - 0.55 / h, subtitulo, ha="left", va="top", fontsize=9.5, color=INK2)


def guardar(fig, nombre, pie=None):
    OUT.mkdir(parents=True, exist_ok=True)
    texto = FUENTE + (f". {pie}" if pie else "")
    fig.text(0.01, 0.008, texto, fontsize=8, color=INK2, ha="left", va="bottom")
    fig.savefig(OUT / nombre, dpi=DPI, bbox_inches=None)
    plt.close(fig)
    print("OK", nombre)


def fig_base(h=5.6, w=10):
    return plt.subplots(figsize=(w, h))


def layout(fig, top=0.83, bottom=0.14, **kw):
    fig.subplots_adjust(top=top, bottom=bottom, left=kw.pop("left", 0.08), right=kw.pop("right", 0.97), **kw)


def sombrear_covid(ax, fin=pd.Timestamp("2020-12-31")):
    ax.axvspan(COVID_INI, fin, color=COVID_C, alpha=0.55, lw=0, zorder=0)


def fecha_mes(df):
    return pd.to_datetime(dict(year=df["anio"], month=df["mes"], day=1))


def texto_contraste(rgb):
    r, g, b = [c if c > 0.03928 else c / 12.92 for c in rgb]
    r, g, b = [((c + 0.055) / 1.055) ** 2.4 if c > 0.03928 else c for c in (r, g, b)]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    # Elige el texto con más contraste (WCAG) entre blanco e INK (#191919, luminancia ~0.0097).
    return "#ffffff" if (1.05 / (lum + 0.05)) >= ((lum + 0.05) / 0.0597) else INK


def etiqueta_barras_v(ax, bars, fmt="{:.1f}", dy=0.0, size=8):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + dy, fmt.format(b.get_height()),
                ha="center", va="bottom", fontsize=size, color=INK)


def apilado_100(ax, df, idx, cols, colores, etiquetas, minimo=4.0, gap=0.35, ancho=0.72):
    """Barras verticales apiladas al 100 % con separador de superficie entre segmentos."""
    base = np.zeros(len(df))
    for c, col, et in zip(cols, colores, etiquetas):
        vals = df[c].to_numpy(dtype=float)
        ax.bar(idx, vals, bottom=base, width=ancho, color=col, edgecolor="white", linewidth=gap, label=et)
        for x, v, b0 in zip(idx, vals, base):
            if v >= minimo:
                ax.text(x, b0 + v / 2, f"{v:.0f}" if v >= 10 else f"{v:.1f}", ha="center", va="center",
                        fontsize=7.5, color=texto_contraste(to_rgb(col)))
        base += vals
    ax.set_ylim(0, 100)
    ax.set_ylabel("%")
    ax.grid(axis="x", visible=False)


# ------------------------------------------------------------------- figuras
def f01_vuelos_mes(res):
    d = leer(res, "01_calidad_1.1")
    d["f"] = fecha_mes(d)
    fig, ax = fig_base()
    sombrear_covid(ax)
    ax.plot(d["f"], d["vuelos_programados"] / 1e3, color=BLUE, lw=2)
    ax.set_ylabel("Vuelos programados por mes (miles)")
    ax.set_ylim(0, None)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    y17 = d[d.anio == 2017]["vuelos_programados"].mean() / 1e3
    y18 = d[d.anio == 2018]["vuelos_programados"].mean() / 1e3
    ax.annotate("2018: salto de +1.53 M de vuelos al año.\nSeis aerolíneas nuevas en los datos\n"
                "(G4, YX, OH, 9E, MQ, YV) explican el 94.5 %.\nNo es crecimiento del tráfico.",
                xy=(pd.Timestamp("2018-01-01"), (y17 + y18) / 2 + 5), xytext=(pd.Timestamp("2013-06-01"), 90),
                fontsize=9, color=INK, arrowprops=dict(arrowstyle="->", color=INK2),
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#bbbbbb"))
    ax.text(pd.Timestamp("2020-06-15"), 20, "COVID", ha="center", fontsize=9, color=INK2)
    titulos(fig, "Vuelos programados por mes, 2010-2020",
            "Universo: todos los vuelos programados de BTS (67.2 M en 132 meses). Sin meses faltantes.")
    layout(fig)
    guardar(fig, "F01_vuelos_programados_mes.png", NOTA_COVID + ".")


def f02_pct_a_tiempo_mes(res):
    d = leer(res, "04_estacionalidad_4.1")
    d["f"] = fecha_mes(d)
    fig, ax = fig_base()
    sombrear_covid(ax)
    ax.plot(d["f"], d["pct_a_tiempo_sobre_operados"], color=BLUE, lw=2)
    ax.set_ylabel("% a tiempo sobre vuelos operados")
    ax.set_ylim(60, 100)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    pre = d[d.f < COVID_INI]
    for _, r in [(0, pre.loc[pre.pct_a_tiempo_sobre_operados.idxmin()])]:
        ax.annotate(f"Mín. pre-COVID: {r.pct_a_tiempo_sobre_operados:.1f} %\n({r.f:%Y-%m}, vórtice polar)",
                    xy=(r.f, r.pct_a_tiempo_sobre_operados), xytext=(pd.Timestamp("2011-09-01"), 64),
                    fontsize=9, arrowprops=dict(arrowstyle="->", color=INK2))
    ax.text(pd.Timestamp("2020-06-15"), 62, "COVID", ha="center", fontsize=9, color=INK2)
    titulos(fig, "Puntualidad mensual, 2010-2020",
            "% a tiempo sobre vuelos operados (a tiempo = llegada con menos de 15 min de retraso)")
    layout(fig)
    guardar(fig, "F02_pct_a_tiempo_mes.png", NOTA_COVID + ".")


def f03_estados_por_anio(res):
    d = pd.read_csv(MART_DIARIA, usecols=["anio", "vuelos_programados", "vuelos_cancelados", "vuelos_desviados",
                                          "vuelos_operados", "vuelos_a_tiempo"])
    a = d.groupby("anio").sum()
    p = a["vuelos_programados"]
    est = pd.DataFrame({
        "A tiempo (< 15 min)": 100 * a["vuelos_a_tiempo"] / p,
        "Retrasado (>= 15 min)": 100 * (a["vuelos_operados"] - a["vuelos_a_tiempo"]) / p,
        "Cancelado": 100 * a["vuelos_cancelados"] / p,
        "Desviado": 100 * a["vuelos_desviados"] / p,
    })
    fig, ax = fig_base()
    x = np.arange(len(est))
    apilado_100(ax, est, x, list(est.columns), [BLUE, ORANGE, RED, VIOLET], list(est.columns), minimo=3.0)
    ax.set_xticks(x, est.index.astype(str))
    ax.set_ylabel("% de los vuelos programados")
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.07))
    ax.text(x[-1], 101.5, "COVID", ha="center", fontsize=8, color=INK2)
    titulos(fig, "Estado de los vuelos por año, 2010-2020",
            "100 % = vuelos programados (retrasado = operados - a tiempo; incluye 352 operados sin dato)")
    layout(fig, bottom=0.17)
    guardar(fig, "F03_estados_vuelo_anio.png", "2020 incluye marzo-diciembre con COVID. Cancelados y desviados < 2 % en cada año antes de 2020.")


def f04_hist_retraso(res):
    d = leer(res, "07_programado_vs_real_7.5")
    x = np.arange(len(d))
    col = [BLUE if s < 15 else ORANGE for s in d["cubeta_inicio_min"]]
    fig, ax = fig_base()
    ax.bar(x, d["pct_sobre_operados"], color=col, width=0.8)
    etiq = [f"{int(v)}" for v in d["cubeta_inicio_min"]]
    etiq[0], etiq[-1] = "< -45", "≥ 240"
    ax.set_xticks(x, etiq, rotation=60, fontsize=8)
    ax.set_xlabel("Retraso de llegada (minutos, cubetas de 15 min; negativo = llegó antes)")
    ax.set_ylabel("% de los vuelos operados")
    ax.grid(axis="x", visible=False)
    u = int(np.where(d["cubeta_inicio_min"] == 15)[0][0]) - 0.5
    ax.axvline(u, color=INK, ls="--", lw=1.2)
    a_t = d.loc[d.cubeta_inicio_min < 15, "pct_sobre_operados"].sum()
    ax.text(u + 0.3, 33, f"Umbral: 15 min\nA tiempo (izq.): {a_t:.1f} %\nRetrasado (der.): {100 - a_t:.1f} %",
            fontsize=9, va="top")
    ax.legend(handles=[Patch(color=BLUE, label="A tiempo (< 15 min)"), Patch(color=ORANGE, label="Retrasado (>= 15 min)")],
              loc="upper right")
    titulos(fig, "Distribución del retraso de llegada, 2010-2020",
            "% sobre vuelos operados con retraso de llegada informado (65.8 M). Mediana: -5 min")
    layout(fig, bottom=0.17)
    guardar(fig, "F04_histograma_retraso_llegada.png",
            "Primera cubeta agrupa retrasos < -45 min (llegadas muy adelantadas); la última agrupa >= 240 min (0.40 %).")


def f05_categorias_retraso(res):
    d = leer(res, "07_programado_vs_real_7.6")
    orden = ["Sin retraso", "Leve", "Moderado", "Severo", "Extremo"]
    p = d.pivot(index="anio", columns="categoria_retraso", values="pct_sobre_operados_del_anio")[orden]
    cols = [SEQ[0], SEQ[2], SEQ[4], SEQ[5], SEQ[6]]
    cols[0] = "#b6d5f8"
    fig, ax = fig_base()
    x = np.arange(len(p))
    apilado_100(ax, p, x, orden, ["#b6d5f8", "#6aabf1", "#2370cd", "#f47230", "#ec4647"], orden, minimo=2.5)
    ax.set_xticks(x, p.index.astype(str))
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.07))
    ax.text(x[-1], 101.5, "COVID", ha="center", fontsize=8, color=INK2)
    ext = p.loc[2010, "Extremo"], p.loc[2019, "Extremo"]
    titulos(fig, "Categorías de retraso de llegada por año",
            "100 % = vuelos operados del año. Sin retraso = llegada con <= 0 min de retraso (no es el KPI de puntualidad)")
    layout(fig, bottom=0.17, top=0.82)
    guardar(fig, "F05_categorias_retraso_anio.png",
            f"Extremo: {ext[0]:.2f} % (2010) a {ext[1]:.2f} % (2019). Números = % del año; no se rotulan los < 2.5 %.")


def f06_por_hora(res):
    d = leer(res, "04_estacionalidad_4.5")
    h = d["bloque_id"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw=dict(hspace=0.12))
    a1.plot(h, d["pct_a_tiempo_sobre_operados"], color=BLUE, lw=2, marker="o", ms=5)
    a1.set_ylabel("% a tiempo\nsobre operados")
    a1.set_ylim(65, 100)
    mx, mn = d.loc[d.pct_a_tiempo_sobre_operados.idxmax()], d.loc[d.pct_a_tiempo_sobre_operados.idxmin()]
    a1.annotate(f"{mx.pct_a_tiempo_sobre_operados:.1f} % ({int(mx.bloque_id):02d}:00)", (mx.bloque_id, mx.pct_a_tiempo_sobre_operados),
                xytext=(7.5, 94), fontsize=9, arrowprops=dict(arrowstyle="->", color=INK2))
    a1.annotate(f"{mn.pct_a_tiempo_sobre_operados:.1f} % ({int(mn.bloque_id):02d}:00)", (mn.bloque_id, mn.pct_a_tiempo_sobre_operados),
                xytext=(19.5, 70), fontsize=9, arrowprops=dict(arrowstyle="->", color=INK2))
    a2.bar(h, d["pct_cancelados_sobre_programados"], color=ORANGE, width=0.7)
    a2.set_ylabel("% cancelados\nsobre programados")
    a2.set_xticks(h, [f"{i:02d}" for i in h])
    a2.set_xlabel("Hora de salida programada (inicio del bloque horario)")
    a2.grid(axis="x", visible=False)
    for a, t in ((a1, "Puntualidad"), (a2, "Cancelación")):
        a.set_title(t, loc="left", fontsize=10, color=INK2)
    titulos(fig, "Puntualidad y cancelación por hora de salida programada",
            "Periodo 2010-01 a 2020-02. % a tiempo sobre vuelos operados; % cancelados sobre vuelos programados")
    fig.subplots_adjust(top=0.85, bottom=0.09, left=0.1, right=0.97)
    guardar(fig, "F06_puntualidad_cancelacion_hora.png", "Horas de 00 a 03 tienen muy pocos vuelos.")


def f07_mapa_calor(res):
    d = leer(res, "04_estacionalidad_4.6")
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    fr = ["Madrugada", "Mañana", "Tarde", "Noche"]
    p = d.pivot(index="nombre_dia", columns="franja", values="pct_a_tiempo_sobre_operados").loc[dias, fr]
    fig, ax = fig_base(h=5.8, w=9)
    ax.grid(False)
    vmin, vmax = p.values.min(), p.values.max()
    im = ax.imshow(p.values, cmap=SEQ_CMAP, vmin=vmin, vmax=vmax, aspect="auto")
    for i in range(len(dias)):
        for j in range(len(fr)):
            v = p.values[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=11,
                    color=texto_contraste(to_rgb(SEQ_CMAP((v - vmin) / (vmax - vmin)))))
    ax.set_xticks(range(len(fr)), fr)
    ax.set_yticks(range(len(dias)), dias)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.05)
    cb.set_label("% a tiempo sobre operados")
    cb.outline.set_visible(False)
    titulos(fig, "Puntualidad por día de la semana y franja horaria",
            "% a tiempo sobre vuelos operados, 2010-01 a 2020-02. Más oscuro = más puntual")
    layout(fig, left=0.14, right=0.95, top=0.84)
    guardar(fig, "F07_mapa_calor_dia_franja.png", "Franjas por hora de salida programada: Madrugada, Mañana, Tarde, Noche.")


def f08_mes_del_anio(res):
    d = leer(res, "04_estacionalidad_4.2")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw=dict(hspace=0.12))
    x = d["mes"]
    a1.plot(x, d["pct_a_tiempo_sobre_operados"], color=BLUE, lw=2, marker="o", ms=6)
    for xi, v in zip(x, d["pct_a_tiempo_sobre_operados"]):
        a1.text(xi, v + 0.5, f"{v:.1f}", ha="center", fontsize=8)
    a1.set_ylabel("% a tiempo\nsobre operados")
    a1.set_ylim(74, 88)
    a2.bar(x, d["pct_cancelados_sobre_programados"], color=ORANGE, width=0.7)
    for xi, v in zip(x, d["pct_cancelados_sobre_programados"]):
        a2.text(xi, v + 0.05, f"{v:.2f}", ha="center", fontsize=8)
    a2.set_ylabel("% cancelados\nsobre programados")
    a2.set_ylim(0, 3.4)
    a2.set_xticks(x, [m[:3] for m in d["nombre_mes"]])
    a2.set_xlabel("Mes del año")
    a2.grid(axis="x", visible=False)
    a1.set_title("Puntualidad", loc="left", fontsize=10, color=INK2)
    a2.set_title("Cancelación", loc="left", fontsize=10, color=INK2)
    titulos(fig, "Puntualidad y cancelación por mes del año (antes de COVID)",
            "Periodo 2010-01 a 2020-02. % a tiempo sobre vuelos operados; % cancelados sobre vuelos programados")
    fig.subplots_adjust(top=0.85, bottom=0.09, left=0.1, right=0.97)
    guardar(fig, "F08_estacionalidad_mes_anio.png", "El eje de puntualidad no parte de cero; el de cancelación sí.")


def f09_causas_retraso(res):
    d = leer(res, "05_causas_retraso_clima_5.2")
    orden = [("pct_avion_tardio_sobre_min_retraso_15", "Avión tardío", BLUE),
             ("pct_aerolinea_sobre_min_retraso_15", "Aerolínea", ORANGE),
             ("pct_nas_sobre_min_retraso_15", "Sistema (NAS)", AQUA),
             ("pct_clima_sobre_min_retraso_15", "Clima", YELLOW),
             ("pct_seguridad_sobre_min_retraso_15", "Seguridad", MAGENTA)]
    fig, ax = fig_base()
    x = np.arange(len(d))
    apilado_100(ax, d, x, [c for c, _, _ in orden], [c for _, _, c in orden], [n for _, n, _ in orden], minimo=3.5)
    ax.set_xticks(x, d["anio"].astype(str))
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.07))
    ax.text(x[-1], 101.5, "COVID", ha="center", fontsize=8, color=INK2)
    titulos(fig, "Causas del retraso por año, participación en los minutos de retraso",
            "100 % = minutos de retraso de vuelos operados con retraso de llegada >= 15 min")
    layout(fig, bottom=0.17)
    guardar(fig, "F09_causas_retraso_anio.png",
            "Clima = solo clima extremo (piso, no el efecto total). Seguridad ~0.1 % no se rotula.")


def f10_causas_cancelacion(res):
    d = leer(res, "06_cancelaciones_6.2")
    p = d.pivot(index="anio", columns="causa", values="pct_causa_sobre_cancelados_del_anio").fillna(0)
    orden = [("Clima", BLUE), ("Aerolínea", ORANGE), ("Sistema Nacional de Aviación (NAS)", AQUA), ("Seguridad", MAGENTA)]
    fig, ax = fig_base()
    x = np.arange(len(p))
    apilado_100(ax, p, x, [c for c, _ in orden], [k for _, k in orden],
                ["Clima", "Aerolínea", "Sistema (NAS)", "Seguridad (código D)"], minimo=4.0)
    ax.set_xticks(x, p.index.astype(str))
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.07))
    ax.annotate("2020: 84 % lleva código D (seguridad)\npor la pandemia, no por incidentes\nde seguridad. Excluir de análisis de causas.",
                xy=(x[-1], 60), xytext=(3.2, 108), fontsize=9, annotation_clip=False,
                arrowprops=dict(arrowstyle="->", color=INK2),
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbbbbb"))
    titulos(fig, "Causas de cancelación por año",
            "100 % = vuelos cancelados del año (código de cancelación de BTS)")
    layout(fig, bottom=0.17, top=0.72)
    guardar(fig, "F10_causas_cancelacion_anio.png", "Seguridad < 0.4 % en 2010-2019 (no se rotula).")


def _nombre_aerolinea(n):
    n = re.sub(r" \(.*?\)", "", n)
    for suf in (" Airlines", " Airline", " Air Lines", " Inc."):
        n = n.replace(suf, "")
    return n


def f11_ranking_aerolineas_2019(res):
    p = leer(res, "02_puntualidad_aerolineas_2.2")
    p = p[p.anio == 2019]
    t = leer(res, "02_puntualidad_aerolineas_2.1")[["tipo", "codigo", "nombre"]]
    d = p.merge(t, on="codigo", how="left")
    tipos = [("tradicional", "Tradicional"), ("bajo costo", "Bajo costo"), ("regional", "Regional")]
    cnt = [int((d.tipo == k).sum()) for k, _ in tipos]
    fig, axs = plt.subplots(3, 1, figsize=(10, 8.2), sharex=True, gridspec_kw=dict(height_ratios=cnt, hspace=0.35))
    # Puntos (no barras): el eje no parte de 0 y una barra truncada exagera las diferencias.
    for ax, (k, nom) in zip(axs, tipos):
        s_ = d[d.tipo == k].sort_values("pct_a_tiempo_sobre_operados")
        s = s_
        y = np.arange(len(s))
        ax.hlines(y, 70, s["pct_a_tiempo_sobre_operados"], color="#dddddd", lw=1)
        ax.scatter(s["pct_a_tiempo_sobre_operados"], y, color=BLUE, s=60, zorder=3)
        ax.set_yticks(y, [f"{_nombre_aerolinea(n)} ({c})" for n, c in zip(s_["nombre"], s_["codigo"])], fontsize=9)
        for yi, v in zip(y, s["pct_a_tiempo_sobre_operados"]):
            ax.text(v + 0.45, yi, f"{v:.1f}", va="center", fontsize=9)
        ax.set_title(nom, loc="left", fontsize=10, fontweight="bold", color=INK2)
        ax.grid(axis="y", visible=False)
        ax.set_xlim(70, 91)
    axs[-1].set_xlabel("% a tiempo sobre vuelos operados (2019)")
    titulos(fig, "Puntualidad 2019 por aerolínea, según tipo",
            "% a tiempo sobre vuelos operados, año 2019 (último año normal). El eje empieza en 70 %")
    fig.subplots_adjust(top=0.86, bottom=0.08, left=0.2, right=0.95)
    guardar(fig, "F11_ranking_aerolineas_2019.png", "Tipo según dim_airline.tipo.")


def _corto(nombre):
    for s in (" International Airport", " International", " Airport", " Intl", " Regional", " Metropolitan"):
        nombre = nombre.replace(s, "")
    return nombre


def f12_aeropuertos_top30(res):
    d = leer(res, "03_aeropuertos_3.3").sort_values("pct_salida_retrasada_15_sobre_operados")
    fig, ax = plt.subplots(figsize=(10, 9))
    y = np.arange(len(d))
    ax.barh(y, d["pct_salida_retrasada_15_sobre_operados"], color=BLUE, height=0.68)
    ax.set_yticks(y, [f"{c}  {_corto(n)[:28]}" for c, n in zip(d.codigo_iata, d.nombre)], fontsize=8.5)
    for yi, v in zip(y, d["pct_salida_retrasada_15_sobre_operados"]):
        ax.text(v + 0.2, yi, f"{v:.1f}", va="center", fontsize=8.5,
                bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none", alpha=0.85))
    ax.axvline(17.64, color=ORANGE, lw=1.8, ls="--")
    ax.text(17.84, -1.35, "Global 17.64 %", color="#b5470f", fontsize=9, va="center")
    ax.set_xlabel("% de salidas retrasadas >= 15 min, sobre vuelos operados desde el aeropuerto")
    ax.set_ylim(-1.8, len(d) - 0.4)
    ax.grid(axis="y", visible=False)
    titulos(fig, "Los 30 aeropuertos más grandes: salidas retrasadas",
            "% de salidas con retraso >= 15 min sobre vuelos operados, 2010-2020 (30 mayores por volumen, 65.8 % de los vuelos)")
    fig.subplots_adjust(top=0.90, bottom=0.08, left=0.27, right=0.96)
    guardar(fig, "F12_aeropuertos_top30_salidas_retrasadas.png", "Línea punteada: promedio de todos los aeropuertos (KPI-4).")


# Posicion aproximada (columna, fila) de cada estado en la cuadricula.
TILES = {
    "AK": (0, 0), "ME": (11, 0), "VT": (10, 1), "NH": (11, 1),
    "WA": (1, 2), "ID": (2, 2), "MT": (3, 2), "ND": (4, 2), "MN": (5, 2), "IL": (6, 2), "WI": (7, 2),
    "MI": (8, 2), "NY": (9, 2), "RI": (10, 2), "MA": (11, 2),
    "OR": (1, 3), "NV": (2, 3), "WY": (3, 3), "SD": (4, 3), "IA": (5, 3), "IN": (6, 3), "OH": (7, 3),
    "PA": (8, 3), "NJ": (9, 3), "CT": (10, 3),
    "CA": (1, 4), "UT": (2, 4), "CO": (3, 4), "NE": (4, 4), "MO": (5, 4), "KY": (6, 4), "WV": (7, 4),
    "VA": (8, 4), "MD": (9, 4), "DE": (10, 4),
    "AZ": (2, 5), "NM": (3, 5), "KS": (4, 5), "AR": (5, 5), "TN": (6, 5), "NC": (7, 5), "SC": (8, 5), "DC": (9, 5),
    "OK": (4, 6), "LA": (5, 6), "MS": (6, 6), "AL": (7, 6), "GA": (8, 6),
    "HI": (0, 7), "TT": (1, 7), "TX": (4, 7), "FL": (9, 7), "PR": (10, 7), "VI": (11, 7),
}


def f13_mapa_estados(res):
    d = leer(res, "03_aeropuertos_3.5").set_index("estado")["pct_salida_retrasada_15_sobre_operados"]
    vmin, vmax = d.min(), d.max()
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.grid(False)
    for e, (c, r) in TILES.items():
        if e in d.index:
            v = d[e]
            col = SEQ_CMAP((v - vmin) / (vmax - vmin))
            txt = texto_contraste(to_rgb(col))
            ax.add_patch(Rectangle((c, -r), 0.94, 0.94, color=col, lw=0))
            ax.text(c + 0.47, -r + 0.58, e, ha="center", va="center", fontsize=10, fontweight="bold", color=txt)
            ax.text(c + 0.47, -r + 0.25, f"{v:.1f}", ha="center", va="center", fontsize=8, color=txt)
        else:
            ax.add_patch(Rectangle((c, -r), 0.94, 0.94, color="#e6e6e6", lw=0))
            ax.text(c + 0.47, -r + 0.47, e, ha="center", va="center", fontsize=10, color="#888888")
    ax.set_xlim(-0.3, 12.2)
    ax.set_ylim(-7.3, 1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    sm = plt.cm.ScalarMappable(cmap=SEQ_CMAP, norm=plt.Normalize(vmin, vmax))
    cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.04, pad=0.03, shrink=0.55)
    cb.set_label("% de salidas retrasadas >= 15 min sobre operados (cuadro: estado y valor)")
    cb.outline.set_visible(False)
    titulos(fig, "Salidas retrasadas por estado de origen",
            "% de salidas con retraso >= 15 min sobre vuelos operados, 2010-2020. Más oscuro = más retrasos")
    fig.subplots_adjust(top=0.88, bottom=0.14, left=0.03, right=0.97)
    guardar(fig, "F13_mapa_estados_salidas_retrasadas.png",
            "Mapa de cuadros (posición aproximada). Gris: DC (sus aeropuertos figuran en VA) y DE (menos de 5,000 operados, mínimo de la consulta 3.5). TT: territorios del Pacífico (Guam, Saipán) en la fuente.")


def f14_covid_semanal(res):
    d = leer(res, "08_covid_2020_8.3")
    d = d[d.semana_iso <= 52]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw=dict(hspace=0.14))
    for a in (a1, a2):
        a.axvspan(9.86, 52.5, color=COVID_C, alpha=0.55, lw=0, zorder=0)
    a1.plot(d["semana_iso"], d["vuelos_2020_como_pct_de_2019"], color=BLUE, lw=2)
    a1.axhline(100, color=INK2, lw=0.8, ls=":")
    a1.set_ylabel("Vuelos 2020 como %\ndel volumen de 2019")
    a1.set_ylim(0, 125)
    mn = d.loc[d.vuelos_2020_como_pct_de_2019.idxmin()]
    a1.annotate(f"Mínimo: sem. {int(mn.semana_iso)}, {mn.vuelos_2020_como_pct_de_2019:.1f} %",
                (mn.semana_iso, mn.vuelos_2020_como_pct_de_2019), xytext=(26, 8), fontsize=9,
                arrowprops=dict(arrowstyle="->", color=INK2))
    a2.plot(d["semana_iso"], d["pct_cancelados_sobre_programados_2020"], color=ORANGE, lw=2)
    a2.set_ylabel("% cancelados sobre\nprogramados 2020")
    a2.set_xlabel("Semana ISO de 2020")
    a2.set_ylim(0, None)
    a1.set_title("Volumen programado (100 = misma semana de 2019)", loc="left", fontsize=10, color=INK2)
    a2.set_title("Cancelación (sobre vuelos programados de la semana)", loc="left", fontsize=10, color=INK2)
    a1.text(10.5, 112, "COVID (desde 2020-03-01)", fontsize=9, color=INK2)
    titulos(fig, "COVID-19: volumen y cancelaciones por semana, 2020",
            "Volumen: vuelos programados 2020 / 2019 por semana ISO. Cancelados: % sobre vuelos programados")
    fig.subplots_adjust(top=0.85, bottom=0.09, left=0.1, right=0.97)
    guardar(fig, "F14_covid_semanal.png", "Se omite la semana 53 (incompleta, sin par en 2019).")


def f15_covid_franja(res):
    d = leer(res, "08_covid_2020_8.7")
    fr = ["Madrugada", "Mañana", "Tarde", "Noche"]
    p = d.pivot(index="franja", columns="anio", values="pct_a_tiempo_sobre_operados").loc[fr]
    fig, ax = fig_base(h=5.4)
    x = np.arange(len(fr))
    w = 0.36
    b1 = ax.bar(x - w / 2, p[2019], w, color=BLUE, label="Mar-dic 2019", edgecolor="white", linewidth=1)
    b2 = ax.bar(x + w / 2, p[2020], w, color=ORANGE, label="Mar-dic 2020", edgecolor="white", linewidth=1)
    etiqueta_barras_v(ax, b1, dy=0.8, size=9)
    etiqueta_barras_v(ax, b2, dy=0.8, size=9)
    ax.set_xticks(x, fr)
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("% a tiempo sobre vuelos operados")
    ax.set_xlabel("Franja de salida programada")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper center", ncol=2)
    titulos(fig, "COVID: la puntualidad mejoró dentro de cada franja",
            "% a tiempo sobre vuelos operados, marzo-diciembre 2019 vs. marzo-diciembre 2020, por franja de salida")
    layout(fig, top=0.84, bottom=0.12)
    guardar(fig, "F15_covid_puntualidad_franja.png", "Noche: 74.24 % a 90.35 %; la mezcla de franjas también cambió, pero la mejora ocurre en todas.")


def f16_clima_mes(res):
    d = leer(res, "05_causas_retraso_clima_5.5")
    fig, ax = fig_base(h=5.2)
    b = ax.bar(d["mes"], d["min_clima_por_vuelo_operado"], color=BLUE, width=0.7)
    etiqueta_barras_v(ax, b, fmt="{:.2f}", dy=0.01, size=9)
    ax.set_xticks(d["mes"], [m[:3] for m in d["nombre_mes"]])
    ax.set_ylabel("Minutos de retraso por clima\npor vuelo operado")
    ax.set_xlabel("Mes del año")
    ax.set_ylim(0, d["min_clima_por_vuelo_operado"].max() * 1.15)
    ax.grid(axis="x", visible=False)
    titulos(fig, "Retraso por clima según el mes del año",
            "Minutos de retraso por clima extremo / vuelos operados, 2010-2020 (todos los operados en el denominador)")
    layout(fig, top=0.84)
    guardar(fig, "F16_clima_por_mes.png", "Incluye 2020. El clima no extremo se registra como NAS, así que son valores mínimos.")


FIGURAS = [f01_vuelos_mes, f02_pct_a_tiempo_mes, f03_estados_por_anio, f04_hist_retraso, f05_categorias_retraso,
           f06_por_hora, f07_mapa_calor, f08_mes_del_anio, f09_causas_retraso, f10_causas_cancelacion,
           f11_ranking_aerolineas_2019, f12_aeropuertos_top30, f13_mapa_estados, f14_covid_semanal,
           f15_covid_franja, f16_clima_mes]


# Las anotaciones de texto de algunas figuras citan cifras de esta corrida (sql/analisis/resultados/).
CORRIDA_REFERENCIA = "20261127_completo"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    res = Path(sys.argv[1])
    if not res.is_absolute():
        res = ROOT / res
    if res.name != CORRIDA_REFERENCIA:
        print(f"AVISO: varias anotaciones (global 17.64 %, 84 % código D, vórtice polar, mediana -5 min, "
              f"74.24 % a 90.35 %) están escritas para {CORRIDA_REFERENCIA}; con {res.name} pueden no coincidir.")
    for f in FIGURAS:
        f(res)


if __name__ == "__main__":
    main()
