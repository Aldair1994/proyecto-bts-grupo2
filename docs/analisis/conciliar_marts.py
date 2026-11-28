"""Concilia los resultados de sql/analisis/ (consultas sobre dw.fact_flights) con los CSV
exportados de las vistas mart (docs/mart_*.csv) que usa el dashboard.

Para cada KPI recalcula el valor desde las sumas del mart (como lo haría una medida DAX:
dividir sumas, nunca promediar porcentajes) y lo compara con el CSV de la consulta.

Uso (desde la raíz del repo):
    python3 docs/analisis/conciliar_marts.py sql/analisis/resultados/20261127_completo

Imprime una tabla Markdown (una fila por revisión) y termina con código 1 si alguna
revisión supera la tolerancia.
"""
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DOCS = RAIZ / "docs"
TOL_PP = 0.011      # puntos porcentuales: las consultas redondean a 2 decimales
TOL_CONTEO = 0      # los conteos deben ser idénticos


def cargar_resultados(carpeta: Path) -> dict:
    res = {}
    for f in carpeta.glob("*.csv"):
        clave = f.stem.rsplit("_", 1)[-1]  # p. ej. '2.1'
        res[clave] = pd.read_csv(f)
    return res


def pct(num, den):
    return 100.0 * num / den


filas = []


def revisar(nombre, esperado: pd.Series, mart: pd.Series, tol, unidad, nota=""):
    """Compara dos series alineadas por índice. Guarda una fila con la diferencia máxima.
    `nota` explica una diferencia conocida de universo (se imprime en la columna Detalle)."""
    a, b = esperado.align(mart, join="outer")
    faltan = int(a.isna().sum() + b.isna().sum())
    dif = (a - b).abs()
    maxdif = float(dif.max()) if len(dif.dropna()) else float("nan")
    peor = dif.idxmax() if len(dif.dropna()) else None
    ok = faltan == 0 and maxdif <= tol
    filas.append({
        "revision": nombre,
        "comparados": int(len(dif.dropna())),
        "sin_pareja": faltan,
        "dif_max": f"{maxdif:.4f} {unidad}",
        "peor_caso": (str(peor) if not ok else "") + (f" {nota}" if nota else ""),
        "resultado": "OK" if ok else "DIFERENCIA",
    })


def main(carpeta: str) -> int:
    r = cargar_resultados(Path(carpeta))
    pm = pd.read_csv(DOCS / "mart_puntualidad_mensual_aerolinea.csv")
    am = pd.read_csv(DOCS / "mart_aeropuerto_mensual.csv")
    ph = pd.read_csv(DOCS / "mart_patron_dia_hora.csv")
    sd = pd.read_csv(DOCS / "mart_serie_diaria.csv")
    ra = pd.read_csv(DOCS / "mart_rutas_anual.csv")
    precovid = lambda df: df[df["anio"] * 100 + df["mes"] <= 202002]

    # --- A. Conteos por año: 01/1.1 contra los cinco marts --------------------------------
    q = r["1.1"].groupby("anio")[["vuelos_programados", "cancelados", "desviados", "operados"]].sum()
    for nombre_mart, df, cols in [
        ("puntualidad_mensual_aerolinea", pm, ("vuelos_programados", "vuelos_cancelados", "vuelos_desviados", "vuelos_operados")),
        ("serie_diaria", sd, ("vuelos_programados", "vuelos_cancelados", "vuelos_desviados", "vuelos_operados")),
        ("aeropuerto_mensual (Origen)", am[am.rol == "Origen"], ("vuelos_programados", "vuelos_cancelados", "vuelos_desviados", "vuelos_operados")),
        ("aeropuerto_mensual (Destino)", am[am.rol == "Destino"], ("vuelos_programados", "vuelos_cancelados", "vuelos_desviados", "vuelos_operados")),
        ("patron_dia_hora", ph, ("vuelos_programados", "vuelos_cancelados", None, "vuelos_operados")),
        ("rutas_anual", ra, ("vuelos_programados", "vuelos_cancelados", None, "vuelos_operados")),
    ]:
        g = df.groupby("anio")
        for col_q, col_m in zip(["vuelos_programados", "cancelados", "desviados", "operados"], cols):
            if col_m is None:
                continue
            revisar(f"1.1 {col_q} por año vs {nombre_mart}", q[col_q], g[col_m].sum(), TOL_CONTEO, "vuelos")

    # --- B. Aerolíneas, periodo completo (02/2.1 y tipo) ----------------------------------
    g = pm.groupby("aerolinea_codigo")[["vuelos_programados", "vuelos_cancelados", "vuelos_operados", "vuelos_a_tiempo"]].sum()
    q = r["2.1"].set_index("codigo")
    revisar("2.1 vuelos operados por aerolínea", q.vuelos_operados, g.vuelos_operados, TOL_CONTEO, "vuelos")
    revisar("2.1 % a tiempo sobre operados por aerolínea", q.pct_a_tiempo_sobre_operados,
            pct(g.vuelos_a_tiempo, g.vuelos_operados), TOL_PP, "pp")
    revisar("2.1 % cancelados sobre programados por aerolínea", q.pct_cancelados_sobre_programados,
            pct(g.vuelos_cancelados, g.vuelos_programados), TOL_PP, "pp")
    tipos_mart = pm.groupby("aerolinea_codigo").tipo_aerolinea.first().str.lower()
    coinciden = (q.tipo == tipos_mart.reindex(q.index))
    filas.append({
        "revision": "tipo de aerolínea: CTE de 02 vs dim_airline.tipo del mart",
        "comparados": int(len(q)), "sin_pareja": int(tipos_mart.reindex(q.index).isna().sum()),
        "dif_max": f"{int((~coinciden).sum())} distintos",
        "peor_caso": ", ".join(f"{c}: {q.tipo[c]} vs {tipos_mart.get(c)}" for c in q.index[~coinciden]),
        "resultado": "OK" if coinciden.all() else "DIFERENCIA",
    })

    # --- C. Aerolínea x año (02/2.2) ------------------------------------------------------
    g = pm.groupby(["aerolinea_codigo", "anio"])[["vuelos_programados", "vuelos_cancelados", "vuelos_operados", "vuelos_a_tiempo"]].sum()
    q = r["2.2"].set_index(["codigo", "anio"])
    revisar("2.2 % a tiempo por aerolínea y año", q.pct_a_tiempo_sobre_operados,
            pct(g.vuelos_a_tiempo, g.vuelos_operados), TOL_PP, "pp")
    revisar("2.2 % cancelados por aerolínea y año", q.pct_cancelados_sobre_programados,
            pct(g.vuelos_cancelados, g.vuelos_programados), TOL_PP, "pp")

    # --- D. Categorías de retraso por aerolínea (02/2.4) ----------------------------------
    g = pm.groupby("aerolinea_codigo")[["cat_sin_retraso", "cat_leve", "cat_moderado", "cat_severo", "cat_extremo"]].sum()
    tot = g.sum(axis=1)
    q = r["2.4"].set_index("aerolinea")
    for cat, col in [("sin_retraso_0min", "cat_sin_retraso"), ("leve", "cat_leve"), ("extremo", "cat_extremo")]:
        revisar(f"2.4 % {cat} por aerolínea", q[f"pct_{cat}_sobre_operados"], pct(g[col], tot), TOL_PP, "pp")

    # --- E. Serie mensual (04/4.1, 08/8.1) contra serie_diaria ----------------------------
    g = sd.groupby(["anio", "mes"])[["vuelos_programados", "vuelos_cancelados", "vuelos_operados", "vuelos_a_tiempo"]].sum()
    q = r["4.1"].set_index(["anio", "mes"])
    revisar("4.1 % a tiempo por mes (serie_diaria)", q.pct_a_tiempo_sobre_operados,
            pct(g.vuelos_a_tiempo, g.vuelos_operados), TOL_PP, "pp")
    revisar("4.1 % cancelados por mes (serie_diaria)", q.pct_cancelados_sobre_programados,
            pct(g.vuelos_cancelados, g.vuelos_programados), TOL_PP, "pp")

    # --- F. Estacionalidad pre-COVID (04/4.2, 4.4, 4.5, 4.7, 4.8) -------------------------
    g = precovid(sd).groupby("mes")[["vuelos_operados", "vuelos_a_tiempo"]].sum()
    revisar("4.2 % a tiempo por mes del año, pre-COVID", r["4.2"].set_index("mes").pct_a_tiempo_sobre_operados,
            pct(g.vuelos_a_tiempo, g.vuelos_operados), TOL_PP, "pp")
    g = precovid(ph).groupby("dia_semana")[["vuelos_operados", "vuelos_a_tiempo"]].sum()
    revisar("4.4 % a tiempo por día de la semana (patron_dia_hora)", r["4.4"].set_index("dia_semana").pct_a_tiempo_sobre_operados,
            pct(g.vuelos_a_tiempo, g.vuelos_operados), TOL_PP, "pp")
    g = precovid(ph).groupby("bloque_id")[["vuelos_programados", "vuelos_cancelados", "vuelos_operados", "vuelos_a_tiempo"]].sum()
    q = r["4.5"].set_index("bloque_id")
    revisar("4.5 % a tiempo por hora de salida (patron_dia_hora)", q.pct_a_tiempo_sobre_operados,
            pct(g.vuelos_a_tiempo, g.vuelos_operados), TOL_PP, "pp")
    revisar("4.5 % cancelados por hora de salida (patron_dia_hora)", q.pct_cancelados_sobre_programados,
            pct(g.vuelos_cancelados, g.vuelos_programados), TOL_PP, "pp")
    s = precovid(sd).assign(es_feriado=lambda d: d.es_feriado.astype(str).str[0], es_fin_semana=lambda d: d.es_fin_semana.astype(str).str[0])
    g = s.groupby(["es_feriado", "es_fin_semana"])[["vuelos_operados", "vuelos_a_tiempo"]].sum()
    q = r["4.7"].assign(es_feriado=lambda d: d.es_feriado.astype(str).str[0], es_fin_semana=lambda d: d.es_fin_semana.astype(str).str[0])
    revisar("4.7 % a tiempo feriado x fin de semana", q.set_index(["es_feriado", "es_fin_semana"]).pct_a_tiempo_sobre_operados,
            pct(g.vuelos_a_tiempo, g.vuelos_operados), TOL_PP, "pp")
    g = precovid(sd).groupby("nombre_feriado")[["vuelos_operados", "vuelos_a_tiempo"]].sum()
    revisar("4.8 % a tiempo por feriado", r["4.8"].set_index("nombre_feriado").pct_a_tiempo_sobre_operados,
            pct(g.vuelos_a_tiempo, g.vuelos_operados), TOL_PP, "pp")

    # --- G. Aeropuertos (03/3.1, 3.2, 3.3, 3.5) contra aeropuerto_mensual -----------------
    o = am[am.rol == "Origen"].groupby("codigo_iata")[["vuelos_operados", "vuelos_retrasados_15", "n_con_dato_15", "vuelos_a_tiempo"]].sum()
    d = am[am.rol == "Destino"].groupby("codigo_iata")[["vuelos_operados", "vuelos_a_tiempo"]].sum()
    for clave in ["3.1", "3.3"]:
        q = r[clave].set_index("codigo_iata")
        revisar(f"{clave} % salida retrasada 15 por aeropuerto de origen", q.pct_salida_retrasada_15_sobre_operados,
                pct(o.vuelos_retrasados_15, o.n_con_dato_15).reindex(q.index), TOL_PP, "pp")
        revisar(f"{clave} vuelos operados por aeropuerto de origen", q.vuelos_operados,
                o.vuelos_operados.reindex(q.index), TOL_CONTEO, "vuelos")
    q = r["3.2"].set_index("codigo_iata")
    revisar("3.2 % a tiempo por aeropuerto de destino", q.pct_a_tiempo_sobre_operados,
            pct(d.vuelos_a_tiempo, d.vuelos_operados).reindex(q.index), TOL_PP, "pp")
    q = r["3.4"].set_index("codigo_iata")
    revisar("3.4 (mapa) % a tiempo desde origen, todos los aeropuertos", q.pct_a_tiempo_sobre_operados_desde_origen,
            pct(o.vuelos_a_tiempo, o.vuelos_operados).reindex(q.index), TOL_PP, "pp")
    e = am[am.rol == "Origen"].groupby("estado")[["vuelos_retrasados_15", "n_con_dato_15", "vuelos_operados", "vuelos_a_tiempo"]].sum()
    q = r["3.5"].set_index("estado")
    excluidos = ", ".join(f"{k} ({v} operados)" for k, v in e.vuelos_operados[~e.index.isin(q.index)].items())
    revisar("3.5 % salida retrasada 15 por estado", q.pct_salida_retrasada_15_sobre_operados,
            pct(e.vuelos_retrasados_15, e.n_con_dato_15).reindex(q.index), TOL_PP, "pp",
            nota=f"Fuera de 3.5 por el mínimo de 5000 operados: {excluidos}." if excluidos else "")

    # --- H. Rutas (03/3.7) contra rutas_anual ---------------------------------------------
    ra2 = ra.assign(ruta=ra.origen_iata + "-" + ra.destino_iata).groupby("ruta")[["vuelos_operados", "vuelos_a_tiempo"]].sum()
    q = r["3.7"].assign(ruta=lambda x: x.origen + "-" + x.destino).set_index("ruta")
    revisar("3.7 % a tiempo de las 30 peores rutas", q.pct_a_tiempo_sobre_operados,
            pct(ra2.vuelos_a_tiempo, ra2.vuelos_operados).reindex(q.index), TOL_PP, "pp")

    # --- I. Causas de retraso (05/5.2) y de cancelación (06/6.2) por año ------------------
    causas = ["min_causa_aerolinea", "min_causa_clima", "min_causa_nas", "min_causa_seguridad", "min_causa_avion_tardio"]
    g = pm.groupby("anio")[causas].sum()
    tot = g.sum(axis=1)
    q = r["5.2"].set_index("anio")
    # El mart suma minutos de causa de TODOS los vuelos; 5.2 solo de operados con retraso >= 15.
    # La diferencia (minutos de causa en vuelos desviados) es de centésimas: tolerancia 0.02 pp.
    for c in ["aerolinea", "clima", "nas", "avion_tardio"]:
        revisar(f"5.2 % minutos de causa {c} por año", q[f"pct_{c}_sobre_min_retraso_15"],
                pct(g[f"min_causa_{c}"], tot), 0.02, "pp",
                nota="Universo distinto: el mart incluye minutos de causa de vuelos desviados.")
    g = pm.groupby("anio")[["cancel_aerolinea", "cancel_clima", "cancel_nas", "cancel_seguridad"]].sum()
    q = r["6.2"].pivot(index="anio", columns="codigo_causa", values="cancelados")
    for cod, col in [("A", "cancel_aerolinea"), ("B", "cancel_clima"), ("C", "cancel_nas"), ("D", "cancel_seguridad")]:
        revisar(f"6.2 cancelados por causa {cod} y año", q[cod], g[col], TOL_CONTEO, "vuelos")

    # --- J. Coordenadas del mapa ------------------------------------------------------------
    sin = am.groupby("codigo_iata")[["latitud", "longitud"]].first()
    n_sin = int((sin.latitud.isna() | sin.longitud.isna()).sum())
    filas.append({
        "revision": "aeropuertos con latitud/longitud en mart.aeropuerto_mensual",
        "comparados": int(len(sin)), "sin_pareja": 0,
        "dif_max": f"{n_sin} sin coordenadas", "peor_caso": "",
        "resultado": "OK" if n_sin == 0 else "PENDIENTE",
    })

    tabla = pd.DataFrame(filas)
    print("| # | Revisión | Comparados | Sin pareja | Diferencia máx. | Resultado | Detalle |")
    print("|---|---|---:|---:|---:|---|---|")
    for i, f in enumerate(tabla.itertuples(), 1):
        print(f"| {i} | {f.revision} | {f.comparados} | {f.sin_pareja} | {f.dif_max} | {f.resultado} | {f.peor_caso} |")
    malas = tabla[tabla.resultado == "DIFERENCIA"]
    calculo = tabla[tabla.resultado != "PENDIENTE"]
    print(f"\n{len(calculo) - len(malas)} de {len(calculo)} revisiones de cálculo cuadran; "
          f"{len(tabla) - len(calculo)} pendiente(s) de datos.")
    return 1 if len(malas) else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
