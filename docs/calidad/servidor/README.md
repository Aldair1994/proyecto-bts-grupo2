# Verificacion de la carga en el servidor

Corrida del 26 de noviembre de 2026 (hora de Guatemala) sobre el commit `9b8209f`, con la base en modo de solo lectura.

| Archivo | Que contiene | Resultado |
|---|---|---|
| `verificacion_descargas.txt` | `calidad/verificar_descargas.py`: zips contra `docs/manifiesto_fuente.csv` | 132 de 132 OK |
| `checks_resultado.txt` | `sql/quality/checks.sql` (tardo 13 minutos) | 11 anios OK, 13 reglas OK, raw = fact = 67,249,397 |
| `puntualidad_por_universo.txt` | Puntualidad por anio sobre programados y sobre operados, y nombres de OH, XE y EV | Citar la puntualidad sobre operados (KPI-1) |

`OK` significa que coincide con lo medido en la fuente, no que los datos no tengan anomalias.

El estado `Sin dato` de `dw.fact_flights` son 352 vuelos operados sin `arr_del15` (1 en 2017, 350 en 2018 y 1 en 2020). Siguen contando dentro de los vuelos operados.
