# Columnas seleccionadas de BTS: propuesta inicial

**Fuente:** BTS TranStats, tabla *Reporting Carrier On-Time Performance (1987-present)*.
**Rango del Grupo 2:** enero 2010 a diciembre 2020.

Se seleccionaron 46 de las ~110 columnas, cubriendo las 8 categorías que pide el enunciado. Esta lista es la base del **diccionario de datos** (Data Administrator) y se puede ajustar cuando el grupo cierre las preguntas de negocio: agregar o quitar una columna solo requiere editar `COLUMNS` en `etl/config.py` y `sql/init/01_raw_flights.sql`.

| Categoría | Columna BTS | Columna en `raw.flights` | Tipo | Justificación |
|---|---|---|---|---|
| Time Period | Year, Quarter, Month, DayofMonth, DayOfWeek | year, quarter, month, day_of_month, day_of_week | entero | Patrones estacionales, por trimestre y por día de la semana |
| Time Period | FlightDate | flight_date | fecha | Llave de la partición y de `dim_fecha` |
| Airline | Reporting_Airline | reporting_airline | texto | Código único de aerolínea; base de `dim_airline` y del ranking de puntualidad |
| Airline | DOT_ID_Reporting_Airline | dot_id_reporting_airline | entero | Identificador estable de la aerolínea |
| Airline | Tail_Number | tail_number | texto | Matrícula del avión; permite estudiar el retraso encadenado de un mismo avión |
| Airline | Flight_Number_Reporting_Airline | flight_number | entero | Identifica rutas recurrentes |
| Origin/Destination | OriginAirportID, DestAirportID | origin_airport_id, dest_airport_id | entero | ID estable de aeropuerto (el código IATA puede cambiar); llave de `dim_airport` |
| Origin/Destination | Origin, Dest | origin, dest | texto | Código IATA para mostrar y para cruzar con coordenadas |
| Origin/Destination | OriginCityName, OriginState, DestCityName, DestState | origin_city_name, … | texto | Análisis geográfico por ciudad y estado |
| Departure | CRSDepTime, DepTime | crs_dep_time, dep_time | hhmm | Comparación programada vs. real (requisito del dashboard) |
| Departure | DepDelay, DepDel15 | dep_delay, dep_del15 | real, bool | Retraso de salida en minutos y bandera oficial de ≥15 min |
| Departure | DepTimeBlk | dep_time_blk | texto | Franja horaria de salida |
| Departure | TaxiOut | taxi_out | real | Congestión en pista del aeropuerto de origen |
| Arrival | CRSArrTime, ArrTime | crs_arr_time, arr_time | hhmm | Comparación programada vs. real |
| Arrival | ArrDelay, ArrDel15 | arr_delay, arr_del15 | real, bool | **Variable principal**: puntualidad oficial de BTS y posible variable objetivo de los modelos |
| Arrival | TaxiIn | taxi_in | real | Congestión en el aeropuerto de destino |
| Cancellations | Cancelled, CancellationCode | cancelled, cancellation_code | bool, texto | Tasa y causa de cancelación (A aerolínea, B clima, C NAS, D seguridad) |
| Diversions | Diverted, DivAirportLandings, DivReachedDest | diverted, … | bool, entero | Vuelos desviados y si llegaron al destino |
| Flight Summaries | CRSElapsedTime, ActualElapsedTime, AirTime | crs_elapsed_time, … | real | Duración programada vs. real |
| Flight Summaries | Distance | distance | real | Relación entre distancia y retraso |
| Cause of Delay | CarrierDelay, WeatherDelay, NASDelay, SecurityDelay, LateAircraftDelay | carrier_delay, … | real | Causa del retraso. **WeatherDelay cubre el objetivo de impacto del clima** sin depender de una fuente externa |
| Gate Return | FirstDepTime, TotalAddGTime, LongestAddGTime | first_dep_time, … | hhmm, real | Vuelos que regresaron a la puerta antes de despegar |

## Notas para el informe de calidad de datos

- **Causas de retraso:** BTS solo las reporta cuando `ArrDelay >= 15`. En los demás vuelos vienen vacías, y eso es lo esperado, no un problema de calidad.
- **Horas:** vienen en formato `hhmm` y en **hora local** de cada aeropuerto. Para estandarizar la zona horaria (requisito de Data Preparation) se necesita la zona de cada aeropuerto (`ref.airport_coords.timezone`).
- **Hora 2400:** BTS usa `2400` para medianoche. En la tabla de hechos el bloque horario se calcula con `mod(hora / 100, 24)`.
- **Vuelos cancelados:** no tienen hora real ni retraso de llegada. **Vuelos desviados:** no tienen retraso de llegada.
- **2020 (COVID):** `dim_fecha.periodo_covid = true` desde el 2020-03-01, para analizarlo aparte o filtrarlo. El supuesto está documentado.

## Reglas de negocio aplicadas en `dw.fact_flights`

| Campo | Regla |
|---|---|
| estado_vuelo | Cancelado > Desviado > Sin dato (operado sin `arr_del15`, ~969 vuelos) > Retrasado (`arr_del15`) > A tiempo. Criterio oficial de BTS: un vuelo está a tiempo si llega con menos de 15 min de retraso |
| retraso_total | Minutos de retraso positivo en la llegada. No se suma el de salida porque el de llegada ya lo acumula |
| categoria_retraso | A tiempo (≤0), Leve (1–14), Moderado (15–59), Severo (60–179), Extremo (≥180) |
| bloque_salida_id | Hora programada de salida, de 0 a 23 |
