"""Modelos de las preguntas 24 (retraso de llegada >= 15 min) y 25 (cancelación).

Uso (desde la raíz del repo, con la muestra ya extraída por modelos/extraer_muestra.py):
    .venv/bin/python modelos/entrenar.py --datos data/modelos --pregunta 24 25
Opciones: --particion A|B (por defecto B), --rapido (menos filas y árboles, para probar),
          --salida modelos/resultados.

Para cada pregunta: 2 líneas base (clase mayoritaria y regla de tasa histórica) y los modelos
(24: regresión logística, bosque aleatorio, gradient boosting; 25: logística y gradient boosting).
Los hiperparámetros y el umbral se eligen en validación (AUC-PR y F1); la prueba se evalúa una vez.
Escribe metricas_pNN.csv, figuras PNG y resumen_pNN.md en la carpeta de salida.
"""
import argparse

import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import comun as C

SEMILLA = 2026
# Paleta (guía dataviz, modo claro): categórica en orden fijo; gris para líneas base.
COLORES = {"Regla (línea base)": "#666666", "Regresión logística": "#257de0",
           "Bosque aleatorio": "#f47230", "Gradient boosting": "#00b894"}
TEXTO, TEXTO_2 = "#191919", "#666666"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#bbbbbb", "axes.labelcolor": TEXTO,
                     "xtick.color": TEXTO_2, "ytick.color": TEXTO_2, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 100, "savefig.dpi": 170,
                     "savefig.bbox": "tight"})
FUENTE = "Fuente: BTS 2010-2020, muestra de dw.fact_flights; cálculo propio."

# Variables de la logística: categorías de baja cardinalidad en one-hot; el resto escalado.
LR_ONEHOT = ["aerolinea", "tipo_aerolinea", "estado_origen", "estado_destino",
             "mes", "dia_semana", "hora_salida", "hora_llegada"]


# ---------------------------------------------------------------------------- modelos
def construir_logistica(c_reg):
    escalar = [v for v in C.NUMERICAS + list(C.CLAVES_TASA) if v not in LR_ONEHOT]
    ct = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=500), LR_ONEHOT),
        ("num", StandardScaler(), escalar),
    ])
    return make_pipeline(ct, LogisticRegression(C=c_reg, class_weight="balanced", max_iter=300))


def a_texto(x: pd.DataFrame) -> pd.DataFrame:
    """La logística usa one-hot sobre texto; origen/destino entran solo por sus tasas históricas."""
    x = x.copy()
    for c in LR_ONEHOT:
        x[c] = x[c].astype(str)
    return x


def a_codigos(x: pd.DataFrame) -> pd.DataFrame:
    x = x.copy()
    for c in C.CATEGORICAS:
        x[c] = x[c].cat.codes
    return x


def candidatos(pregunta, rapido):
    """(nombre, configuración legible, fábrica del estimador, transformación de X, filas máx. de entrenamiento)."""
    n_arb = 40 if rapido else 150
    iters = 60 if rapido else 400
    peso = "balanced" if pregunta == 25 else None
    hgb = [
        ("Gradient boosting", f"hojas={h}, tasa={lr}",
         (lambda h=h, lr=lr: HistGradientBoostingClassifier(
             max_leaf_nodes=h, learning_rate=lr, max_iter=iters, early_stopping=True,
             validation_fraction=0.1, n_iter_no_change=20, class_weight=peso,
             categorical_features="from_dtype", random_state=SEMILLA)),
         lambda x: x, None)
        for h, lr in ([(31, 0.1)] if rapido else [(31, 0.1), (127, 0.1)])
    ]
    lr = [("Regresión logística", f"C={c}", (lambda c=c: construir_logistica(c)), a_texto, None)
          for c in ([1.0] if rapido else [0.1, 1.0])]
    rf = [("Bosque aleatorio", f"árboles={n_arb}, prof={p}, hoja_min=50",
           (lambda p=p: RandomForestClassifier(
               n_estimators=n_arb, max_depth=p, min_samples_leaf=50, max_features="sqrt",
               class_weight="balanced_subsample", n_jobs=-1, random_state=SEMILLA)),
           a_codigos, 100_000 if rapido else 600_000)
          for p in ([12] if rapido else [14, 20])]
    return lr + rf + hgb if pregunta == 24 else lr + hgb


# ---------------------------------------------------------------------------- flujo
def preparar(parts: C.Particiones, pregunta: int):
    tr, desc_tr = C.universo(parts.entrenamiento, pregunta)
    evals = {}
    descartes = {"entrenamiento": desc_tr}
    for p in [parts.validacion, parts.prueba, *parts.robustez]:
        d, n = C.universo(p.datos, pregunta)
        evals[p.nombre] = d
        descartes[p.nombre] = n
    prior = C.tasas_historicas(tr, list(evals.values()))
    prep = C.Preparador().ajustar(tr)
    return tr, evals, prep, prior, descartes


def entrenar_pregunta(df, pregunta, opcion, rapido, salida: Path):
    info = C.PREGUNTAS[pregunta]
    t0 = time.time()
    parts = C.particionar(df, opcion)
    tr, evals, prep, prior, descartes = preparar(parts, pregunta)
    nombre_val, nombre_test = parts.validacion.nombre, parts.prueba.nombre
    xtr = prep.transformar(tr)
    xs = {k: prep.transformar(v) for k, v in evals.items()}
    ys = {k: v["y"].to_numpy() for k, v in evals.items()}
    print(f"[p{pregunta}] entrenamiento {len(tr):,} filas (prevalencia {100 * prior:.2f} %)")

    puntajes = {}   # modelo -> {particion: probabilidades}
    filas_metricas, busqueda = [], []

    # Líneas base: mayoritaria (umbral inalcanzable) y regla de tasa histórica.
    puntajes["Clase mayoritaria"] = {k: np.full(len(v), prior) for k, v in ys.items()}
    regla = info["regla_base"]
    puntajes["Regla (línea base)"] = {k: xs[k][regla].to_numpy() for k in ys}
    umbrales = {"Clase mayoritaria": float("inf"),
                "Regla (línea base)": C.umbral_max_f1(ys[nombre_val], puntajes["Regla (línea base)"][nombre_val])}
    config = {"Clase mayoritaria": "predice siempre la clase negativa",
              "Regla (línea base)": f"{regla} (tasa histórica de entrenamiento) con umbral"}
    importancias = {}
    rng = np.random.default_rng(SEMILLA)

    for nombre, cfg, fabrica, tx, max_filas in candidatos(pregunta, rapido):
        idx = np.arange(len(xtr))
        if max_filas and len(idx) > max_filas:
            idx = rng.choice(idx, max_filas, replace=False)
        t1 = time.time()
        est = fabrica().fit(tx(xtr.iloc[idx]), tr["y"].to_numpy()[idx])
        p_val = est.predict_proba(tx(xs[nombre_val]))[:, 1]
        ap = average_precision_score(ys[nombre_val], p_val)
        busqueda.append({"modelo": nombre, "configuracion": cfg, "filas_entrenamiento": len(idx),
                         "auc_pr_validacion": ap, "segundos": round(time.time() - t1, 1)})
        print(f"[p{pregunta}] {nombre} ({cfg}): AUC-PR validación {ap:.4f} en {time.time() - t1:.0f} s")
        mejor = [b for b in busqueda if b["modelo"] == nombre]
        if ap >= max(b["auc_pr_validacion"] for b in mejor):
            puntajes[nombre] = {k: est.predict_proba(tx(v))[:, 1] for k, v in xs.items()}
            umbrales[nombre] = C.umbral_max_f1(ys[nombre_val], puntajes[nombre][nombre_val])
            config[nombre] = cfg
            importancias[nombre] = (est, tx)

    for modelo, ps in puntajes.items():
        for part, p in ps.items():
            m = C.metricas(ys[part], p, umbrales[modelo])
            filas_metricas.append({"pregunta": pregunta, "modelo": modelo, "particion": part,
                                   "configuracion": config[modelo], **m})
    met = pd.DataFrame(filas_metricas)
    modelos_reales = [m for m in puntajes if m not in ("Clase mayoritaria", "Regla (línea base)")]
    mejor = max(modelos_reales, key=lambda m: met[(met.modelo == m) & (met.particion == nombre_val)].auc_pr.iloc[0])

    # Subgrupos del mejor modelo en prueba: tipo de aerolínea y franja.
    sub = []
    for col in ["tipo_aerolinea", "franja"]:
        d = evals[nombre_test]
        for val, g in d.groupby(col):
            pos = d.index.get_indexer(g.index)
            m = C.metricas(ys[nombre_test][pos], puntajes[mejor][nombre_test][pos], umbrales[mejor])
            sub.append({"variable": col, "valor": val, **m})
    sub = pd.DataFrame(sub)

    # Importancia por permutación del mejor modelo (en validación, submuestra).
    est, tx = importancias[mejor]
    n_imp = min(len(xs[nombre_val]), 20_000 if rapido else 60_000)
    pos = rng.choice(len(xs[nombre_val]), n_imp, replace=False)
    imp = permutation_importance(est, tx(xs[nombre_val].iloc[pos]), ys[nombre_val][pos],
                                 scoring="average_precision", n_repeats=3, random_state=SEMILLA, n_jobs=1)
    imp = pd.DataFrame({"variable": xs[nombre_val].columns, "caida_auc_pr": imp.importances_mean,
                        "desv": imp.importances_std}).sort_values("caida_auc_pr", ascending=False)

    salida.mkdir(parents=True, exist_ok=True)
    pref = f"p{pregunta}"
    met.to_csv(salida / f"metricas_{pref}.csv", index=False)
    sub.to_csv(salida / f"subgrupos_{pref}.csv", index=False)
    imp.to_csv(salida / f"importancia_{pref}.csv", index=False)
    pd.DataFrame(busqueda).to_csv(salida / f"busqueda_{pref}.csv", index=False)

    figura_pr(pregunta, info, puntajes, ys, nombre_test, salida / f"{pref}_curvas_pr.png")
    figura_confusion(pregunta, info, ys, puntajes, umbrales, mejor, [nombre_test, *[p.nombre for p in parts.robustez]],
                     salida / f"{pref}_matriz_confusion.png")
    figura_importancia(pregunta, info, imp, mejor, salida / f"{pref}_importancia.png")
    figura_calibracion(pregunta, info, ys[nombre_test], puntajes[mejor][nombre_test], mejor,
                       salida / f"{pref}_calibracion.png")
    escribir_resumen(pregunta, info, parts, tr, prior, descartes, met, sub, imp, busqueda, mejor,
                     nombre_val, nombre_test, rapido, time.time() - t0, salida / f"resumen_{pref}.md")
    print(f"[p{pregunta}] listo en {time.time() - t0:.0f} s; mejor modelo en validación: {mejor}")


# ---------------------------------------------------------------------------- figuras
def _pie(fig):
    fig.text(0.01, -0.02, FUENTE, fontsize=8, color=TEXTO_2, ha="left")


def figura_pr(pregunta, info, puntajes, ys, part, ruta):
    fig, ax = plt.subplots(figsize=(7, 4.6))
    y = ys[part]
    for modelo, color in COLORES.items():
        if modelo not in puntajes:
            continue
        p, r, _ = precision_recall_curve(y, puntajes[modelo][part])
        ap = average_precision_score(y, puntajes[modelo][part])
        ax.plot(r, p, color=color, lw=2, label=f"{modelo} (AUC-PR {ap:.3f})")
    ax.axhline(y.mean(), color=TEXTO_2, lw=1, ls="--")
    ax.text(0.01, y.mean() - 0.015, f"azar = prevalencia {100 * y.mean():.1f} %", color=TEXTO_2,
            fontsize=8, ha="left", va="top")
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Recall (positivos detectados / positivos reales)",
           ylabel="Precisión (positivos reales / marcados)")
    ax.grid(color="#eeeeee", lw=0.8)
    ax.set_title(f"Pregunta {pregunta}: curvas precisión-recall, {part}\n"
                 f"Clase positiva: {info['nombre']}. Universo: {info['universo']}.",
                 loc="left", fontsize=11, color=TEXTO)
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    _pie(fig)
    fig.savefig(ruta)
    plt.close(fig)


def figura_confusion(pregunta, info, ys, puntajes, umbrales, mejor, partes, ruta):
    fig, axs = plt.subplots(1, len(partes), figsize=(3.8 * len(partes), 3.6), gridspec_kw={"wspace": 0.08})
    for i, (ax, part) in enumerate(zip(np.atleast_1d(axs), partes)):
        y, p = ys[part], puntajes[mejor][part]
        pred = (p >= umbrales[mejor]).astype(int)
        cm = np.array([[((y == a) & (pred == b)).sum() for b in (0, 1)] for a in (0, 1)])
        fila = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
        ax.imshow(fila, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("az", ["#ffffff", "#1b64be"]),
                  vmin=0, vmax=1)
        for a in (0, 1):
            for b in (0, 1):
                ax.text(b, a, f"{cm[a, b]:,}\n{100 * fila[a, b]:.1f} % de la fila", ha="center", va="center",
                        fontsize=8.5, color="#ffffff" if fila[a, b] > 0.55 else TEXTO)
        ax.set_xticks([0, 1], ["Predicho no", "Predicho sí"])
        ax.set_yticks([0, 1], ["Real no", "Real sí"] if i == 0 else ["", ""])
        ax.set_title(part, fontsize=10, color=TEXTO)
        for s in ax.spines.values():
            s.set_visible(False)
    fig.suptitle(f"Pregunta {pregunta}: matriz de confusión de {mejor} (umbral {umbrales[mejor]:.3f}, "
                 f"elegido en validación)\nClase positiva: {info['nombre']}. Universo: {info['universo']}.",
                 x=0.01, ha="left", fontsize=10.5, color=TEXTO, y=1.08)
    _pie(fig)
    fig.savefig(ruta)
    plt.close(fig)


def figura_importancia(pregunta, info, imp, mejor, ruta):
    d = imp.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 4.8))
    ax.barh(d.variable, d.caida_auc_pr, color="#257de0", height=0.6)
    ax.errorbar(d.caida_auc_pr, d.variable, xerr=d.desv, fmt="none", ecolor=TEXTO_2, lw=1)
    ax.set_xlabel("Caída del AUC-PR al desordenar la variable (validación)")
    ax.grid(axis="x", color="#eeeeee", lw=0.8)
    ax.set_title(f"Pregunta {pregunta}: importancia de variables de {mejor}\n"
                 f"Clase positiva: {info['nombre']}. Importancia por permutación.",
                 loc="left", fontsize=11, color=TEXTO)
    _pie(fig)
    fig.savefig(ruta)
    plt.close(fig)


def figura_calibracion(pregunta, info, y, p, mejor, ruta):
    fr, pm = calibration_curve(y, p, n_bins=10, strategy="quantile")
    fig, ax = plt.subplots(figsize=(5, 4.6))
    ax.plot([0, 1], [0, 1], color=TEXTO_2, lw=1, ls="--")
    ax.plot(pm, fr, color="#257de0", lw=2, marker="o", ms=5)
    lim = max(0.05, float(max(pm.max(), fr.max())) * 1.1)
    ax.set(xlim=(0, lim), ylim=(0, lim), xlabel="Probabilidad predicha (promedio del decil)",
           ylabel="Proporción real de positivos")
    ax.grid(color="#eeeeee", lw=0.8)
    ax.set_title(f"Pregunta {pregunta}: calibración de {mejor} (prueba)\n"
                 f"Diagonal = calibración perfecta.", loc="left", fontsize=11, color=TEXTO)
    _pie(fig)
    fig.savefig(ruta)
    plt.close(fig)


# ---------------------------------------------------------------------------- resumen
def _tabla(df, cols, fmt):
    filas = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        filas.append("| " + " | ".join(fmt.get(c, "{}").format(getattr(r, c)) for c in cols) + " |")
    return "\n".join(filas)


def escribir_resumen(pregunta, info, parts, tr, prior, descartes, met, sub, imp, busqueda, mejor,
                     nombre_val, nombre_test, rapido, segundos, ruta):
    f = {"prevalencia_pct": "{:.2f}", "accuracy": "{:.3f}", "precision": "{:.3f}", "recall": "{:.3f}",
         "f1": "{:.3f}", "f2": "{:.3f}", "auc_pr": "{:.3f}", "auc_roc": "{:.3f}", "umbral": "{:.3f}",
         "filas": "{:,}", "positivos": "{:,}", "vp": "{:,}", "fp": "{:,}", "fn": "{:,}", "vn": "{:,}",
         "auc_pr_validacion": "{:.4f}", "filas_entrenamiento": "{:,}", "caida_auc_pr": "{:.4f}", "desv": "{:.4f}"}
    cols = ["modelo", "umbral", "accuracy", "precision", "recall", "f1", "f2", "auc_pr", "auc_roc"]
    prev = met[met.modelo == "Clase mayoritaria"][["particion", "filas", "positivos", "prevalencia_pct"]]
    prev = pd.concat([pd.DataFrame([{"particion": "entrenamiento", "filas": len(tr),
                                     "positivos": int(tr.y.sum()), "prevalencia_pct": 100 * prior}]), prev])
    prev["descartadas_objetivo_nulo"] = prev.particion.map(descartes).fillna(0).astype(int)
    texto = [
        f"# Pregunta {pregunta}: {info['nombre']} — resultados{' (CORRIDA RÁPIDA DE PRUEBA)' if rapido else ''}",
        "",
        f"- **Clase positiva**: {info['nombre']}. **Universo**: {info['universo']}.",
        f"- **Partición** (opción {parts.opcion} de `docs/analisis/03_plan_modelos.md` §5): entrenamiento "
        f"{int(tr.anio.min())}-{int(tr.anio.max())} (muestra 5 %), {nombre_val}, {nombre_test}"
        + (" y 2020 como prueba de robustez (muestra 15 %)." if parts.opcion == "B" else "."),
        "- **Variables**: solo conocidas antes del despegue (§3) más tasas históricas calculadas solo con "
        "entrenamiento (fuera de pliegue por año en las filas de entrenamiento). Ninguna variable de §4.",
        "- Hiperparámetros y umbral (máximo F1) elegidos en **validación**; la prueba se evaluó una sola vez.",
        f"- **Mejor modelo en validación (AUC-PR)**: {mejor}.",
        f"- Tiempo total: {segundos / 60:.1f} min.",
        "",
        "## Prevalencia de cada partición",
        "",
        _tabla(prev, ["particion", "filas", "positivos", "prevalencia_pct", "descartadas_objetivo_nulo"], f),
        "",
        f"## Métricas en {nombre_test}",
        "",
        "Precisión = de los vuelos marcados como positivos, cuántos lo son. Recall = de los positivos reales, "
        "cuántos detecta. AUC-PR de un modelo al azar = prevalencia.",
        "",
        _tabla(met[met.particion == nombre_test], cols, f),
        "",
        f"## Métricas en {nombre_val} (selección)",
        "",
        _tabla(met[met.particion == nombre_val], cols, f),
        "",
    ]
    for p in parts.robustez:
        if p.nombre != nombre_test:
            texto += [f"## Robustez: {p.nombre} ({p.descripcion})", "",
                      _tabla(met[met.particion == p.nombre], cols, f), ""]
    texto += [
        "## Búsqueda de hiperparámetros (validación)", "",
        _tabla(pd.DataFrame(busqueda), ["modelo", "configuracion", "filas_entrenamiento", "auc_pr_validacion", "segundos"], f),
        "",
        f"## {mejor} por subgrupo ({nombre_test})", "",
        _tabla(sub, ["variable", "valor", "filas", "prevalencia_pct", "precision", "recall", "f1", "auc_pr"], f),
        "",
        f"## Importancia de variables de {mejor} (permutación, validación)", "",
        _tabla(imp.head(15), ["variable", "caida_auc_pr", "desv"], f),
        "",
        f"Figuras: `p{pregunta}_curvas_pr.png`, `p{pregunta}_matriz_confusion.png`, "
        f"`p{pregunta}_importancia.png`, `p{pregunta}_calibracion.png`.",
    ]
    ruta.write_text("\n".join(texto) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", default="data/modelos", help="carpeta con muestra_AAAA.parquet")
    ap.add_argument("--pregunta", type=int, nargs="+", default=[24, 25], choices=[24, 25])
    ap.add_argument("--particion", default="B", choices=["A", "B"])
    ap.add_argument("--salida", default="modelos/resultados")
    ap.add_argument("--rapido", action="store_true", help="menos filas y árboles (solo para probar)")
    a = ap.parse_args()
    df = C.cargar_muestra(Path(a.datos))
    print(f"muestra: {len(df):,} filas, años {df.anio.min()}-{df.anio.max()}")
    for q in a.pregunta:
        entrenar_pregunta(df, q, a.particion, a.rapido, Path(a.salida))


if __name__ == "__main__":
    main()
