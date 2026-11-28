# Figuras del informe

Generadas con `.venv/bin/python docs/analisis/generar_figuras.py sql/analisis/resultados/20261127_completo` (desde la raíz del repo). PNG de 170 dpi, 10 pulgadas de ancho (1700 px): se pegan a ancho de página en Word. Todas llevan "Fuente: BTS, cálculo propio". "A tiempo" = llegada con menos de 15 min de retraso. Las figuras con eje de tiempo marcan COVID con franja gris desde 2020-03-01.

Secciones: `02` = `../02_esqueleto_informe.md`; `04` = `../04_hallazgos.md`.

| Archivo | Qué muestra | Origen (consulta / CSV) | Universo del % | Va en |
|---|---|---|---|---|
| `F01_vuelos_programados_mes.png` | Vuelos programados por mes 2010-2020, salto de 2018 anotado (94.5 % por seis aerolíneas nuevas), COVID sombreado | 01_calidad_1.1 | Vuelos programados (conteo, no %) | 02 §2.1; 04 §2.1 |
| `F02_pct_a_tiempo_mes.png` | % a tiempo por mes 2010-2020 | 04_estacionalidad_4.1 | Vuelos operados | 02 §2.8; 04 §5.2 (tendencia anual) |
| `F03_estados_vuelo_anio.png` | A tiempo / retrasado / cancelado / desviado por año, 100 % apilado | `docs/mart_serie_diaria.csv` (suma por año; retrasado = operados - a tiempo) | Vuelos programados | 02 §2.2; 04 §2.2 |
| `F04_histograma_retraso_llegada.png` | Histograma del retraso de llegada, cubetas de 15 min, umbral de 15 min | 07_programado_vs_real_7.5 | Operados con retraso de llegada informado | 02 §2.3; 04 §2.3 |
| `F05_categorias_retraso_anio.png` | Sin retraso / Leve / Moderado / Severo / Extremo por año, 100 % apilado | 07_programado_vs_real_7.6 | Operados del año | 02 §2.4; 04 §2.4 |
| `F06_puntualidad_cancelacion_hora.png` | % a tiempo y % cancelados por hora de salida programada (2010-01 a 2020-02) | 04_estacionalidad_4.5 | A tiempo: operados; cancelados: programados | 02 §2.8; 04 §5.2 |
| `F07_mapa_calor_dia_franja.png` | Mapa de calor día de la semana x franja, % a tiempo (2010-01 a 2020-02) | 04_estacionalidad_4.6 | Operados | 02 §2.8; 04 §5.2 |
| `F08_estacionalidad_mes_anio.png` | % a tiempo y % cancelados por mes del año, antes de COVID | 04_estacionalidad_4.2 | A tiempo: operados; cancelados: programados | 02 §2.8; 04 §5.2 |
| `F09_causas_retraso_anio.png` | Participación de causas en los minutos de retraso por año | 05_causas_retraso_clima_5.2 | Minutos de retraso de operados con llegada >= 15 min | 02 §2.9; 04 §5.4 |
| `F10_causas_cancelacion_anio.png` | Causas de cancelación por año; nota del código D en 2020 | 06_cancelaciones_6.2 | Vuelos cancelados del año | 02 §2.10; 04 §5.5 |
| `F11_ranking_aerolineas_2019.png` | Ranking 2019 por aerolínea en tres paneles (tradicional, bajo costo, regional) | 02_puntualidad_aerolineas_2.2 (anio = 2019) + 2.1 (tipo, nombre) | Operados de la aerolínea en 2019 | 02 §2.5 / §5.1 del esqueleto; 04 §5.3 |
| `F12_aeropuertos_top30_salidas_retrasadas.png` | 30 mayores aeropuertos, % de salidas retrasadas >= 15 min, global 17.64 % | 03_aeropuertos_3.3 | Operados con origen en el aeropuerto | 02 §5.1; 04 §5.1 |
| `F13_mapa_estados_salidas_retrasadas.png` | Mapa de cuadros por estado, % de salidas retrasadas >= 15 min | 03_aeropuertos_3.5 | Operados con origen en el estado | 02 §3 y §5.1; 04 §5.1 |
| `F14_covid_semanal.png` | Volumen semanal 2020 como % de 2019 y % cancelados 2020 (dos paneles; sin semana 53) | 08_covid_2020_8.3 | Volumen: programados 2020 / 2019; cancelados: programados | 02 §5.6; 04 §5.6 |
| `F15_covid_puntualidad_franja.png` | % a tiempo mar-dic 2019 vs. 2020 por franja | 08_covid_2020_8.7 | Operados de marzo a diciembre | 02 §5.6; 04 §5.6 |
| `F16_clima_por_mes.png` | Minutos de retraso por clima por vuelo operado según mes del año | 05_causas_retraso_clima_5.5 | Vuelos operados (no es %) | 02 §5.4; 04 §5.4 |

Notas
- F04: la primera cubeta agrupa los retrasos < -45 min y la última los >= 240 min (la consulta 7.5 trunca en -60 y 240).
- F13: cuadrícula aproximada, sin geodependencias. DC y DE salen en gris (sin datos); TT es un código de la fuente.
- F14 y F08 usan dos paneles (nunca eje doble) porque las dos medidas tienen distinta escala.
