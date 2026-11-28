"""Piezas comunes de los modelos (preguntas 24 y 25) y de las correlaciones.

Reglas del plan (docs/analisis/03_plan_modelos.md):
  * Solo variables conocidas antes del despegue (§3). Las de fuga (§4) están en PROHIBIDAS y
    `preparar_variables` falla si alguna entra al modelo.
  * Partición temporal (§5). Opción B (por defecto): entrenar 2010-2017, validar 2018, probar 2019;
    2020 aparte como prueba de robustez (ene-feb y mar-dic). Opción A: 2010-2018 / 2019 / 2020.
  * Todo lo que aprende de los datos (tasas históricas, categorías frecuentes, medianas, umbral)
    se ajusta solo con entrenamiento.
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             precision_recall_curve, roc_auc_score)

RAIZ = Path(__file__).resolve().parents[1]

# Tasa de muestreo (por mil) de cada partición; ver modelos/muestra.sql.
POR_MIL_ENTRENAMIENTO = 50
POR_MIL_EVALUACION = 150

PROHIBIDAS = {
    # §4 del plan: se conocen al despegar o después, o definen el objetivo.
    "retraso_salida", "retraso_salida_15", "hora_salida_real", "taxi_out", "wheels_off",
    "taxi_in", "hora_llegada_real", "tiempo_real", "tiempo_aire", "retraso_llegada",
    "retraso_total", "categoria_retraso", "estado_vuelo", "retraso_aerolinea", "retraso_clima",
    "retraso_nas", "retraso_seguridad", "retraso_avion_tardio", "tiempo_extra_puerta",
    "cancelacion_id", "desviado", "matricula", "cancelado", "retraso_llegada_15",
}

CATEGORICAS = ["aerolinea", "tipo_aerolinea", "origen", "destino", "estado_origen", "estado_destino"]
NUMERICAS = ["mes", "dia_semana", "hora_salida", "hora_llegada", "es_feriado", "es_fin_semana",
             "distancia", "tiempo_programado"]
# Tasas históricas (codificación por objetivo) calculadas solo con entrenamiento.
CLAVES_TASA = {
    "tasa_origen": ["origen"],
    "tasa_destino": ["destino"],
    "tasa_ruta": ["origen", "destino"],
    "tasa_aerolinea_franja": ["aerolinea", "franja"],
    "tasa_origen_mes": ["origen", "mes"],
}
SUAVIZADO = 200          # vuelos "ficticios" con la tasa global (evita tasas extremas con poco volumen)
MAX_CATEGORIAS = 250     # HistGradientBoosting admite hasta 255 categorías por variable

PREGUNTAS = {
    24: {"objetivo": "retraso_llegada_15", "nombre": "retraso de llegada >= 15 min",
         "universo": "vuelos operados (ni cancelados ni desviados)",
         "regla_base": "tasa_aerolinea_franja"},
    25: {"objetivo": "cancelado", "nombre": "cancelación",
         "universo": "todos los vuelos programados",
         "regla_base": "tasa_origen_mes"},
}


def franja_de_hora(hora: pd.Series) -> pd.Series:
    """Misma regla que dw.dim_bloque_horario: 0-5 Madrugada, 6-11 Mañana, 12-17 Tarde, 18-23 Noche."""
    h = pd.to_numeric(hora, errors="coerce").astype(float)
    franja = np.select([h <= 5, h <= 11, h <= 17, h <= 23], ["Madrugada", "Mañana", "Tarde", "Noche"],
                       default="Desconocida")
    return pd.Series(np.where(h.isna(), "Desconocida", franja), index=hora.index)


def cargar_muestra(carpeta: Path) -> pd.DataFrame:
    archivos = sorted(Path(carpeta).glob("muestra_*.parquet"))
    if not archivos:
        raise SystemExit(f"No hay archivos muestra_*.parquet en {carpeta}")
    return derivar(pd.concat([pd.read_parquet(a) for a in archivos], ignore_index=True))


def derivar(df: pd.DataFrame) -> pd.DataFrame:
    """Columnas derivadas: hora de llegada (0-23), franja de salida y booleanos sin nulos."""
    df["hora_llegada"] = (df["hora_llegada_prog"] // 100) % 24
    df["franja"] = franja_de_hora(df["hora_salida"])
    for c in ["es_feriado", "es_fin_semana", "periodo_covid", "cancelado", "desviado"]:
        df[c] = df[c].astype(bool)
    return df


@dataclass
class Particion:
    nombre: str
    datos: pd.DataFrame
    descripcion: str


@dataclass
class Particiones:
    entrenamiento: pd.DataFrame
    validacion: Particion
    prueba: Particion
    robustez: list = field(default_factory=list)
    opcion: str = "B"


def particionar(df: pd.DataFrame, opcion: str = "B") -> Particiones:
    ent = df["cubeta"] < POR_MIL_ENTRENAMIENTO
    eva = df["cubeta"] < POR_MIL_EVALUACION
    if opcion == "B":
        tr = df[ent & df.anio.between(2010, 2017)]
        va = Particion("validación 2018", df[eva & (df.anio == 2018)], "2018 completo (muestra 15 %)")
        te = Particion("prueba 2019", df[eva & (df.anio == 2019)], "2019 completo (muestra 15 %)")
        d20 = df[eva & (df.anio == 2020)]
        rob = [Particion("2020 ene-feb", d20[~d20.periodo_covid], "antes de COVID"),
               Particion("2020 mar-dic", d20[d20.periodo_covid], "con COVID")]
    elif opcion == "A":
        tr = df[ent & df.anio.between(2010, 2018)]
        va = Particion("validación 2019", df[eva & (df.anio == 2019)], "2019 completo (muestra 15 %)")
        d20 = df[eva & (df.anio == 2020)]
        te = Particion("prueba 2020", d20, "2020 completo (muestra 15 %), régimen COVID")
        rob = [Particion("2020 ene-feb", d20[~d20.periodo_covid], "antes de COVID"),
               Particion("2020 mar-dic", d20[d20.periodo_covid], "con COVID")]
    else:
        raise ValueError("opción de partición: 'A' o 'B'")
    return Particiones(tr.copy(), va, te, rob, opcion)


def universo(df: pd.DataFrame, pregunta: int) -> tuple[pd.DataFrame, int]:
    """Filtra el universo de la pregunta. Devuelve (datos, filas descartadas por objetivo nulo)."""
    if pregunta == 24:
        op = df[~df.cancelado & ~df.desviado]
        nulos = int(op.retraso_llegada_15.isna().sum())
        op = op[op.retraso_llegada_15.notna()].copy()
        op["y"] = op.retraso_llegada_15.astype(bool).astype(int)
        return op, nulos
    d = df.copy()
    d["y"] = d.cancelado.astype(int)
    return d, 0


def tasas_historicas(train: pd.DataFrame, otros: list, claves_tasa=CLAVES_TASA, m=SUAVIZADO):
    """Codificación por objetivo con suavizado, sin fuga:
       * filas de entrenamiento: tasa calculada con los DEMÁS años de entrenamiento (fuera de pliegue);
       * validación / prueba: tasa con todo el entrenamiento.
    Modifica los DataFrames en su lugar (agrega una columna por clave)."""
    prior = train["y"].mean()
    for nombre, claves in claves_tasa.items():
        tot = train.groupby(claves, observed=True)["y"].agg(s="sum", n="count").reset_index()
        anu = train.groupby(claves + ["anio"], observed=True)["y"].agg(sa="sum", na="count").reset_index()
        t = train[claves + ["anio"]].merge(tot, on=claves, how="left").merge(anu, on=claves + ["anio"], how="left")
        # Clave nula: groupby la descarta; igual que en validación/prueba, recibe la tasa global.
        t = t.fillna({"s": 0, "n": 0, "sa": 0, "na": 0})
        train[nombre] = ((t.s - t.sa + m * prior) / (t.n - t.na + m)).to_numpy()
        for o in otros:
            t = o[claves].merge(tot, on=claves, how="left")
            o[nombre] = ((t.s.fillna(0) + m * prior) / (t.n.fillna(0) + m)).to_numpy()
    return prior


@dataclass
class Preparador:
    """Aprende de entrenamiento las categorías frecuentes y las medianas; transforma cualquier partición."""
    categorias: dict = field(default_factory=dict)
    medianas: dict = field(default_factory=dict)
    variables: list = field(default_factory=list)

    def ajustar(self, train: pd.DataFrame):
        self.variables = NUMERICAS + list(CLAVES_TASA) + CATEGORICAS
        fuga = PROHIBIDAS.intersection(self.variables)
        if fuga:
            raise ValueError(f"Variables con fuga de información en el modelo: {sorted(fuga)}")
        for c in CATEGORICAS:
            frec = train[c].fillna("Desconocido").value_counts()
            self.categorias[c] = list(frec.index[:MAX_CATEGORIAS]) + ["Otros"]
        for c in NUMERICAS + list(CLAVES_TASA):
            self.medianas[c] = float(pd.to_numeric(train[c], errors="coerce").median())
        return self

    def transformar(self, df: pd.DataFrame) -> pd.DataFrame:
        x = pd.DataFrame(index=df.index)
        for c in NUMERICAS + list(CLAVES_TASA):
            x[c] = pd.to_numeric(df[c], errors="coerce").astype(float).fillna(self.medianas[c])
        for c in CATEGORICAS:
            v = df[c].fillna("Desconocido")
            v = v.where(v.isin(self.categorias[c]), "Otros")
            x[c] = pd.Categorical(v, categories=self.categorias[c])
        return x[self.variables]


def umbral_max_f1(y, p) -> float:
    """Umbral que maximiza F1 (se elige en validación)."""
    prec, rec, umb = precision_recall_curve(y, p)
    f1 = np.where(prec + rec > 0, 2 * prec * rec / np.maximum(prec + rec, 1e-12), 0)[:-1]
    if len(umb) == 0:
        return float("inf")
    return float(umb[int(np.argmax(f1))])


def metricas(y, p, umbral) -> dict:
    y = np.asarray(y).astype(int)
    pred = (np.asarray(p) >= umbral).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    f2 = 5 * prec * rec / (4 * prec + rec) if 4 * prec + rec else 0.0
    unicos = len(np.unique(p)) > 1
    return {
        "filas": len(y), "positivos": int(y.sum()), "prevalencia_pct": 100 * y.mean(),
        "umbral": umbral, "vp": int(tp), "fp": int(fp), "fn": int(fn), "vn": int(tn),
        "accuracy": (tp + tn) / len(y), "precision": prec, "recall": rec, "f1": f1, "f2": f2,
        "auc_pr": average_precision_score(y, p) if unicos else y.mean(),
        "auc_roc": roc_auc_score(y, p) if unicos and 0 < y.sum() < len(y) else 0.5,
    }
