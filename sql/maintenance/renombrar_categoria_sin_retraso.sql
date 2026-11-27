-- =====================================================================
-- renombrar_categoria_sin_retraso.sql  (se corre UNA sola vez, en el servidor)
-- Pasa categoria_retraso 'A tiempo' -> 'Sin retraso' en la tabla de hechos ya cargada,
-- para no confundirla con estado_vuelo = 'A tiempo' (pedido del Data Analyst).
-- Las cargas nuevas ya usan 'Sin retraso' (sql/build/20_fact_flights.sql).
-- Va año por año para ver el avance. Tarda unos 20-30 min en total.
-- Uso, desde ~/app en el servidor:
--   docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/maintenance/renombrar_categoria_sin_retraso.sql
-- =====================================================================
\echo '2010...'
UPDATE dw.fact_flights_2010 SET categoria_retraso = 'Sin retraso' WHERE categoria_retraso = 'A tiempo';
\echo '2011...'
UPDATE dw.fact_flights_2011 SET categoria_retraso = 'Sin retraso' WHERE categoria_retraso = 'A tiempo';
\echo '2012...'
UPDATE dw.fact_flights_2012 SET categoria_retraso = 'Sin retraso' WHERE categoria_retraso = 'A tiempo';
\echo '2013...'
UPDATE dw.fact_flights_2013 SET categoria_retraso = 'Sin retraso' WHERE categoria_retraso = 'A tiempo';
\echo '2014...'
UPDATE dw.fact_flights_2014 SET categoria_retraso = 'Sin retraso' WHERE categoria_retraso = 'A tiempo';
\echo '2015...'
UPDATE dw.fact_flights_2015 SET categoria_retraso = 'Sin retraso' WHERE categoria_retraso = 'A tiempo';
\echo '2016...'
UPDATE dw.fact_flights_2016 SET categoria_retraso = 'Sin retraso' WHERE categoria_retraso = 'A tiempo';
\echo '2017...'
UPDATE dw.fact_flights_2017 SET categoria_retraso = 'Sin retraso' WHERE categoria_retraso = 'A tiempo';
\echo '2018...'
UPDATE dw.fact_flights_2018 SET categoria_retraso = 'Sin retraso' WHERE categoria_retraso = 'A tiempo';
\echo '2019...'
UPDATE dw.fact_flights_2019 SET categoria_retraso = 'Sin retraso' WHERE categoria_retraso = 'A tiempo';
\echo '2020...'
UPDATE dw.fact_flights_2020 SET categoria_retraso = 'Sin retraso' WHERE categoria_retraso = 'A tiempo';
\echo 'Limpiando y actualizando estadísticas (VACUUM ANALYZE)...'
VACUUM ANALYZE dw.fact_flights;
SELECT categoria_retraso, count(*) FROM dw.fact_flights GROUP BY 1 ORDER BY 1;
