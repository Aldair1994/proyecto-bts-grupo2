# Esqueleto del informe: Data Understanding y Análisis final (BORRADOR)

Cada sección indica qué va escrito y qué consulta de `sql/analisis/` alimenta cada tabla o gráfico.
Cada consulta tiene arriba su pregunta, universo y KPI. Las definiciones están en `01_preguntas_kpis.md`.

## Avisos obligatorios (deben aparecer en el informe)

- **Universo de cada porcentaje**: puntualidad sobre vuelos operados (no cancelados ni desviados); cancelación sobre programados; causas de retraso solo sobre vuelos con retraso de llegada >= 15 min (BTS no reporta causas fuera de ahí; los nulos son esperados).
- **COVID**: `periodo_covid = true` desde 2020-03-01 (supuesto). 2020 se muestra aparte en tendencias; los patrones estacionales usan 2010-01 a 2020-02.
- **Aerolíneas**: Spirit (NK) solo desde 2015; Allegiant (G4) y Republic (YX) desde 2018. Fusiones: Continental CO a UA, AirTran FL a WN, US Airways US a AA, Virgin America VX a AS. Avisarlo al comparar 2010 vs. 2020. Regionales (SkyWest OO, Envoy MQ, ExpressJet EV, Endeavor 9E, PSA OH, Mesa YV, Republic YX, etc.) se rankean aparte.
- **Mapa**: puede faltar la latitud/longitud de algunos aeropuertos; indicar cuántos vuelos quedan fuera (consulta 3.6).
- **Modelos**: pregunta 24 = retraso de llegada; pregunta 25 = cancelaciones (evento raro: precisión y recall); sin variables de fuga (retraso_salida, hora_salida_real, taxi_out, WheelsOff).

---

## PARTE I. Data Understanding

### 1. Inventario de fuentes y diccionario de datos
- **Qué va**: fuente (BTS TranStats, Reporting Carrier On-Time Performance), rango 2010-2020, método de extracción, volumen (~67.2 M de filas esperadas, 132 meses), propietario, fecha de descarga. Diccionario de las 46 columnas (de `docs/columnas.md`) y del modelo estrella `dw` (`sql/init/03_dw_star.sql`).
- **Consulta**: `01_calidad.sql` 1.1 (conteos por año y mes) para demostrar cobertura.

### 2. Análisis exploratorio (EDA)

| Subsección | Qué va | Gráfico / tabla | Consulta |
|---|---|---|---|
| 2.1 Volumen y cobertura | vuelos por año y mes, meses faltantes | línea mensual de vuelos; tabla de huecos (debe estar vacía) | 01 (1.1, 1.2, 1.3) |
| 2.2 Estados del vuelo | % a tiempo / retrasado / cancelado / desviado por año (cada % con su universo) | barras apiladas por año | 04 (4.1), 06 (6.1) |
| 2.3 Distribución del retraso de llegada | histograma, percentiles, cola | histograma de cubetas de 15 min; tabla de percentiles por año | 07 (7.5, 7.7), 01 (1.7) |
| 2.4 Categorías de retraso | Leve a Extremo por año | barras 100 % apiladas | 07 (7.6) |
| 2.5 Aerolíneas | volumen y cobertura por aerolínea, tipo | tabla de cobertura; barras por tipo | 01 (1.12), 02 (2.1) |
| 2.6 Aeropuertos y rutas | aeropuertos más grandes, distribución de volumen, rutas | barras top N; tabla de rutas | 03 (3.3, 3.7) |
| 2.7 Distancia y duración | relación distancia vs. retraso y duración programada vs. real | barras por rango de distancia | 05 (5.8), 07 (7.3) |
| 2.8 Estacionalidad | mes, temporada, día, hora, feriados | línea por mes, barras por día, mapa de calor día x franja | 04 (4.2 a 4.8) |
| 2.9 Causas | participación de causas, causa dominante | barras apiladas por año; torta/barras de causa dominante | 05 (5.1 a 5.3) |
| 2.10 Cancelaciones | tasa por año, causa, mes | línea por año; barras por causa | 06 (6.1, 6.2, 6.5) |
| 2.11 Relaciones entre variables | correlación entre retraso_salida, retraso_llegada, distancia, hora | matriz de correlación (calculada sobre una muestra; ver `03_plan_modelos.md` sección 10) | muestra desde `dw.fact_flights` |

### 3. Análisis de visualización
- **Qué va**: justificación de los gráficos elegidos para cada KPI del dashboard (barras para rankings, línea para tendencias, mapa para geografía, histograma para distribución, mapa de calor para día x hora), escalas, colores y tratamiento de COVID (franja sombreada desde 2020-03-01) y de las aerolíneas que aparecen/desaparecen. Capturas del dashboard y mockups.
- **Consultas**: las de los requerimientos R2 a R6 (02/2.1, 02/2.3, 03/3.4, 07/7.1, 07/7.5, 03/3.1).
- **Aviso**: mapa con nota de aeropuertos sin coordenadas.

### 4. Informe de calidad de datos

| Subsección | Qué va | Consulta |
|---|---|---|
| 4.1 Completitud | % de nulos por columna y año, separando nulos esperados (cancelados sin horas reales; causas fuera de retraso >= 15) de los inesperados | 01 (1.4, 1.5) |
| 4.2 Valores inválidos y atípicos | distancia <= 0, tiempos <= 0, retrasos extremos (> 24 h), adelantos > 2 h, origen = destino, hora fuera de rango; decisión de tratamiento (excluir o conservar) | 01 (1.6, 1.7) |
| 4.3 Integridad referencial | hechos sin dimensión, dimensiones sin uso, aeropuertos sin coordenadas / zona horaria | 01 (1.8) |
| 4.4 Coherencia de reglas de negocio | `estado_vuelo` vs. `cancelado`/`desviado`/retraso; causas vs. retraso de llegada | 01 (1.9, 1.10), 05 (5.9) |
| 4.5 Duplicados | llave natural fecha-aerolínea-vuelo-origen-destino-hora | 01 (1.11) |
| 4.6 Cambios de cobertura | aerolíneas que aparecen/desaparecen (NK, G4, YX, CO, FL, US, VX) | 01 (1.12) |
| 4.7 Priorización | tabla de hallazgos con impacto (alto/medio/bajo), cantidad de filas afectadas y acción | síntesis de lo anterior |
| 4.8 Disponibilidad de campos | qué campo se conoce antes de la salida (para evitar fuga en el modelo) | ver `03_plan_modelos.md` sección 3 |

---

## PARTE II. Análisis final e insights

### 5. Hallazgos (uno por objetivo; escribir solo con cifras reales de las consultas)

| Hallazgo | Qué va | Gráfico / tabla | Consulta |
|---|---|---|---|
| 5.1 Aeropuertos con más retrasos | ranking con mínimo de vuelos, hubs vs. resto, estados | barras top 15; mapa (o mapa por estado si faltan coordenadas) | 03 (3.1, 3.2, 3.3, 3.4/3.5) |
| 5.2 Estacionalidad | meses, días y horas críticos; feriados | línea mensual; barras por día; mapa de calor | 04 (4.2 a 4.8) |
| 5.3 Puntualidad por aerolínea | ranking separado por tipo (regional / bajo costo / tradicional); evolución por año | barras por tipo; líneas por año; tabla 2010 vs. 2019 de aerolíneas comparables | 02 (2.1, 2.2, 2.5) |
| 5.4 Clima y geografía | causas de retraso, clima por mes y estado, distancia | barras de causas; clima por mes; barras por distancia | 05 (5.1, 5.5 a 5.8) |
| 5.5 Cancelaciones | tasa por año, causa, aerolínea, aeropuerto; días extremos | línea anual; barras por causa; tabla de días | 06 (6.1 a 6.4, 6.7) |
| 5.6 Efecto COVID | caída de vuelos, cancelaciones y puntualidad frente a 2019; efecto de composición | líneas 2019 vs. 2020 por mes; curva semanal; tabla por aerolínea | 08 (8.1 a 8.7) |
| 5.7 Programado vs. real | desvío de duración, holgura de itinerario | línea por mes; barras por distancia | 07 (7.1 a 7.4) |
| 5.8 Modelos (24 y 25) | resultados frente al modelo de referencia; variables importantes | tabla de métricas; curva precisión-recall; matriz de confusión | `03_plan_modelos.md` |

### 6. Insights
- **Qué va**: interpretación de negocio de cada hallazgo (por qué ocurre, a quién afecta, qué decisión habilita). Separar lo que muestra el dato de lo que es hipótesis. Señalar el efecto de composición en 2020 (menos vuelos, otros horarios) antes de atribuir mejoras de puntualidad a la operación. Indicar el universo del porcentaje en cada afirmación.

### 7. Conclusiones
- **Qué va**: respuesta explícita a cada objetivo de `01_preguntas_kpis.md`, comparando el valor obtenido con la meta propuesta (secciones de "Valor actual" y "Meta"). Cumplimiento de criterios de aceptación. Coherencia entre dashboard e informe (mismos KPI de la sección 5 de `01_preguntas_kpis.md`).

### 8. Recomendaciones
- **Qué va**: acciones por actor (aerolíneas, aeropuertos, pasajeros/autoridades), priorizadas por impacto y facilidad; cómo monitorearlas con los KPI del dashboard.

### 9. Limitaciones y trabajo futuro
- **Qué va**: los avisos del inicio; falta de datos climatológicos externos; solo WeatherDelay de BTS; ausencia de coordenadas; supuesto de COVID desde 2020-03-01; clasificación temporal de aerolíneas por tipo; sesgo COVID en el modelo; mejoras posibles (clima externo, tráfico aéreo, retraso del avión anterior).
