# Hallazgos del análisis (Data Understanding y Análisis final) — BORRADOR

> Redactado por el Data Analyst con las cifras reales de la corrida completa del 2026-11-27
> (66 consultas de `sql/analisis/` sobre los 67,249,397 vuelos de `dw.fact_flights`, 2010-2020).
> Los CSV están en `sql/analisis/resultados/20261127_completo/` (no se versionan; se regeneran con
> `correr_todo.sh`). Cada cifra cita su consulta entre corchetes, p. ej. [2.1].
>
> Sigue la estructura de `02_esqueleto_informe.md`. Definiciones y universos: `01_preguntas_kpis.md`.
> Coherencia con el dashboard: `05_conciliacion_marts.md` (55 de 55 revisiones de cálculo cuadran; falta cargar las coordenadas).
>
> Convención de redacción: **Dato** = sale directo de la consulta. **Hipótesis** = interpretación
> que el dato sugiere pero no prueba (se presenta así en el informe).

## Avisos que acompañan a todas las cifras

- **Puntualidad (KPI-1)** = llegada con menos de 15 min de retraso, **sobre vuelos operados** (ni cancelados ni desviados). **Cancelación (KPI-3)** = sobre vuelos **programados**. **Causas de retraso (KPI-5)** = sobre minutos de vuelos operados con retraso de llegada >= 15 min.
- **Estacionalidad** (meses, días, horas, feriados) se calcula con **2010-01 a 2020-02** para que la pandemia no la distorsione. Las tendencias por año muestran 2020 aparte.
- **Aerolíneas que no cubren todo el periodo**: Spirit (NK) 2015-2020; Allegiant (G4) y Republic (YX) 2018-2020; Continental (CO) y ExpressJet XE 2010-2011; AirTran (FL) 2010-2014; US Airways (US) hasta jun-2015; Virgin America (VX) 2012 a mar-2018. Además hay regionales con años sin datos: Endeavor 9E (solo 2010, 2013 y 2018-2020), Envoy MQ (sin 2016-2017), PSA OH (2010 y 2018-2020), Mesa YV (sin 2014-2017) [1.12, 2.2]. **Un promedio del periodo de una aerolínea que solo existe en 2018-2020 incluye 2020, que fue un año atípicamente puntual.**

---

## PARTE I. Data Understanding

### 2.1 Volumen y cobertura [1.1, 1.2, 1.3]

- **Dato**: 67,249,397 vuelos programados en 132 meses, **sin meses ni días faltantes** (1.2 y 1.3 vacías). Coincide con el total esperado de `raw.flights`.
- **Dato**: 65,790,547 operados (97.83 %), 1,302,027 cancelados (1.94 %) y 156,836 desviados (0.23 %), todos sobre programados.
- **Dato**: el volumen bajó de 6.45 M (2010) a 5.67 M (2017) y **saltó a 7.21 M en 2018 (+1,531,574)**. Seis aerolíneas que no tenían vuelos en 2017 (G4, YX, OH, 9E, MQ, YV) aportan 1,447,824 vuelos en 2018: **el 94.5 % del salto** [1.12, 6.8].
- **Implicación**: la serie de volumen **no mide crecimiento del tráfico** entre 2017 y 2018; mide un cambio en las aerolíneas que reportan a BTS. En el informe y el dashboard, el volumen anual debe llevar esta nota o compararse solo con aerolíneas presentes todo el periodo.

### 2.2 Estados del vuelo [1.9, 4.1, 6.1]

| Estado | Vuelos | % sobre programados |
|---|---:|---:|
| A tiempo (< 15 min) | 53,749,985 | 79.93 |
| Retrasado (>= 15 min) | 12,040,210 | 17.90 |
| Cancelado | 1,302,027 | 1.94 |
| Desviado | 156,823 | 0.23 |
| Sin dato (operado sin `retraso_llegada`) | 352 | 0.0005 |

Sobre operados, la puntualidad del periodo es **81.70 %**; sin 2020 (2010-01 a 2020-02), **81.18 %**.

### 2.3 Distribución del retraso de llegada [1.7, 7.5, 7.7]

- **Dato**: mediana **-5 min** (la mitad de los vuelos llega antes de hora), p25 -14, p75 +7, p95 +66, p99 +168, p99.9 +393, máximo 3,864 min (64 h). El promedio (4.2 min) es mayor que la mediana: **distribución muy asimétrica a la derecha**.
- **Dato**: 61.9 % de los operados llega antes de la hora programada; 19.8 % entre 0 y 14 min tarde; 5.7 % llega con 60 min o más de retraso y 0.4 % con 4 h o más [7.5].
- **Implicación para el dashboard**: los marts solo permiten **promedios** (no medianas). El retraso promedio sobrestima el retraso típico; usar el % a tiempo como métrica principal y el promedio solo como apoyo, con nota.

### 2.4 Categorías de retraso [7.6]

- **Dato**: la categoría **Extremo** pasó de 0.60 % de los operados (2010) a **1.25 % (2019)**, y el p99 del retraso de 149 a **199 min** [7.7]. En el mismo periodo la mediana mejoró de -4 a -6 min.
- **Hallazgo**: **el vuelo típico llega mejor, pero los retrasos graves son más frecuentes y más largos.** El KPI-1 (que solo mira el umbral de 15 min) no capta este deterioro; conviene mostrar también el % Severo + Extremo.

### 2.5 Aerolíneas [1.12, 2.1]

22 códigos de aerolínea. Los volúmenes más grandes: Southwest (13.3 M), Delta (9.0 M), American (7.7 M), SkyWest (7.2 M), United (5.4 M). Clasificación por tipo (CTE de las consultas) **idéntica** a `dim_airline.tipo` del mart (22 de 22).

### 2.6 Aeropuertos y rutas [3.3, 3.7]

394 aeropuertos. Los 30 más grandes concentran el **65.8 %** de los vuelos operados. Atlanta (4.08 M), O'Hare (3.12 M), Dallas/Fort Worth (2.74 M), Denver (2.47 M), Los Ángeles (2.25 M).

### 2.7 Distancia y duración [5.8, 7.3]

- **Dato**: la puntualidad casi no cambia con la distancia (82.24 % en < 500 millas, 80.14 % en >= 2,500 millas).
- **Dato**: los vuelos más largos recuperan más tiempo en el aire (mediana del cambio en vuelo de -5 min en < 500 millas a -9 min en 1,500-2,499 millas).

### 2.8 a 2.10 Estacionalidad, causas y cancelaciones

Ver Parte II, hallazgos 5.2, 5.4 y 5.5.

### 2.11 Relaciones entre variables

**Pendiente**: la matriz de correlación se calcula sobre una muestra de `dw.fact_flights` (ver `03_plan_modelos.md`, sección 10). Correlación ya disponible a nivel agregado: entre estados, minutos de clima por vuelo y puntualidad tienen **r = -0.42** (Pearson y Spearman) [5.6].

### 4. Informe de calidad de datos [1.4 a 1.11, 5.9]

| # | Revisión | Resultado | Filas afectadas | Impacto | Acción |
|---|---|---|---:|---|---|
| Q1 | Meses o días sin datos | Ninguno | 0 | — | — |
| Q2 | Duplicados (llave natural, 2019) | Ninguno | 0 | — | Extender a los demás años si hay tiempo |
| Q3 | Hechos sin dimensión (FK) | Ninguno | 0 | — | — |
| Q4 | Coherencia `estado_vuelo` vs. cancelado / desviado / retraso | 0 incoherencias | 0 | — | — |
| Q5 | Cancelado **y** desviado a la vez | Se clasifican como Cancelado | 13 | Bajo | Documentar |
| Q6 | Operados sin `retraso_llegada` (`estado_vuelo = 'Sin dato'`) | 350 en 2018, 1 en 2017, 1 en 2020 | 352 | Bajo | Ya excluidos de "A tiempo"; cuentan en el denominador de operados |
| Q7 | Retraso de llegada o salida > 24 h | Crecen con los años: 4 (2010) a 170 (2019) | 617 llegada | Bajo | Conservar (son reales, cola de la distribución); excluir en el modelo si distorsionan |
| Q8 | Adelanto de llegada > 2 h | | 18 | Bajo | Conservar |
| Q9 | `tiempo_programado <= 0` | 5 en 2018, 1 en 2020 | 6 | Bajo | Excluir del KPI-6 (las consultas ya lo hacen) |
| Q10 | Causas que no suman el retraso de llegada | | 2 | Bajo | Ignorar |
| Q11 | Retraso >= 15 sin ninguna causa | | 2 | Bajo | Ignorar |
| Q12 | Causas informadas con retraso < 15 min | Ninguna | 0 | — | — |
| Q13 | Bloque horario nulo | | 1 | Bajo | — |
| Q14 | Nulos esperados | `retraso_llegada` 1.4-2.4 % por año (= cancelados + desviados; 6.2 % en 2020); causas ~81 % (solo existen con retraso >= 15) | — | — | Documentar como esperados |
| Q15 | Matrícula nula | 0.2-0.5 % por año; **3.3 % en 2020** | — | Bajo | No se usa en KPI |
| Q16 | **Aeropuertos sin latitud/longitud ni zona horaria** | **394 de 394** | 100 % de los vuelos | **Alto para el mapa** | Cargar coordenadas (Data Engineering). Mientras tanto, mapa por estado [3.5] |
| Q17 | Aerolíneas con años sin datos (2.5 arriba) | 9E, MQ, OH, YV, + altas y bajas | — | **Medio** | Avisos en cada comparación entre años |

---

## PARTE II. Análisis final e insights

### 5.1 Aeropuertos con más retrasos (Objetivo 1) [3.1, 3.2, 3.3, 3.5, 3.7]

**Salidas retrasadas (KPI-4, sobre operados del aeropuerto de origen, mínimo 5,000 operados).** Global del periodo: 17.64 %.

| Grandes (top 30 por volumen), peores | % salida retrasada | | Grandes, mejores | % |
|---|---:|---|---|---:|
| Chicago Midway (MDW) | 25.39 | | Salt Lake City (SLC) | 12.34 |
| Newark (EWR) | 23.57 | | Seattle (SEA) | 14.11 |
| Dallas Love Field (DAL) | 22.66 | | Minneapolis (MSP) | 14.31 |
| Chicago O'Hare (ORD) | 22.15 | | Washington National (DCA) | 15.46 |
| San Francisco (SFO) | 21.70 | | Detroit (DTW) | 15.80 |

- **Dato**: los peores de todo el ranking son aeropuertos pequeños: North Bend/Coos Bay OTH (37.12 %), Arcata ACV (26.78 %), Modesto MOD (25.42 %), Chico CIC (24.91 %), que envían entre el 76 % y el 100 % de sus vuelos a San Francisco [mart_rutas_anual].
- **Dato**: los 30 más grandes (65.8 % de los vuelos) tienen **18.77 %** de salidas retrasadas; el resto, **15.47 %**. **Los hubs son peores en promedio**, aunque los casos extremos sean pequeños.
- **Dato**: en llegadas (KPI-1 por destino) los grandes peores son Newark (73.27 % a tiempo), San Francisco (74.47 %), LaGuardia (76.02 %), JFK (78.66 %) y Boston (78.76 %).
- **Dato**: de las 30 rutas con peor puntualidad, **23 tocan Newark (16) o San Francisco (7)**; la peor es EWR-OKC con 56.16 % a tiempo.
- **Dato (estados)**: peores Nueva Jersey (23.40 %), Illinois (22.60 %), Maryland (21.32 %), Colorado (19.95 %) y Nevada (19.43 %); mejores Hawái (8.35 %), Montana (9.84 %), Alaska (10.73 %), Idaho (11.70 %) y Utah (12.27 %).
- **Hipótesis 1 (congestión en tierra)**: Nueva York y Newark tienen las medianas de taxi-out más altas (JFK 23 min, LGA 22, EWR 19) frente a ~10 min en Midway. Su problema es de capacidad del aeropuerto y del espacio aéreo, no de la aerolínea.
- **Hipótesis 2 (propagación en bases de Southwest)**: Midway, Hobby, Love Field y Baltimore, todos bases fuertes de Southwest, están entre los peores en salidas con taxi-out bajo. Southwest es la aerolínea con mayor peso de "avión tardío" (51.7 % de sus minutos de retraso [5.4]): rotaciones cortas que propagan el retraso durante el día.

### 5.2 Estacionalidad (Objetivo 2) [4.1 a 4.9, 7.2] — periodo 2010-01 a 2020-02

| Dimensión | Peor | Mejor |
|---|---|---|
| Mes | Junio 77.14 %, Julio 77.69 %, Diciembre 78.49 % | Septiembre 85.09 %, Noviembre 84.83 %, Octubre 84.49 % |
| Temporada | Verano 78.24 % | Otoño 84.80 % |
| Día | Jueves 79.40 %, Viernes 79.60 % | Sábado 83.84 % |
| Hora de salida | 18:00-18:59 73.54 % | 05:00-05:59 92.34 % |
| Día x franja | Jueves noche 71.07 % | Miércoles madrugada 91.80 % |

- **Hallazgo principal: la hora del día es el factor estacional más fuerte.** La puntualidad cae casi en línea recta de 92.3 % (5 a. m.) a 73.5 % (6 p. m.): **19 puntos**, más que la diferencia entre el mejor y el peor mes (8 puntos). El p90 del retraso pasa de 10 min a 53 min [7.2]. La cancelación también sube con la hora (1.34 % a las 9 a. m., 2.01 % a las 6 p. m.).
- **Hipótesis**: retraso acumulado en la rotación del avión (coherente con que "avión tardío" sea la primera causa, 5.4).
- **Dos picos de retraso al año**: verano (tormentas, más vuelos) e invierno (nieve, más cancelaciones: enero 2.69 % y febrero 2.91 %).
- **Feriados**: no empeoran la operación. Los feriados entre semana tienen 82.16 % a tiempo frente a 80.59 % de los días normales, con ~9 % menos vuelos por día [4.7]. Acción de Gracias es el mejor día del año (91.94 % a tiempo, 0.17 % cancelados); el peor feriado es Año Nuevo observado (70.14 %) y el Día de los Presidentes, en febrero (76.74 %, 2.89 % cancelados) [4.8].
- **Demanda semanal**: el pico está en las semanas 28 a 31 (julio, ~128 mil vuelos por semana) y el valle en las semanas 47 a 52 (~115 mil) [4.9].
- **Tendencia anual** (KPI-1): 81.4 % (2010) → 83.1 % (2012, mejor año pre-COVID) → **78.2 % (2014, peor año)** → 80.9 % (2019) → 90.2 % (2020). **No hay mejora sostenida entre 2010 y 2019.** Los peores meses fueron dic-2013 (71.06 %) y ene-2014 (72.71 %, 6.54 % cancelados), que coinciden con el vórtice polar (`docs/eventos_externos.csv`, E09).

### 5.3 Puntualidad por aerolínea (Objetivo 3) [2.1, 2.2, 2.4, 2.5, 6.3]

**Por tipo (periodo completo)**: tradicionales 83.27 % a tiempo y 1.39 % cancelados; regionales 80.73 % y **2.83 %**; bajo costo 80.47 % y 1.78 %. **Las regionales cancelan el doble que las tradicionales.**

**Ranking 2019** (último año normal; evita que 2020 favorezca a las aerolíneas recientes):

| Tradicional | % a tiempo | Bajo costo | % | Regional | % |
|---|---:|---|---:|---|---:|
| Hawaiian HA | 88.56 | Southwest WN | 82.44 | Endeavor 9E | 82.46 |
| Delta DL | 85.52 | Spirit NK | 81.09 | SkyWest OO | 81.23 |
| Alaska AS | 81.47 | Allegiant G4 | 79.38 | Republic YX | 80.75 |
| American AA | 78.89 | JetBlue B6 | 74.67 | PSA OH | 80.21 |
| United UA | 78.64 | Frontier F9 | 74.51 | Envoy MQ | 79.07 |
| | | | | Mesa YV | 78.83 |
| | | | | ExpressJet EV | 74.22 |

- **Dato (periodo completo)**: Hawaiian lidera todo el periodo (91.12 %); JetBlue (76.39 %) y Frontier (77.15 %) son las menos puntuales [2.1].
- **Dato (2010 vs. 2019, solo aerolíneas presentes ambos años [2.5])**: **Delta es la que más mejoró (+6.4 puntos, 79.15 % a 85.52 %)** y canceló solo 0.19 % en 2019 (la segunda más baja, tras Hawaiian con 0.16 %). Las que más empeoraron: United (-8.0), Frontier (-7.4), ExpressJet (-7.1), Alaska (-6.8) y Mesa (-6.4). United 2010 y United 2019 no son la misma empresa (fusión con Continental); OH 2010 era Comair.
- **Dato (gravedad [2.4])**: Southwest tiene muchos retrasos leves y moderados pero pocos extremos (0.49 %); Allegiant (1.64 %), JetBlue (1.41 %) y ExpressJet (1.34 %) tienen la mayor proporción de retrasos extremos.
- **Dato (holgura de itinerario [7.4])**: United y Delta programan con más colchón (mediana real - programado de -9 y -7 min); en Southwest solo 18.5 % de los vuelos dura más de lo programado, frente a 50 % en Hawaiian.
- **Hipótesis**: parte de la puntualidad de una aerolínea viene de cómo programa (colchón), no solo de cómo opera. Comparar puntualidad sin considerar la holgura favorece a quien programa vuelos más largos.

### 5.4 Clima y geografía (Objetivo 4) [5.1 a 5.8, 6.2]

**Participación de causas sobre los 721.8 M de minutos de retraso (vuelos con retraso >= 15 min, 2010-2020)** [5.1]:

| Avión tardío | Aerolínea | NAS (sistema) | Clima | Seguridad |
|---:|---:|---:|---:|---:|
| 39.95 % | 31.23 % | 24.06 % | 4.74 % | 0.14 % |

- **Hallazgo**: **el 71 % de los minutos de retraso tiene causas que la aerolínea controla o puede amortiguar** (aerolínea + avión tardío). El clima explícito pesa menos del 5 %.
- **Límite**: `retraso_clima` solo registra clima extremo; el clima no extremo cuenta como NAS y su efecto se arrastra como avión tardío. **El 4.74 % es un piso, no el efecto total del clima.**
- **El clima sí domina las cancelaciones**: es la primera causa de cancelación todos los años de 2010 a 2019 (42 % a 59 % de los cancelados) [6.2]. Los 10 días con más cancelaciones antes de 2020 son tormentas y huracanes: 1-feb-2011 (33.6 %), huracán Sandy 29-oct-2012 (27.8 %), 13-feb-2014 (27.5 %), 14-mar-2017 (25.0 %), tormenta Jonas 23-ene-2016 (24.5 %) [mart_serie_diaria, eventos E03, E05, E27, E28, E13].
- **Meses**: el clima pesa más en junio-julio (0.74 min de clima por vuelo operado) y en enero (0.66); menos en octubre (0.26) [5.5].
- **Geografía**: más minutos de clima por vuelo en las Dakotas (SD 1.13, ND 1.02) e Illinois (0.93); menos en Hawái (0.09), Puerto Rico (0.12), Arizona (0.17) y California (0.17) [5.6]. Entre estados, más clima se asocia con menos puntualidad (r = -0.42), pero **California es poco afectada por el clima y aun así tiene puntualidad media (81.8 %)**: ahí pesa la congestión (SFO, LAX).
- **Distancia**: casi sin relación con la puntualidad (2 puntos entre el rango más corto y el más largo) [5.8].
- **Tendencia**: la participación del clima en los minutos de retraso subió de 4.40 % (2010) a 5.51 % (2019) y 7.04 % (2020) [5.2].

### 5.5 Cancelaciones (Objetivo 5) [6.1 a 6.9]

- **Dato**: 1.94 % de cancelados en todo el periodo; **1.62 % antes de COVID**; entre 1.17 % (2016) y 2.18 % (2014); **5.99 % en 2020** [6.1].
- **Dato (causa)**: clima 42-59 %, aerolínea 22-38 %, NAS 13-23 %, seguridad < 0.4 % (2010-2019). La participación de la aerolínea bajó de 37.2 % (2010) a 28.1 % (2019).
- **Dato (2020)**: el **84.4 % de las cancelaciones de 2020 tiene el código D (seguridad)**: 97,858 de 110,187 en marzo y 125,371 de 130,078 en abril. El código viene así de la fuente BTS (`CancellationCode`). **No son incidentes de seguridad**: BTS no tiene un código para la pandemia y las aerolíneas usaron D. Hay que **excluir 2020 de cualquier análisis de causas de cancelación** o explicarlo.
- **Dato (aeropuertos)**: las tasas más altas están en aeropuertos pequeños de montaña o clima extremo: Sun Valley SUN (10.14 %), Modesto MOD (8.45 %), Aspen ASE (7.66 %) [6.4].
- **Dato (franja)**: la noche cancela más que la mañana todos los días de la semana (p. ej. lunes 2.04 % frente a 1.52 %) [6.6].
- **Desvíos**: 0.17 % a 0.26 % por año; evento todavía más raro que la cancelación [6.1, 6.8].
- **Implicación para el modelo (pregunta 25)**: la clase "cancelado" es entre 1.2 % y 2.2 % de los vuelos por año antes de 2020 (de 45 a 84 no cancelados por cada cancelado) y sube a 6 % en 2020 [6.9]. Un modelo que diga "nunca se cancela" tendría 98 % de exactitud: reportar precisión, recall y curva precisión-recall, y no entrenar con 2020 sin tratarlo aparte.

### 5.6 Efecto COVID (Objetivo 6) [8.1 a 8.7]

- **Dato**: ene-feb 2020 tenía **más** vuelos que 2019 (+4.0 % y +7.7 %). En marzo se programaron +2.6 %, pero se canceló el 17 %. Caída máxima en **mayo: -71.6 %** de vuelos frente a mayo de 2019. De julio a diciembre se estabilizó entre -40 % y -47 % [8.1].
- **Dato (semanal)**: el mínimo fue la semana 20 (27.1 % del volumen de 2019). Las cancelaciones superaron el 40 % en las semanas 13 a 15 (máximo diario 53.15 % el 30-mar-2020). **El año cerró en 55-66 % del volumen de 2019: no hubo recuperación a niveles previos** [8.3, 6.7].
- **Dato (mar-dic)**: 3.51 M de vuelos programados frente a 6.30 M (-44.4 %); cancelación 7.67 % frente a 1.63 %; puntualidad **91.80 %** frente a 81.17 %; mediana de retraso -11 min frente a -7 [8.2].
- **Hallazgo: la mejora de la puntualidad en 2020 no es solo efecto de composición.** Sí cambió la mezcla (más vuelos de mañana, menos de noche: 22.6 % a 18.6 % de los vuelos), pero **la puntualidad subió dentro de cada franja**: noche 74.24 % a 90.35 %, tarde 78.40 % a 91.25 %, mañana 87.09 % a 92.94 % [8.7]. Con menos vuelos desaparece la congestión que explica el deterioro a lo largo del día.
- **Dato (causas)**: en 2020 "avión tardío" bajó de 40.1 % a 26.0 % de los minutos de retraso y "aerolínea" subió de 30.8 % a 45.5 % [8.6]. Con menos rotaciones se propaga menos el retraso.
- **Dato (quién recortó más, mar-dic)**: ExpressJet -72.6 %, Hawaiian -62.2 %, JetBlue -61.7 %, United -60.1 %; quien menos, Allegiant -10.2 % (aunque canceló 17.3 %), Endeavor -23.7 % y Southwest -35.0 % [8.4]. Aeropuertos: Westchester HPN -79.4 %, **LaGuardia -71.0 %, JFK -65.4 %**, Washington National -63.2 %, Boston -60.8 %: **la zona de Nueva York y Washington fue la más afectada** [8.5].
- **Implicación**: 2020 no sirve como referencia de puntualidad ni de causas; se reporta aparte y se advierte en el dashboard (franja sombreada desde 2020-03-01).

### 5.7 Programado vs. real [7.1 a 7.4, 7.8]

- **Dato**: la duración real es sistemáticamente menor que la programada: mediana de -4 a -6 min cada mes de 2010 a 2019 y -7 min en 2019. Entre 26 % y 29 % de los vuelos dura más de lo programado, según la distancia [7.1, 7.3].
- **Dato**: la mediana mensual de la duración programada pasó de ~112 min (2010) a ~128 min (2017) [7.1]. **Hipótesis**: las aerolíneas añadieron colchón al itinerario, lo que mejora el KPI-1 sin que la operación sea más rápida (pregunta 19 del enunciado, *schedule padding*). Falta descartar que sea un cambio en la mezcla de rutas (controlar por distancia).
- **Excepción**: las rutas cortas de Hawái (entre islas) y Alaska no tienen colchón: duran 1-3 min más de lo programado [7.8].

### 5.8 Modelos (preguntas 24 y 25)

**Pendiente**: correr los modelos según `03_plan_modelos.md`. Datos útiles ya medidos: prevalencia de la clase positiva de la pregunta 24 (retraso de llegada >= 15) = 18.3 % de los operados; de la pregunta 25 = 1.2-2.2 % por año antes de 2020. Variables candidatas con efecto claro (conocidas antes del despegue): hora programada de salida (19 puntos de diferencia), mes, día de la semana, aerolínea, aeropuerto de origen y destino. La distancia aporta poco.

---

## 6. Insights (interpretación para el negocio)

1. **El retraso se fabrica a lo largo del día.** La puntualidad cae 19 puntos de la primera salida a la de las 6 p. m. y "avión tardío" es la primera causa (40 % de los minutos). Proteger las primeras rotaciones y dar holgura entre rotaciones en la tarde rinde más que cualquier acción por temporada.
2. **Pocos aeropuertos concentran el problema.** Newark y San Francisco aparecen en 23 de las 30 peores rutas; Nueva York, Newark, Chicago y San Francisco tienen los peores indicadores entre los grandes. Son cuellos de botella de capacidad (taxi-out alto) que afectan a toda la red.
3. **El clima explica las cancelaciones, no los retrasos.** Menos del 5 % de los minutos de retraso es clima explícito, pero el clima causa la mitad de las cancelaciones y los días de tormenta concentran los peores picos. Las cancelaciones se gestionan con planes de contingencia por tormenta; los retrasos, con la programación de la operación.
4. **La puntualidad del sector no mejoró de 2010 a 2019** (81 % al inicio y al final), y los retrasos graves (Extremo) se duplicaron. Las mejoras de algunas aerolíneas (Delta +6.4 puntos) se compensan con caídas de otras (United, Frontier, JetBlue).
5. **Comparar aerolíneas exige contexto**: tipo (las regionales cancelan el doble), años cubiertos (2020 infla a las recientes) y holgura de itinerario (programar más largo "compra" puntualidad).
6. **2020 demuestra el efecto de la congestión**: con 44 % menos vuelos, la puntualidad subió 10 puntos y subió en todas las franjas. Es un experimento natural que cuantifica cuánto del retraso normal se debe a la saturación del sistema.

## 7. Conclusiones (valor actual de cada objetivo)

| Objetivo | Valor actual | Meta |
|---|---|---|
| 1. Aeropuertos | KPI-4 global 17.64 %; hubs 18.77 % vs. resto 15.47 %; peor grande MDW 25.39 %, mejor SLC 12.34 % | `[META]` por definir con el equipo |
| 2. Estacionalidad | Meses críticos: junio, julio, diciembre; franja crítica 17:00-21:59 (73.5-75.3 %) | `[META]` |
| 3. Aerolíneas | Tradicional 83.27 %, bajo costo 80.47 %, regional 80.73 %. Brecha dentro del tipo (periodo): tradicional 10.9 pts, bajo costo 8.1, regional 5.4 | `[META]` |
| 4. Clima y geografía | Clima 4.74 % de los minutos de retraso; 71.2 % aerolínea + avión tardío; clima 42-59 % de las cancelaciones | `[META]` |
| 5. Cancelaciones | 1.94 % (periodo), 1.62 % (pre-COVID), 5.99 % (2020); desvío 0.23 % | `[META]` recall/precisión del modelo |
| 6. COVID | -44.4 % de vuelos mar-dic; peor mes mayo -71.6 %; sin recuperación en 2020 (máx. 66 % del volumen 2019) | `[META]` |

## 8. Recomendaciones (borrador)

- **Aerolíneas**: reforzar la holgura de rotación después de las 2 p. m. y en jueves y viernes; vigilar el % Severo + Extremo además del KPI-1.
- **Aeropuertos y autoridad (FAA)**: priorizar capacidad en EWR, LGA, JFK, ORD y SFO (taxi-out y NAS).
- **Pasajeros**: el vuelo más puntual es el primero de la mañana (92 %); evitar conexiones ajustadas por la tarde y en verano.
- **Monitoreo**: KPI-1, KPI-3 y % Severo + Extremo por hora y aeropuerto en el dashboard.

## 9. Limitaciones

- Sin coordenadas ni zona horaria de aeropuertos (Q16): el mapa usa estados.
- `retraso_clima` subestima el clima; no se cargaron datos climatológicos externos.
- Cambios en las aerolíneas que reportan a BTS (salto de 2018, años faltantes de regionales).
- Códigos de cancelación de 2020 (D) no reflejan la causa real.
- `periodo_covid` desde 2020-03-01 es un supuesto.
- Correlaciones a nivel de vuelo y modelos aún pendientes.
