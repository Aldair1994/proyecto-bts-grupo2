# Conciliación: consultas de análisis vs. vistas mart del dashboard

## Método

- **Objetivo** (requerimiento R13 de `01_preguntas_kpis.md`): que los números del dashboard (sobre `mart.*`) y los del informe (sobre `dw.fact_flights`) salgan iguales.
- `docs/analisis/conciliar_marts.py` recalcula cada KPI desde los CSV de las vistas (`docs/mart_*.csv`, commit b5e9bb2) **dividiendo sumas**, como las medidas DAX de `docs/marts.md`, y lo compara con los CSV de la corrida completa del 2026-11-27.
- **Tolerancia** para marcar OK: 0 en conteos; 0.011 puntos porcentuales en porcentajes (las consultas redondean a 2 decimales).
- Para repetirla: `python3 docs/analisis/conciliar_marts.py sql/analisis/resultados/<carpeta>` (termina con código 1 si alguna revisión no cuadra).

## Resultado

**Las 55 revisiones de cálculo cuadran.** Los conteos de los cinco marts por año son idénticos a
`dw.fact_flights`, y todos los porcentajes coinciden dentro del redondeo. La revisión 56 (coordenadas)
queda pendiente porque faltan los datos.

| # | Revisión | Comparados | Sin pareja | Diferencia máx. | Resultado | Detalle |
|---|---|---:|---:|---:|---|---|
| 1 | 1.1 vuelos_programados por año vs puntualidad_mensual_aerolinea | 11 | 0 | 0.0000 vuelos | OK |  |
| 2 | 1.1 cancelados por año vs puntualidad_mensual_aerolinea | 11 | 0 | 0.0000 vuelos | OK |  |
| 3 | 1.1 desviados por año vs puntualidad_mensual_aerolinea | 11 | 0 | 0.0000 vuelos | OK |  |
| 4 | 1.1 operados por año vs puntualidad_mensual_aerolinea | 11 | 0 | 0.0000 vuelos | OK |  |
| 5 | 1.1 vuelos_programados por año vs serie_diaria | 11 | 0 | 0.0000 vuelos | OK |  |
| 6 | 1.1 cancelados por año vs serie_diaria | 11 | 0 | 0.0000 vuelos | OK |  |
| 7 | 1.1 desviados por año vs serie_diaria | 11 | 0 | 0.0000 vuelos | OK |  |
| 8 | 1.1 operados por año vs serie_diaria | 11 | 0 | 0.0000 vuelos | OK |  |
| 9 | 1.1 vuelos_programados por año vs aeropuerto_mensual (Origen) | 11 | 0 | 0.0000 vuelos | OK |  |
| 10 | 1.1 cancelados por año vs aeropuerto_mensual (Origen) | 11 | 0 | 0.0000 vuelos | OK |  |
| 11 | 1.1 desviados por año vs aeropuerto_mensual (Origen) | 11 | 0 | 0.0000 vuelos | OK |  |
| 12 | 1.1 operados por año vs aeropuerto_mensual (Origen) | 11 | 0 | 0.0000 vuelos | OK |  |
| 13 | 1.1 vuelos_programados por año vs aeropuerto_mensual (Destino) | 11 | 0 | 0.0000 vuelos | OK |  |
| 14 | 1.1 cancelados por año vs aeropuerto_mensual (Destino) | 11 | 0 | 0.0000 vuelos | OK |  |
| 15 | 1.1 desviados por año vs aeropuerto_mensual (Destino) | 11 | 0 | 0.0000 vuelos | OK |  |
| 16 | 1.1 operados por año vs aeropuerto_mensual (Destino) | 11 | 0 | 0.0000 vuelos | OK |  |
| 17 | 1.1 vuelos_programados por año vs patron_dia_hora | 11 | 0 | 0.0000 vuelos | OK |  |
| 18 | 1.1 cancelados por año vs patron_dia_hora | 11 | 0 | 0.0000 vuelos | OK |  |
| 19 | 1.1 operados por año vs patron_dia_hora | 11 | 0 | 0.0000 vuelos | OK |  |
| 20 | 1.1 vuelos_programados por año vs rutas_anual | 11 | 0 | 0.0000 vuelos | OK |  |
| 21 | 1.1 cancelados por año vs rutas_anual | 11 | 0 | 0.0000 vuelos | OK |  |
| 22 | 1.1 operados por año vs rutas_anual | 11 | 0 | 0.0000 vuelos | OK |  |
| 23 | 2.1 vuelos operados por aerolínea | 22 | 0 | 0.0000 vuelos | OK |  |
| 24 | 2.1 % a tiempo sobre operados por aerolínea | 22 | 0 | 0.0050 pp | OK |  |
| 25 | 2.1 % cancelados sobre programados por aerolínea | 22 | 0 | 0.0048 pp | OK |  |
| 26 | tipo de aerolínea: CTE de 02 vs dim_airline.tipo del mart | 22 | 0 | 0 distintos | OK |  |
| 27 | 2.2 % a tiempo por aerolínea y año | 169 | 0 | 0.0050 pp | OK |  |
| 28 | 2.2 % cancelados por aerolínea y año | 169 | 0 | 0.0050 pp | OK |  |
| 29 | 2.4 % sin_retraso_0min por aerolínea | 22 | 0 | 0.0048 pp | OK |  |
| 30 | 2.4 % leve por aerolínea | 22 | 0 | 0.0047 pp | OK |  |
| 31 | 2.4 % extremo por aerolínea | 22 | 0 | 0.0050 pp | OK |  |
| 32 | 4.1 % a tiempo por mes (serie_diaria) | 132 | 0 | 0.0050 pp | OK |  |
| 33 | 4.1 % cancelados por mes (serie_diaria) | 132 | 0 | 0.0049 pp | OK |  |
| 34 | 4.2 % a tiempo por mes del año, pre-COVID | 12 | 0 | 0.0046 pp | OK |  |
| 35 | 4.4 % a tiempo por día de la semana (patron_dia_hora) | 7 | 0 | 0.0045 pp | OK |  |
| 36 | 4.5 % a tiempo por hora de salida (patron_dia_hora) | 24 | 0 | 0.0048 pp | OK |  |
| 37 | 4.5 % cancelados por hora de salida (patron_dia_hora) | 24 | 0 | 0.0048 pp | OK |  |
| 38 | 4.7 % a tiempo feriado x fin de semana | 4 | 0 | 0.0044 pp | OK |  |
| 39 | 4.8 % a tiempo por feriado | 14 | 0 | 0.0047 pp | OK |  |
| 40 | 3.1 % salida retrasada 15 por aeropuerto de origen | 50 | 0 | 0.0049 pp | OK |  |
| 41 | 3.1 vuelos operados por aeropuerto de origen | 50 | 0 | 0.0000 vuelos | OK |  |
| 42 | 3.3 % salida retrasada 15 por aeropuerto de origen | 30 | 0 | 0.0047 pp | OK |  |
| 43 | 3.3 vuelos operados por aeropuerto de origen | 30 | 0 | 0.0000 vuelos | OK |  |
| 44 | 3.2 % a tiempo por aeropuerto de destino | 50 | 0 | 0.0050 pp | OK |  |
| 45 | 3.4 (mapa) % a tiempo desde origen, todos los aeropuertos | 356 | 0 | 0.0050 pp | OK |  |
| 46 | 3.5 % salida retrasada 15 por estado | 52 | 0 | 0.0049 pp | OK |  Fuera de 3.5 por el mínimo de 5000 operados: DE (1138 operados). |
| 47 | 3.7 % a tiempo de las 30 peores rutas | 30 | 0 | 0.0049 pp | OK |  |
| 48 | 5.2 % minutos de causa aerolinea por año | 11 | 0 | 0.0098 pp | OK |  Universo distinto: el mart incluye minutos de causa de vuelos desviados. |
| 49 | 5.2 % minutos de causa clima por año | 11 | 0 | 0.0055 pp | OK |  Universo distinto: el mart incluye minutos de causa de vuelos desviados. |
| 50 | 5.2 % minutos de causa nas por año | 11 | 0 | 0.0073 pp | OK |  Universo distinto: el mart incluye minutos de causa de vuelos desviados. |
| 51 | 5.2 % minutos de causa avion_tardio por año | 11 | 0 | 0.0118 pp | OK |  Universo distinto: el mart incluye minutos de causa de vuelos desviados. |
| 52 | 6.2 cancelados por causa A y año | 11 | 0 | 0.0000 vuelos | OK |  |
| 53 | 6.2 cancelados por causa B y año | 11 | 0 | 0.0000 vuelos | OK |  |
| 54 | 6.2 cancelados por causa C y año | 11 | 0 | 0.0000 vuelos | OK |  |
| 55 | 6.2 cancelados por causa D y año | 11 | 0 | 0.0000 vuelos | OK |  |
| 56 | aeropuertos con latitud/longitud en mart.aeropuerto_mensual | 394 | 0 | 394 sin coordenadas | PENDIENTE |  |

55 de 55 revisiones de cálculo cuadran; 1 pendiente(s) de datos.

## Diferencias explicadas (no son errores)

1. **3.5, estados**: la consulta exige al menos 5,000 vuelos operados por estado; Delaware (1,138) solo aparece en el mart. Si el dashboard muestra todos los estados, DE tendrá un porcentaje con pocos vuelos.
2. **5.2, causas de retraso**: el mart suma minutos de causa de **todos** los vuelos; la consulta, solo de operados con retraso >= 15 min. La diferencia (minutos de causa en vuelos desviados) es de 0.01 puntos como máximo. Si se quiere el universo exacto del KPI-5, el mart podría filtrar `NOT desviado` en `min_causa_*`; no cambia ninguna conclusión.

## Notas para el dashboard (Melani)

1. **Mapa**: `latitud` y `longitud` vienen vacías para los 394 aeropuertos. Hasta que se carguen, usar el mapa por **estado** (campo `estado` de `mart.aeropuerto_mensual`, rol `Origen`).
2. **Retraso promedio vs. mediana**: el mart solo permite promedios. El promedio del periodo es +4.2 min y la mediana -5 min (distribución muy asimétrica). Usar "% a tiempo" como KPI principal y rotular el promedio como "retraso promedio (incluye adelantos)".
3. **Volumen 2018**: el salto de +1.53 M vuelos en 2018 se debe en 94.5 % a seis aerolíneas que empiezan a aparecer ese año (G4, YX, OH, 9E, MQ, YV). Poner nota en el gráfico de volumen anual.
4. **Causas de cancelación 2020**: 84 % viene con código D (seguridad) porque las aerolíneas usaron ese código para la pandemia. Excluir 2020 del gráfico de causas o anotarlo.
5. **Ranking de aerolíneas**: para comparar en igualdad, filtrar 2019 (o 2018-2019); con el periodo completo, G4, YX y NK salen favorecidas porque solo existen en los años recientes, que incluyen 2020.
6. **Tipo de aerolínea**: `tipo_aerolinea` del mart coincide con la clasificación usada en el análisis (22 de 22).
