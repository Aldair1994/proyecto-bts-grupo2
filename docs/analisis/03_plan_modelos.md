# Plan de modelos: preguntas 24 y 25 (BORRADOR)

## 1. Definición de los problemas

| | Pregunta 24 | Pregunta 25 |
|---|---|---|
| Tarea | Clasificación binaria: retraso de llegada | Clasificación binaria: cancelación |
| Variable objetivo | `retraso_llegada_15` = true (llegada con >= 15 min de retraso; equivale a `estado_vuelo = 'Retrasado'`) | `cancelado` = true |
| Unidad de análisis | un vuelo programado (una fila de `dw.fact_flights`) | un vuelo programado |
| Población | vuelos **operados** (no cancelados ni desviados), pues solo ahí existe el retraso de llegada | **todos** los vuelos programados |
| Prevalencia | por calcular (consulta `07_programado_vs_real.sql` 7.6 / `04_estacionalidad.sql`) | ~1.9 % del periodo, ~6 % en 2020 (consulta `06_cancelaciones.sql` 6.9) |
| Momento de predicción | antes del despegue (con el itinerario y el calendario) | antes del despegue |

Los 3 modelos mínimos del proyecto pueden ser 3 algoritmos distintos sobre la pregunta 24; la pregunta 25 se puede cubrir con 1 o 2 de ellos.

## 2. Reglas de universo
- Pregunta 24: excluir cancelados y desviados; filas con `retraso_llegada_15` nulo se descartan y se cuenta cuántas son.
- Pregunta 25: incluir todos los vuelos; el objetivo no tiene nulos (`cancelado` es NOT NULL).
- Todo porcentaje reportado indica su universo (p. ej. "precisión sobre vuelos predichos como cancelados").

## 3. Variables permitidas (se conocen antes del despegue)

| Variable | Columna real | Nota |
|---|---|---|
| Mes, trimestre, temporada | `dim_fecha.mes`, `trimestre`, `temporada` | cíclicas: codificar con seno/coseno o como categoría |
| Día de la semana | `dim_fecha.dia_semana` | |
| Feriado, fin de semana | `dim_fecha.es_feriado`, `es_fin_semana` | |
| Bloque horario de salida programada | `bloque_salida_id` (franja en `dim_bloque_horario`) | hora programada |
| Hora de llegada programada | `hora_llegada_prog` | derivar hora 0-23 |
| Aerolínea | `airline_id` / `codigo` (y tipo cuando exista `dim_airline.tipo`) | muchas categorías: agrupar las raras en "otras" |
| Aeropuerto de origen y destino | `origin_airport_id`, `destination_airport_id` | alta cardinalidad: codificación por frecuencia o agrupar los de bajo volumen |
| Estado del origen / destino | `dim_airport.estado` | alternativa de menor cardinalidad |
| Distancia | `distancia` | |
| Duración programada | `tiempo_programado` | |
| Número de vuelo (como identificador de ruta) | `numero_vuelo` | solo si se justifica; riesgo de sobreajuste |
| Historial agregado **solo de entrenamiento** | p. ej. tasa histórica de retraso del aeropuerto / aerolínea / ruta | se calcula **solo con la ventana de entrenamiento** y se aplica a validación y prueba, para evitar fuga |

## 4. Variables prohibidas (fuga de información)

| Variable | Columna | Razón |
|---|---|---|
| Retraso de salida | `retraso_salida` (DepDelay), `retraso_salida_15` | solo se conoce al despegar; explica casi todo el retraso de llegada |
| Hora de salida real | `hora_salida_real` (DepTime) | idem |
| Taxi de salida | `taxi_out` (TaxiOut), WheelsOff | se conocen al despegar |
| Todo lo posterior al despegue | `taxi_in`, `hora_llegada_real`, `tiempo_real`, `tiempo_aire`, `retraso_llegada`, `retraso_total`, `categoria_retraso`, `estado_vuelo` | son el resultado (o lo definen) |
| Causas de retraso | `retraso_aerolinea`, `retraso_clima`, `retraso_nas`, `retraso_seguridad`, `retraso_avion_tardio` | solo existen cuando ya hubo retraso >= 15 min (equivale al objetivo) |
| Regreso a la puerta | `tiempo_extra_puerta` | ocurre durante la operación |
| Causa de cancelación | `cancelacion_id` | solo existe si ya se canceló (es el objetivo de la pregunta 25) |
| Desviado | `desviado` | ocurre durante el vuelo |
| Matrícula | `matricula` | no sirve de variable general (alta cardinalidad); el retraso del avión anterior sí sería válido pero requiere reconstruir la secuencia y que el vuelo previo ya haya aterrizado al momento de predecir; fuera del alcance inicial |

## 5. Partición temporal

La partición es por fecha (no aleatoria), para simular el uso real (predecir el futuro con datos del pasado).

**Opción A (propuesta del equipo)**: entrenar 2010-2018, validar 2019, probar 2020.
- Ventaja: respeta el orden temporal; validación en un año "normal".
- **Problema**: 2020 está dominado por COVID (cancelación ~6 % frente a ~1.9 % del periodo, menos vuelos, otra composición). Un mal resultado en 2020 puede deberse al cambio de régimen y no al modelo. Hay que reportarlo como prueba de robustez ante un cambio de régimen, no como estimación del desempeño normal. Cambia la prevalencia de la pregunta 25.

**Opción B (alternativa recomendada para la métrica principal)**: entrenar 2010-2017, validar 2018, probar 2019 (periodo normal); y reportar **aparte** el desempeño sobre 2020 (ene-feb sin COVID y mar-dic con COVID) como prueba de robustez.

**Opción C**: validación cruzada con ventana expansiva (entrenar en 2010..t, validar en t+1) para ver la estabilidad por año.

Reglas: las transformaciones que aprenden de los datos (codificaciones, escalado, historial agregado, umbral de decisión) se ajustan **solo con la partición de entrenamiento**; el umbral se elige en validación; la prueba se usa una sola vez. Documentar la prevalencia de cada partición.

## 6. Modelo de referencia (baseline)

- **Pregunta 24**: (a) predicción constante de la clase mayoritaria ("a tiempo"); (b) regla simple: tasa histórica de retraso por aerolínea + franja horaria (calculada en entrenamiento) con un umbral. El segundo es el baseline que hay que superar.
- **Pregunta 25**: (a) clase mayoritaria (nunca cancela: accuracy alta y recall 0, por eso accuracy engaña); (b) tasa histórica de cancelación por mes y aeropuerto de origen en entrenamiento, con umbral.

## 7. Algoritmos candidatos (3 sobre la pregunta 24)

1. **Regresión logística** (con regularización): interpretable, rápida; sirve de referencia "de modelo".
2. **Bosque aleatorio** (Random Forest): captura interacciones no lineales; robusto.
3. **Gradient boosting** (LightGBM, XGBoost o HistGradientBoosting de scikit-learn): normalmente el mejor en datos tabulares con categorías; admite `scale_pos_weight` y manejo de categorías.

Para la pregunta 25 repetir 1 y 3 (o el mejor de la 24), ajustando el desbalance.
Hiperparámetros: búsqueda sencilla en validación (profundidad, número de árboles, tasa de aprendizaje, regularización).

## 8. Métricas

Clase positiva = retraso (24) o cancelado (25). Todas se calculan sobre la partición de prueba (y validación para elegir).

- **Matriz de confusión** (conteos y normalizada por fila).
- **Precisión** = VP / (VP + FP): de los vuelos que el modelo marca como positivos, cuántos lo son.
- **Recall** = VP / (VP + FN): de los vuelos realmente positivos, cuántos detecta el modelo.
- **F1** (y F2 si el costo de no detectar es mayor).
- **AUC-PR** (área bajo la curva precisión-recall): métrica principal en la pregunta 25 por el desbalance; se compara con la prevalencia (el AUC-PR de un modelo aleatorio es igual a la prevalencia).
- AUC-ROC como complemento (informa, pero es optimista con clases raras).
- **Accuracy** solo como referencia; en la pregunta 25 no se usa para decidir (un modelo que nunca predice cancelación obtiene ~98 %).
- Desempeño por subgrupos: por año, aerolínea (tipo) y aeropuerto grande, para detectar sesgos.
- Calibración (curva de calibración) si se va a usar la probabilidad como riesgo.

## 9. Desbalance de clases

- Pregunta 25 (~1.9 %, ~6 % en 2020) y, en menor grado, la 24.
- Técnicas, en orden de preferencia: (1) **pesos de clase** (`class_weight`/`scale_pos_weight`); (2) **submuestreo de la clase mayoritaria solo en entrenamiento**; (3) umbral de decisión ajustado en validación según el objetivo de negocio (p. ej. recall mínimo); (4) SMOTE solo si hace falta (rara vez con tanto volumen y mayor costo).
- **Nunca** remuestrear validación ni prueba: deben conservar la prevalencia real.
- Reportar siempre la prevalencia de cada partición junto con las métricas.

## 10. Muestreo dado el volumen (~67 M de vuelos)

- Entrenar con la base completa de 2010-2018 no es necesario para estos algoritmos. Propuesta:
  - **Entrenamiento**: muestra estratificada por año (y por mes, para conservar estacionalidad) de ~1 a 3 M de filas (pregunta 24); para la pregunta 25 conservar **todos** los cancelados y submuestrear los no cancelados (guardando los pesos para corregir la prevalencia).
  - **Validación y prueba**: muestra aleatoria **sin remuestrear clases** de ~1 M de filas, o el año completo si el servidor lo permite.
- Muestrear en la base de datos (p. ej. `WHERE fecha_id BETWEEN ... AND random() < p` o `TABLESAMPLE`) y traer solo las columnas permitidas (sección 3); hacerlo año por año para aprovechar las particiones.
- Fijar semilla y registrar la consulta de extracción y el tamaño de cada muestra para que sea reproducible.
- Verificar que la muestra conserva la distribución del objetivo por año y mes.

## 11. Entregables del modelado
- Notebook o script reproducible, tabla comparativa de modelos frente al baseline, matrices de confusión, curvas precisión-recall, importancia de variables, discusión del sesgo COVID y de las decisiones del equipo (variables prohibidas, partición).
