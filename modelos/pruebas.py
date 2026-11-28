"""Pruebas de las reglas que no pueden fallar (sin servidor ni pytest):
    .venv/bin/python modelos/pruebas.py
"""
import numpy as np
import pandas as pd

import comun as C
from datos_sinteticos import generar as _generar


def generar(n):
    return C.derivar(_generar(n))


def prueba_sin_fuga_en_variables():
    tr = generar(20_000)
    tr, _ = C.universo(tr, 24)
    C.tasas_historicas(tr, [])
    prep = C.Preparador().ajustar(tr)
    assert not C.PROHIBIDAS.intersection(prep.variables), "variable prohibida en el modelo"
    for v in ["retraso_salida", "taxi_out", "taxi_in", "retraso_llegada"]:
        assert v not in prep.transformar(tr).columns


def prueba_guardia_detecta_fuga():
    viejo = list(C.NUMERICAS)
    C.NUMERICAS.append("retraso_salida")
    try:
        C.Preparador().ajustar(pd.DataFrame({c: [1] for c in C.NUMERICAS + C.CATEGORICAS + list(C.CLAVES_TASA)}))
        raise AssertionError("la guardia no detectó retraso_salida")
    except ValueError:
        pass
    finally:
        C.NUMERICAS[:] = viejo


def prueba_tasa_fuera_de_pliegue():
    """La tasa de una fila de entrenamiento no usa su propio año; la de validación usa todo."""
    tr = pd.DataFrame({"origen": ["X"] * 4, "anio": [2010, 2010, 2011, 2011], "y": [1, 1, 0, 0]})
    va = pd.DataFrame({"origen": ["X", "Z"]})
    prior = C.tasas_historicas(tr, [va], {"t": ["origen"]}, m=0.000001)
    assert prior == 0.5
    assert np.allclose(tr.t, [0, 0, 1, 1], atol=1e-4), tr.t.tolist()      # 2010 ve solo 2011 y viceversa
    assert np.isclose(va.t.iloc[0], 0.5) and np.isclose(va.t.iloc[1], 0.5)  # Z sin datos -> prior


def prueba_particion_b():
    df = generar(30_000)
    p = C.particionar(df, "B")
    assert p.entrenamiento.anio.between(2010, 2017).all()
    assert (p.entrenamiento.cubeta < C.POR_MIL_ENTRENAMIENTO).all()
    assert set(p.validacion.datos.anio) == {2018} and set(p.prueba.datos.anio) == {2019}
    assert not p.robustez[0].datos.periodo_covid.any() and p.robustez[1].datos.periodo_covid.all()


def prueba_universo_24_excluye_no_operados():
    d, _ = C.universo(generar(20_000), 24)
    assert not d.cancelado.any() and not d.desviado.any()


def prueba_metricas():
    m = C.metricas([1, 0, 1, 0], [0.9, 0.8, 0.2, 0.1], 0.5)
    assert (m["vp"], m["fp"], m["fn"], m["vn"]) == (1, 1, 1, 1)
    assert m["precision"] == 0.5 and m["recall"] == 0.5
    sin = C.metricas([1, 0, 0, 0], [0.25] * 4, float("inf"))
    assert sin["recall"] == 0 and sin["accuracy"] == 0.75


if __name__ == "__main__":
    for nombre, f in list(globals().items()):
        if nombre.startswith("prueba_"):
            f()
            print("OK", nombre)
