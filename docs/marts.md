# Capa de consumo para el dashboard (esquema `mart`)

Vistas materializadas que resumen los 67 millones de vuelos de `dw.fact_flights` en unas pocas miles de filas. Se crean con `sql/build/30_marts.sql` (paso `marts` del pipeline) y se recrean cada vez que se recarga la tabla de hechos.

**En Power BI conviene IMPORTAR estas vistas** en lugar de usar DirectQuery sobre `fact_flights`: pesan poco y el dashboard responde al instante.

## Vistas

| Vista | Grano (una fila por…) | Preguntas que responde |
|---|---|---|
| `mart.puntualidad_mensual_aerolinea` | mes × aerolínea | Ranking de aerolíneas, tipo (tradicional / bajo costo / regional), evolución anual, causas de retraso y de cancelación, COVID |
| `mart.aeropuerto_mensual` | mes × aeropuerto × rol (`Origen` / `Destino`) | Aeropuertos con más retrasos, congestión (taxi), mapa por estado |
| `mart.patron_dia_hora` | mes × día de la semana × hora programada | Mejor día y hora para volar, retraso acumulado en el día |
| `mart.serie_diaria` | día | Feriados, caída y recuperación por COVID, días críticos (cruzar con `docs/eventos_externos.csv`) |
| `mart.rutas_anual` | año × ruta (origen → destino) | Rutas más transitadas y su puntualidad, distancia vs. retraso |

## Reglas

- **Programado** = todos los vuelos. **Operado** = ni cancelado ni desviado (mismas convenciones que `docs/analisis/01_preguntas_kpis.md`).
- Las vistas guardan **conteos y sumas**, nunca porcentajes ni promedios. Así se pueden filtrar y agregar por cualquier combinación sin error.
- Los porcentajes y promedios se calculan en el dashboard **dividiendo sumas**. **Nunca promediar una columna de porcentaje.**
- `periodo_covid` = mes desde marzo de 2020.
- En `aeropuerto_mensual`, `vuelos_retrasados_15` es la **salida** retrasada en el rol `Origen` y la **llegada** retrasada en el rol `Destino`. Filtrar siempre por `rol`.

## Medidas DAX sugeridas

Sobre `mart.puntualidad_mensual_aerolinea` (cambiar el nombre de la tabla para las otras vistas):

```dax
% A tiempo (sobre operados) =
DIVIDE ( SUM ( puntualidad_mensual_aerolinea[vuelos_a_tiempo] ),
         SUM ( puntualidad_mensual_aerolinea[vuelos_operados] ) )

% A tiempo (sobre programados, criterio BTS) =
DIVIDE ( SUM ( puntualidad_mensual_aerolinea[vuelos_a_tiempo] ),
         SUM ( puntualidad_mensual_aerolinea[vuelos_programados] ) )

% Cancelados (sobre programados) =
DIVIDE ( SUM ( puntualidad_mensual_aerolinea[vuelos_cancelados] ),
         SUM ( puntualidad_mensual_aerolinea[vuelos_programados] ) )

Retraso promedio de llegada (min) =
DIVIDE ( SUM ( puntualidad_mensual_aerolinea[suma_retraso_llegada_min] ),
         SUM ( puntualidad_mensual_aerolinea[n_retraso_llegada] ) )

Minutos de retraso por causa (total) =
SUM ( puntualidad_mensual_aerolinea[min_causa_aerolinea] )
  + SUM ( puntualidad_mensual_aerolinea[min_causa_clima] )
  + SUM ( puntualidad_mensual_aerolinea[min_causa_nas] )
  + SUM ( puntualidad_mensual_aerolinea[min_causa_seguridad] )
  + SUM ( puntualidad_mensual_aerolinea[min_causa_avion_tardio] )

% Minutos por clima =
DIVIDE ( SUM ( puntualidad_mensual_aerolinea[min_causa_clima] ), [Minutos de retraso por causa (total)] )

Taxi-out promedio (min) =
DIVIDE ( SUM ( puntualidad_mensual_aerolinea[suma_taxi_out_min] ),
         SUM ( puntualidad_mensual_aerolinea[n_taxi_out] ) )

Colchón de horario (min) =
DIVIDE ( SUM ( puntualidad_mensual_aerolinea[suma_tiempo_programado_min] )
           - SUM ( puntualidad_mensual_aerolinea[suma_tiempo_real_min] ),
         SUM ( puntualidad_mensual_aerolinea[n_tiempo_real] ) )
```

`Colchón de horario` positivo significa que los vuelos duran menos de lo programado (pregunta 19, *schedule padding*).

## Lo que estas vistas NO tienen

- **Medianas y percentiles:** no se pueden reconstruir a partir de sumas. Usar las consultas de `sql/analisis/` contra `dw.fact_flights`.
- **Detalle por vuelo individual** y **por aerolínea dentro de un aeropuerto:** usar `dw.fact_flights` (en DirectQuery o con SQL).
