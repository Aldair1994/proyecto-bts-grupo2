-- =====================================================================
-- 02_puntualidad_aerolineas.sql  --  Objetivo: puntualidad por aerolínea
-- Solo SELECT. Esquema dw.
--
-- PRUEBAS RÁPIDAS (limitar a un año): reemplazar
--     f.fecha_id BETWEEN 20100101 AND 20201231
-- por
--     f.fecha_id BETWEEN 20190101 AND 20191231
--
-- Definiciones (iguales en todo el proyecto):
--   * operado = NOT cancelado AND NOT desviado
--   * pct_a_tiempo_sobre_operados = vuelos 'A tiempo' (llegada < 15 min de retraso) / operados * 100
--   * pct_cancelados_sobre_programados = cancelados / todos los vuelos * 100
--
-- AVISOS DE COMPARACIÓN: Spirit (NK) solo desde 2015; Allegiant (G4) y Republic (YX)
--   desde 2018. Fusiones: Continental CO->UA, AirTran FL->WN, US Airways US->AA,
--   Virgin America VX->AS. Al comparar 2010 vs 2020 las cifras no son del mismo conjunto de
--   aerolíneas. Los regionales (SkyWest, Envoy, etc.) se rankean APARTE de las troncales.
--
-- TIPO DE AEROLÍNEA: las consultas usan la CTE temporal `tipo_aerolinea` (lista VALUES).
--   -- TODO: reemplazar por dw.dim_airline.tipo cuando exista
--   Códigos DUDOSOS (verificar contra L_UNIQUE_CARRIERS / catalogo_aerolineas.csv):
--     * Clasificación discutible: AS (Alaska: ¿tradicional?), B6 (JetBlue: ¿bajo costo o híbrido?),
--       HA (Hawaiian), VX (Virgin America: ¿bajo costo o premium?), F9 (ultra bajo costo desde ~2014).
--     * Código a confirmar en BTS: XE, CP, ZW, QX, AX, C5, G7, 9K, KS (regionales pequeños;
--       pueden no aparecer en la base o tener otro código).
--     * OH fue Comair (hasta 2012) y luego PSA; MQ fue American Eagle y luego Envoy (2014);
--       EV = ExpressJet (absorbió a Atlantic Southeast): todos regionales, pero cambian de nombre.
--     * Códigos que no estén en la lista salen como 'sin clasificar'.
-- =====================================================================


-- 2.1 Puntualidad global por aerolínea (periodo completo), separada por tipo
-- Pregunta: ¿qué aerolíneas son más puntuales? Universo: operados (puntualidad, mediana de
--   retraso) y programados (cancelación). Mínimo de volumen: params.min_operados vuelos operados
--   (evita rankear aerolíneas con muy pocos vuelos). Ajustar a gusto.
-- KPI: pct_a_tiempo_sobre_operados (KPI-1), pct_cancelados_sobre_programados (KPI-3).
WITH params AS (SELECT 5000 AS min_operados),
tipo_aerolinea (codigo, tipo) AS (  -- TODO: reemplazar por dw.dim_airline.tipo cuando exista
    VALUES ('AA','tradicional'),('AS','tradicional'),('CO','tradicional'),('DL','tradicional'),
           ('HA','tradicional'),('UA','tradicional'),('US','tradicional'),
           ('B6','bajo costo'),('F9','bajo costo'),('FL','bajo costo'),('G4','bajo costo'),
           ('NK','bajo costo'),('VX','bajo costo'),('WN','bajo costo'),
           ('9E','regional'),('EV','regional'),('MQ','regional'),('OH','regional'),('OO','regional'),
           ('YV','regional'),('YX','regional'),('XE','regional'),('CP','regional'),('ZW','regional'),
           ('QX','regional'),('AX','regional'),('C5','regional'),('G7','regional'),('9K','regional'),
           ('KS','regional')
)
SELECT coalesce(t.tipo, 'sin clasificar') AS tipo,
       a.codigo, a.nombre,
       count(*)                                                        AS vuelos_programados,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado)      AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_a_tiempo_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado)
             / NULLIF(count(*), 0), 2)                                 AS pct_cancelados_sobre_programados,
       round(100.0 * count(*) FILTER (WHERE f.desviado)
             / NULLIF(count(*), 0), 2)                                 AS pct_desviados_sobre_programados,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.retraso_llegada)
              FILTER (WHERE NOT f.cancelado AND NOT f.desviado))::numeric, 1) AS mediana_retraso_llegada_min,
       round(avg(f.retraso_total) FILTER (WHERE NOT f.cancelado AND NOT f.desviado)::numeric, 1) AS retraso_total_promedio_min_sobre_operados,
       rank() OVER (PARTITION BY coalesce(t.tipo, 'sin clasificar')
                    ORDER BY 100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
                             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0) DESC) AS posicion_dentro_del_tipo
FROM dw.fact_flights f
JOIN dw.dim_airline a USING (airline_id)
LEFT JOIN tipo_aerolinea t ON t.codigo = a.codigo
CROSS JOIN params p
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY t.tipo, a.codigo, a.nombre, p.min_operados
HAVING count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) >= p.min_operados
ORDER BY 1, posicion_dentro_del_tipo;


-- 2.2 Puntualidad por aerolínea y año (tendencia)
-- Pregunta: ¿cómo evolucionó la puntualidad de cada aerolínea? Universo: operados del año.
--   2020 mezcla antes y después de COVID: ver 08_covid_2020.sql. Aerolíneas con pocos años de
--   datos (NK, G4, YX) o fusionadas (CO, FL, US, VX) aparecen solo en los años en que existen.
-- Mínimo: 1000 operados por aerolínea-año para mostrar la fila.
-- KPI: pct_a_tiempo_sobre_operados.
SELECT a.codigo, f.fecha_id / 10000 AS anio,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_a_tiempo_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.cancelado) / NULLIF(count(*), 0), 2) AS pct_cancelados_sobre_programados
FROM dw.fact_flights f
JOIN dw.dim_airline a USING (airline_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY a.codigo, f.fecha_id / 10000
HAVING count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) >= 1000
ORDER BY a.codigo, anio;


-- 2.3 Ranking mensual para el dashboard (aerolínea x mes, con filtros de fecha)
-- Pregunta: KPI de puntualidad por aerolínea filtrable por fecha. Universo: operados del mes.
-- Para el dashboard: pasar el rango de fechas con fecha_id (AAAAMMDD) en el WHERE.
SELECT d.anio, d.mes, a.codigo AS aerolinea,
       count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS vuelos_operados,
       round(100.0 * count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')
             / NULLIF(count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado), 0), 2) AS pct_a_tiempo_sobre_operados
FROM dw.fact_flights f
JOIN dw.dim_airline a USING (airline_id)
JOIN dw.dim_fecha d USING (fecha_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
GROUP BY d.anio, d.mes, a.codigo
HAVING count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) >= 100
ORDER BY d.anio, d.mes, pct_a_tiempo_sobre_operados DESC;


-- 2.4 Distribución de categorías de retraso por aerolínea
-- Pregunta: ¿qué tan graves son los retrasos de cada aerolínea?
-- Universo: operados con categoria_retraso no nula (A tiempo <=0, Leve 1-14, Moderado 15-59,
--   Severo 60-179, Extremo >=180). Los % suman 100 por aerolínea.
-- OJO: la categoría 'A tiempo' de categoria_retraso significa retraso de llegada <= 0 min; NO es el
--   KPI-1 (estado_vuelo = 'A tiempo', llegada < 15 min). Por eso el alias es distinto
--   (pct_sin_retraso_0min_sobre_operados) y sus cifras serán menores que pct_a_tiempo_sobre_operados.
SELECT a.codigo AS aerolinea,
       count(*) AS vuelos_operados_con_categoria,
       round(100.0 * count(*) FILTER (WHERE f.categoria_retraso = 'A tiempo') / NULLIF(count(*),0), 2) AS pct_sin_retraso_0min_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.categoria_retraso = 'Leve')     / NULLIF(count(*),0), 2) AS pct_leve_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.categoria_retraso = 'Moderado') / NULLIF(count(*),0), 2) AS pct_moderado_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.categoria_retraso = 'Severo')   / NULLIF(count(*),0), 2) AS pct_severo_sobre_operados,
       round(100.0 * count(*) FILTER (WHERE f.categoria_retraso = 'Extremo')  / NULLIF(count(*),0), 2) AS pct_extremo_sobre_operados
FROM dw.fact_flights f
JOIN dw.dim_airline a USING (airline_id)
WHERE f.fecha_id BETWEEN 20100101 AND 20201231
  AND f.categoria_retraso IS NOT NULL
GROUP BY a.codigo
HAVING count(*) >= 1000
ORDER BY pct_sin_retraso_0min_sobre_operados DESC;


-- 2.5 Tabla de comparación por año de referencia: aerolíneas presentes en TODO el periodo
-- Pregunta: comparación 2010 vs 2019 (pre-COVID) solo con aerolíneas que existen en ambos años,
--   para no comparar manzanas con naranjas (se excluyen NK, G4, YX y las fusionadas).
-- Universo: operados de cada año. Ajustar los años en `anio_a` / `anio_b`.
WITH params AS (SELECT 2010 AS anio_a, 2019 AS anio_b),
base AS (
    SELECT a.codigo, f.fecha_id / 10000 AS anio,
           count(*) FILTER (WHERE NOT f.cancelado AND NOT f.desviado) AS operados,
           count(*) FILTER (WHERE f.estado_vuelo = 'A tiempo')        AS a_tiempo
    FROM dw.fact_flights f
    JOIN dw.dim_airline a USING (airline_id)
    CROSS JOIN params p
    WHERE f.fecha_id BETWEEN p.anio_a * 10000 + 101 AND p.anio_a * 10000 + 1231
       OR f.fecha_id BETWEEN p.anio_b * 10000 + 101 AND p.anio_b * 10000 + 1231
    GROUP BY a.codigo, f.fecha_id / 10000
)
SELECT x.codigo,
       x.operados AS operados_anio_a, y.operados AS operados_anio_b,
       round(100.0 * x.a_tiempo / NULLIF(x.operados, 0), 2) AS pct_a_tiempo_sobre_operados_anio_a,
       round(100.0 * y.a_tiempo / NULLIF(y.operados, 0), 2) AS pct_a_tiempo_sobre_operados_anio_b,
       round(100.0 * y.a_tiempo / NULLIF(y.operados, 0) - 100.0 * x.a_tiempo / NULLIF(x.operados, 0), 2) AS diferencia_puntos_porcentuales
FROM base x
JOIN base y ON y.codigo = x.codigo
CROSS JOIN params p
WHERE x.anio = p.anio_a AND y.anio = p.anio_b
  AND x.operados >= 1000 AND y.operados >= 1000
ORDER BY diferencia_puntos_porcentuales DESC;
