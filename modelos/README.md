# Correlaciones (informe 2.11) y modelos (preguntas 24 y 25)

Implementa `docs/analisis/03_plan_modelos.md`. Solo el **paso 1** necesita el servidor; lo demás corre en la laptop.

| Archivo | Qué hace |
|---|---|
| `muestra.sql` | Consulta de la muestra (un año por ejecución). Muestreo determinista por hash de `flight_id`. |
| `extraer_muestra.py` | Corre la consulta año por año y guarda `data/modelos/muestra_AAAA.parquet` + `extraccion.json`. |
| `comun.py` | Variables permitidas y **prohibidas** (fuga), partición temporal, tasas históricas sin fuga, métricas. |
| `correlaciones.py` | Matriz Pearson/Spearman y correlación con el objetivo (2.11). |
| `entrenar.py` | Líneas base + 3 modelos (pregunta 24) y 2 modelos (pregunta 25); métricas, figuras y resumen. |
| `datos_sinteticos.py`, `pruebas.py` | Datos falsos con el mismo esquema y pruebas de las reglas (sin servidor). |

## Muestra

- 2010-2017: 5 % de cada año (~2.4 M vuelos) → **entrenamiento**.
- 2018-2020: 15 % de cada año (~2.9 M) → **validación 2018, prueba 2019, robustez 2020** (ene-feb y mar-dic).
- La cubeta (hash de `flight_id` módulo 1000) no depende del resultado del vuelo: muestra aleatoria simple dentro de cada año, reproducible. El entrenamiento usa la misma tasa (5 %) en todos sus años.

## Pasos (esta noche, con el servidor encendido: fines de semana 17:00-22:00 GT)

```bash
cd proyecto-bts-grupo2
python3 -m venv .venv && .venv/bin/pip install -r modelos/requirements.txt   # una vez
.venv/bin/python modelos/pruebas.py                                          # debe decir OK x6

# 1) Extracción (único paso con servidor, ~15-30 min). Terminal A: túnel
ssh -N -C -L 15432:localhost:5432 ubuntu@100.55.222.111
# Terminal B: contraseña de la BD = POSTGRES_PASSWORD del .env de ~/app en el servidor
#   (ssh ubuntu@100.55.222.111 'grep POSTGRES_PASSWORD ~/app/.env')  o  cd ../infra && tofu output -raw db_password
export PGHOST=localhost PGPORT=15432 PGDATABASE=bts PGUSER=bts_admin PGPASSWORD='...'
.venv/bin/python modelos/extraer_muestra.py --anios 2019 --limite 100   # prueba -> data/modelos/prueba_2019.parquet (no se usa)
.venv/bin/python modelos/extraer_muestra.py --salida data/modelos                                    # completa
# (si se corta, volver a correrla: salta los años ya guardados; la bitácora se escribe año por año)

# 2) Sin servidor (se puede apagar):
.venv/bin/python modelos/correlaciones.py --datos data/modelos --salida modelos/resultados
.venv/bin/python modelos/entrenar.py --datos data/modelos --salida modelos/resultados
```

Comprobar en `data/modelos/extraccion.json` que el % de cancelados y de retraso >= 15 por año se parezca a
`sql/analisis/resultados/20261127_completo/06_cancelaciones_6.1.csv` y `07_programado_vs_real_7.6.csv`.

## Salidas (`modelos/resultados/`)

- `resumen_p24.md`, `resumen_p25.md`: prevalencia por partición, métricas en prueba y validación, robustez 2020, búsqueda de hiperparámetros, subgrupos e importancia de variables.
- `p24_*.png`, `p25_*.png`: curvas precisión-recall, matriz de confusión (prueba y 2020), importancia, calibración.
- `correlaciones.md`, `correlaciones.png`, CSV de métricas.

## Decisiones (para el informe)

- **Sin fuga**: no se usan retraso de salida, hora real, taxi, causas ni nada posterior al despegue; `comun.py` falla si alguna entra.
- **Tasas históricas** (aeropuerto, ruta, aerolínea × franja, aeropuerto × mes) calculadas solo con entrenamiento; en las filas de entrenamiento, con los *otros* años (fuera de pliegue) para no filtrar el objetivo.
- **Umbral** = máximo F1 en validación. **Desbalance**: pesos de clase en la logística y el bosque (ambas preguntas) y en gradient boosting de la pregunta 25; gradient boosting de la 24 sin pesos (prevalencia ~18 %). No se remuestrea validación ni prueba. Los modelos con pesos **no están calibrados**: su probabilidad ordena el riesgo pero no es una probabilidad real (ver `pNN_calibracion.png`).
- **Métrica principal**: AUC-PR (comparar con la prevalencia, que es el AUC-PR del azar); accuracy solo como referencia.
- El bosque aleatorio se entrena con 600 mil filas (costo); logística y gradient boosting con toda la muestra de entrenamiento.
- Opción A del plan (entrenar 2010-2018, validar 2019, probar 2020): `--particion A`.
