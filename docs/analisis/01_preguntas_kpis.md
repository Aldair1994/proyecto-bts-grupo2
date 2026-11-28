# Business Understanding: objetivos, preguntas de negocio y KPI (BORRADOR)

## 0. Convenciones de definición (valen para todo el proyecto)

- **Vuelo operado** = `NOT cancelado AND NOT desviado`. **Vuelo programado** = todos los vuelos.
- **A tiempo** (`estado_vuelo = 'A tiempo'`) sigue el criterio oficial de BTS: llegada con menos de 15 min de retraso. Es el KPI-1.
- **No confundir:** `categoria_retraso = 'Sin retraso'` (retraso de llegada <= 0 min) es OTRA definición, más estricta. Antes se llamaba 'A tiempo'; se renombró para no chocar con `estado_vuelo`.
  No es el KPI-1; en las consultas se publica como `pct_sin_retraso_0min_sobre_operados`.
  Recomendación a Data Engineering: renombrar esa categoría en `20_fact_flights.sql` (p. ej. a 'Sin retraso')
  para que el dashboard no muestre dos "A tiempo" distintos.
- Cada porcentaje lleva su universo en el nombre: `pct_a_tiempo_sobre_operados`,
  `pct_cancelados_sobre_programados`, etc. Un porcentaje sin universo no se publica.
- Las causas de retraso (`retraso_aerolinea`, `retraso_clima`, `retraso_nas`, `retraso_seguridad`,
  `retraso_avion_tardio`) solo existen cuando `retraso_llegada >= 15` (`retraso_llegada_15 = true`).
  Los nulos fuera de ese universo son esperados.
- Mínimos de volumen en rankings (aerolíneas, aeropuertos, rutas): se define en cada consulta
  (`params.min_operados`) para no rankear grupos con pocos vuelos.

## 1. Objetivos de negocio

Usuarios y decisión: gerencias de operaciones de aerolíneas, administración de aeropuertos y
autoridades de aviación civil, que necesitan saber **dónde, cuándo y por qué** se retrasan o
cancelan los vuelos para priorizar acciones.

### Objetivo 1. Identificar los aeropuertos con mayor incidencia de retrasos

- **Preguntas de negocio**
  1. ¿Qué aeropuertos de origen tienen la mayor proporción de salidas con retraso de 15 min o más?
  2. ¿A qué aeropuertos de destino se llega con peor puntualidad?
  3. ¿Los aeropuertos grandes (hubs) son peores que los pequeños?
  4. ¿Qué estados/rutas concentran los peores resultados?
- **KPI**
  - `pct_salida_retrasada_15_sobre_operados` = vuelos operados con `retraso_salida_15 = true` / vuelos operados con `retraso_salida_15` no nulo * 100, por `origin_airport_id`. (KPI-4)
  - `pct_a_tiempo_sobre_operados` por `destination_airport_id`. (KPI-1)
- **Universo**: vuelos operados del aeropuerto; solo aeropuertos con >= N vuelos operados.
- **Valor actual** (2010-2020, ver `04_hallazgos.md` 5.1): KPI-4 global 17.64 %; 30 aeropuertos más grandes 18.77 % vs. resto 15.47 %; peor grande Midway 25.39 %, mejor Salt Lake City 12.34 %. **Meta**: `[META: reducir a ___ % las salidas retrasadas en los aeropuertos del cuartil peor]`.
- **Consultas**: `03_aeropuertos.sql` (3.1 a 3.7); mapa en 3.4 y alternativa por estado en 3.5.

### Objetivo 2. Determinar patrones estacionales en los vuelos

- **Preguntas de negocio**
  1. ¿Qué meses, temporadas, días de la semana y horas del día tienen peor puntualidad?
  2. ¿Los feriados y fines de semana aumentan los retrasos o cancelaciones?
  3. ¿Cómo evoluciona el volumen de vuelos y la puntualidad de 2010 a 2020?
- **KPI**: `pct_a_tiempo_sobre_operados` y `mediana_retraso_llegada_min` por mes / día / bloque horario / temporada / es_feriado; vuelos por día (KPI-7).
- **Universo**: operados del periodo analizado. El patrón estacional se calcula con 2010-01 a 2020-02 (antes de `periodo_covid`).
- **Valor actual** (2010-01 a 2020-02, ver `04_hallazgos.md` 5.2): meses críticos junio (77.14 %), julio (77.69 %) y diciembre (78.49 %); franja crítica 17:00-21:59 (73.5-75.3 %) frente a 92.34 % a las 5 a. m. **Meta**: `[META: identificar los ___ meses y las ___ franjas horarias críticas para reforzar operación]`.
- **Consultas**: `04_estacionalidad.sql` (4.1 a 4.9).

### Objetivo 3. Calcular qué aerolíneas presentan mejor desempeño puntual

- **Preguntas de negocio**
  1. ¿Cuál es el ranking de aerolíneas por puntualidad, separando regionales, bajo costo y tradicionales?
  2. ¿Cómo evolucionó la puntualidad de cada aerolínea por año?
  3. ¿Qué tan graves son los retrasos de cada aerolínea (categorías Leve a Extremo)?
- **KPI**: `pct_a_tiempo_sobre_operados` (KPI-1); `mediana_retraso_llegada_min` (KPI-2); `pct_cancelados_sobre_programados` (KPI-3).
- **Universo**: operados de la aerolínea, con mínimo de vuelos. Los rankings se hacen **por tipo** (regional / bajo costo / tradicional).
- **Valor actual** (2010-2020, ver `04_hallazgos.md` 5.3): tradicional 83.27 %, regional 80.73 %, bajo costo 80.47 %; brecha mejor-peor dentro del tipo: 10.9, 5.4 y 8.1 puntos. Cancelación: regional 2.83 %, tradicional 1.39 %. **Meta**: `[META: ___ % de vuelos a tiempo; brecha máxima de ___ puntos entre la mejor y la peor de cada tipo]`.
- **Consultas**: `02_puntualidad_aerolineas.sql` (2.1 a 2.5).
- **Avisos**: ver sección 4 (Spirit, Allegiant, Republic, fusiones).

### Objetivo 4. Analizar el impacto del clima y la geografía en los retrasos

- **Preguntas de negocio**
  1. ¿Qué proporción de los minutos de retraso se debe al clima, a la aerolínea, al sistema nacional (NAS), a seguridad o al avión tardío?
  2. ¿En qué meses y en qué estados/aeropuertos pesa más el clima?
  3. ¿La distancia del vuelo se relaciona con el retraso?
- **KPI**: `pct_causa_X_sobre_min_retraso_15` = minutos de la causa X / suma de minutos de las 5 causas * 100 (KPI-5); `min_clima_por_vuelo_operado`; `pct_a_tiempo_sobre_operados` por rango de distancia.
- **Universo**: participación de causas = solo operados con `retraso_llegada >= 15`. Clima por vuelo = todos los operados (nulo = 0), indicado en el alias.
- **Valor actual** (2010-2020, ver `04_hallazgos.md` 5.4): avión tardío 39.95 %, aerolínea 31.23 %, NAS 24.06 %, clima 4.74 %, seguridad 0.14 % de los minutos de retraso (controlables: 71.2 %). Clima = 42-59 % de las cancelaciones por año (2010-2019). **Meta**: `[META: explicar ___ % de los minutos de retraso con causas controlables por la aerolínea]`.
- **Consultas**: `05_causas_retraso_clima.sql` (5.1 a 5.9).
- **Límite**: `retraso_clima` es solo el WeatherDelay de BTS; el clima también influye en NAS y en avión tardío (subestima el impacto total). Los datos climatológicos externos (3.3 del enunciado) son opcionales y no están cargados.

### Objetivo 5. Reducir la incertidumbre sobre cancelaciones y desvíos (pregunta 25)

- **Preguntas de negocio**
  1. ¿Cuál es la tasa de cancelación por año, aerolínea y aeropuerto, y por qué causa (aerolínea, clima, NAS, seguridad)?
  2. ¿Se puede predecir qué vuelos se cancelarán con información disponible antes de la salida?
- **KPI**: `pct_cancelados_sobre_programados` = cancelados / programados * 100 (KPI-3); `pct_desviados_sobre_programados` (KPI-8); en el modelo: precisión y recall de la clase "cancelado".
- **Universo**: todos los vuelos programados (los cancelados no son "operados").
- **Valor actual** (2010-2020, ver `04_hallazgos.md` 5.5): 1.94 % del periodo, 1.62 % antes de COVID, 5.99 % en 2020; desvío 0.23 %. **Meta**: `[META: recall >= ___ con precisión >= ___ para la clase cancelado]`.
- **Consultas**: `06_cancelaciones.sql` (6.1 a 6.9); plan del modelo en `03_plan_modelos.md`.

### Objetivo 6. Cuantificar el efecto de COVID-19 en 2020

- **Preguntas de negocio**
  1. ¿Cuánto cayó el volumen de vuelos y cuánto subieron las cancelaciones después de marzo de 2020, frente a los mismos meses de 2019?
  2. ¿Cambió la puntualidad, la mezcla de causas o el tipo de vuelo (distancia, franja)?
  3. ¿Qué aerolíneas y aeropuertos fueron más afectados?
- **KPI**: `variacion_vuelos_pct_vs_2019` (KPI-7), `pct_cancelados_sobre_programados` (KPI-3), `pct_a_tiempo_sobre_operados` (KPI-1), comparados mes a mes.
- **Universo**: programados (volumen, cancelación) y operados (puntualidad). Se compara cada mes de 2020 con el mismo mes de 2019. `dim_fecha.periodo_covid = true` desde 2020-03-01 (supuesto).
- **Valor actual** (ver `04_hallazgos.md` 5.6): -44.4 % de vuelos mar-dic 2020 vs. 2019; peor mes mayo (-71.6 %); 2020 cerró en 55-66 % del volumen de 2019 (sin recuperación); puntualidad mar-dic 91.80 % vs. 81.17 %. **Meta**: `[META: documentar la caída máxima mensual y el mes de recuperación a >= ___ % del volumen 2019]`.
- **Consultas**: `08_covid_2020.sql` (8.1 a 8.7).

### Objetivo analítico de modelado (pregunta 24)

Clasificar si un vuelo **llegará con retraso de 15 min o más** (variable objetivo `retraso_llegada_15`) usando solo información conocida antes del despegue. Ver `03_plan_modelos.md`.
Meta: `[META: superar el modelo de referencia en F1 / AUC-PR por ___ puntos]`.

## 2. Requerimientos analíticos

| # | Requerimiento | Fuente / consulta |
|---|---|---|
| R1 | Informe de calidad: cobertura por año y mes, nulos, valores inválidos, coherencia de estados, duplicados | `01_calidad.sql` |
| R2 | KPI de puntualidad por aerolínea (dashboard) con filtros de fecha y aerolínea | `02_puntualidad_aerolineas.sql` (2.1, 2.3) |
| R3 | Mapa geográfico por aeropuerto (con filtros de fecha y aeropuerto) | `03_aeropuertos.sql` (3.4; 3.5 si faltan coordenadas) |
| R4 | Distribución de retrasos (histograma y categorías) | `07_programado_vs_real.sql` (7.5, 7.6) |
| R5 | Comparación programado vs. real (duración y horas) | `07_programado_vs_real.sql` (7.1 a 7.4) |
| R6 | Ranking de aerolíneas y de aeropuertos, con mínimo de volumen y regionales separados | `02` (2.1) y `03` (3.1 a 3.3) |
| R7 | Estacionalidad: mes, día de semana, hora, feriados, temporada | `04_estacionalidad.sql` |
| R8 | Participación de causas de retraso y análisis de clima/geografía | `05_causas_retraso_clima.sql` |
| R9 | Cancelaciones y desvíos por año, causa, aerolínea y aeropuerto | `06_cancelaciones.sql` |
| R10 | Efecto COVID aparte (2019 vs. 2020, por mes) | `08_covid_2020.sql` |
| R11 | Modelo de clasificación de retraso de llegada (24) y de cancelación (25) con partición temporal | `03_plan_modelos.md` |
| R12 | Filtros por fecha, aerolínea y aeropuerto en el dashboard (todas las consultas filtran por `fecha_id`) | todas |
| R13 | Los números del dashboard y del informe deben salir de las mismas definiciones (tabla de la sección 5) | este documento |

## 3. Supuestos y limitaciones

1. **Pregunta 24** = modelo de retraso de llegada (clasificación). **Pregunta 25** = cancelaciones, evento raro (~1.9 % en el periodo, ~6 % en 2020): reportar precisión y recall, no solo accuracy.
2. **Fuga de información**: no usar `retraso_salida` (DepDelay), `hora_salida_real` (DepTime), `taxi_out` (TaxiOut), WheelsOff ni nada que se conozca al despegar o después.
3. **Porcentajes**: cada uno dice su universo (denominador). Puntualidad sobre operados; cancelación sobre programados; causas solo sobre vuelos con retraso de llegada >= 15 min.
4. **COVID**: `periodo_covid = true` desde 2020-03-01 (supuesto). 2020 se trata aparte en tendencias; en el modelo se discute el sesgo.
5. **Coordenadas**: `dim_airport.latitud/longitud` pueden ser NULL. Las consultas del mapa funcionan igual (devuelven NULL y marcan `sin_coordenadas`); la consulta 3.6 mide cuántos vuelos quedarían fuera del mapa. Pendiente: cargar las coordenadas.
6. **Tipo de aerolínea**: mientras no exista `dw.dim_airline.tipo` (viene de `docs/catalogo_aerolineas.csv`, de Andoni), las consultas usan una CTE temporal con `-- TODO: reemplazar por dw.dim_airline.tipo cuando exista`. Códigos dudosos en el encabezado de `02_puntualidad_aerolineas.sql` (clasificación discutible de AS, B6, HA, VX, F9; códigos regionales XE, CP, ZW, QX, AX, C5, G7, 9K, KS por confirmar).
7. **Cobertura de aerolíneas**: Spirit (NK) solo desde 2015; Allegiant (G4) y Republic (YX) desde 2018. Fusiones: Continental CO a UA, AirTran FL a WN, US Airways US a AA, Virgin America VX a AS. Avisarlo siempre que se compare 2010 vs. 2020 (la consulta 02/2.5 compara solo aerolíneas presentes en ambos años). Regionales (SkyWest OO, Envoy MQ, ExpressJet EV, Endeavor 9E, PSA OH, Mesa YV, Republic YX, etc.) se rankean aparte.
8. **"A tiempo"** sigue el criterio BTS (< 15 min). Hay vuelos operados con `retraso_llegada` nulo que la regla de `20_fact_flights.sql` clasifica como 'A tiempo'; se miden en `01_calidad.sql` (1.5 y 1.9) y deben ser ~0.
   **No confundir:** `categoria_retraso = 'Sin retraso'` significa <= 0 min (no < 15) y no equivale a `estado_vuelo = 'A tiempo'`. Se usa en 02/2.4 y 07/7.6 con alias propio. Resuelto el 2026-11-27: Data Engineering la renombró (antes 'A tiempo') en `20_fact_flights.sql` y en la base con `sql/maintenance/renombrar_categoria_sin_retraso.sql` (42.2 M vuelos).
9. Las horas (`hora_salida_prog`, etc.) son hora local de cada aeropuerto; la estandarización de zona horaria depende de `dim_airport.zona_horaria` (puede ser NULL).
10. `retraso_clima` solo mide el WeatherDelay de BTS (subestima el efecto total del clima).

## 4. Aviso para comparaciones entre años

| Aerolínea / código | Situación | Efecto al comparar |
|---|---|---|
| Spirit (NK) | solo desde 2015 | no existe en 2010-2014 |
| Allegiant (G4), Republic (YX) | desde 2018 | no existen antes de 2018 |
| Continental (CO) | se fusiona en United (UA) | UA 2010 y UA 2020 no son la misma empresa |
| AirTran (FL) | se fusiona en Southwest (WN) | idem |
| US Airways (US) | se fusiona en American (AA) | idem |
| Virgin America (VX) | se fusiona en Alaska (AS) | idem |

## 5. KPI para el dashboard (Melani): definición única

Todas las tarjetas, gráficos y tablas del dashboard deben usar estas definiciones. Los porcentajes se muestran en escala 0-100 con el universo en la etiqueta.

| KPI | Nombre en SQL | Fórmula | Universo (denominador) | Dónde se calcula |
|---|---|---|---|---|
| KPI-1 Puntualidad | `pct_a_tiempo_sobre_operados` | `count(estado_vuelo='A tiempo') / count(operados) * 100` | vuelos operados (no cancelados ni desviados) | 02, 03, 04, 08 |
| KPI-2 Retraso de llegada típico | `mediana_retraso_llegada_min` | `percentile_cont(0.5)` de `retraso_llegada` | vuelos operados con `retraso_llegada` no nulo | 02, 04, 07 |
| KPI-3 Cancelación | `pct_cancelados_sobre_programados` | `count(cancelado) / count(*) * 100` | todos los vuelos programados | 02, 04, 06, 08 |
| KPI-4 Salida retrasada | `pct_salida_retrasada_15_sobre_operados` | `count(retraso_salida_15) / count(retraso_salida_15 no nulo) * 100` | vuelos operados | 03 |
| KPI-5 Participación de causa | `pct_<causa>_sobre_min_retraso_15` | `sum(minutos causa) / sum(minutos de las 5 causas) * 100` | operados con `retraso_llegada >= 15` | 05, 08 |
| KPI-6 Duración real vs. programada | `mediana_diferencia_real_menos_programado_min` | `percentile_cont(0.5)` de `tiempo_real - tiempo_programado` | operados con ambos tiempos > 0 | 07 |
| KPI-7 Volumen | `vuelos_programados`, `variacion_vuelos_pct_vs_2019` | `count(*)`; `(v2020 - v2019) / v2019 * 100` por mes | todos los vuelos programados | 01, 04, 08 |
| KPI-8 Desvío | `pct_desviados_sobre_programados` | `count(desviado) / count(*) * 100` | todos los vuelos programados | 02, 06 |

Reglas de visualización: ranking de aerolíneas por tipo (regional / bajo costo / tradicional); rankings de aeropuertos con mínimo de vuelos indicado en la nota del gráfico; 2020 señalado con `periodo_covid`; mapa con aviso "aeropuertos sin coordenadas" mientras falten.

## 6. Estado de las consultas

Los 8 archivos de `sql/analisis/` corren sin error sobre Postgres 16. **Corrida completa del 2026-11-27 sobre los 67,249,397 vuelos: 66 de 66 consultas OK en 78 min** (las que recorren toda la tabla tardan ~65 s; las de un año, 1-12 s). Los valores reales están en `04_hallazgos.md` y cuadran con los marts del dashboard (`05_conciliacion_marts.md`). Los mínimos de volumen están calibrados para la base completa; con muestras pequeñas pueden devolver 0 filas (no es un error).

Para correrlas todas contra el servidor (túnel SSH `ssh -N -L 5432:localhost:5432 ubuntu@100.55.222.111`, variables `PG*` de psql) usar `sql/analisis/correr_todo.sh`: guarda un CSV por consulta y `tiempos.csv` en `sql/analisis/resultados/AAAAMMDD/` (no se versiona).
Opciones: `--anio AAAA` (no modifica las consultas con rango propio, como 2010-2020-02 o 2019-2020) y `--solo 02`.
