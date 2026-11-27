# Changelog

Formato de versiones: MAYOR.MENOR.PARCHE. Mayor si cambia el esquema, menor si cambia una regla o una definicion, parche si se corrige un dato.

## [1.0.0] - Data Administrator (borrador)

### Agregado
- `docs/Documento_CRISP-DM_Grupo2.docx` y `docs/generar_documento.py`: documento formal con Business Understanding, Data Understanding, gobierno de datos y lineamientos de Data Preparation.
- `docs/diccionario_datos.csv`: 53 campos de la fuente BTS con tipo, unidad, nulos esperados y su columna en `raw.flights`.
- `docs/eventos_externos.csv`: 30 eventos de 2010 a 2020 (pandemia, 737 MAX, huracanes, tormentas, fallas) para marcar o filtrar en el analisis.
- `docs/manifiesto_fuente.csv`: hash SHA-256 de los 132 zip mensuales de BTS (enero 2010 a diciembre 2020).
- `calidad/perfilado_calidad.py` y `calidad/diccionario.py`: reglas de calidad R01 a R13 sobre los zip de BTS.
- `docs/calidad/q_*.csv`: resultados de la corrida sobre los 132 archivos (67,249,397 vuelos).

### Hallazgos de la corrida de calidad
- Sin nulos en campos obligatorios, banderas invalidas, horas fuera de rango ni distancias no positivas.
- 4 duplicados de la clave natural, 969 vuelos normales sin retraso, 352 con ArrDel15 incoherente, 2 con causas que no suman.
- 39,234 vuelos cancelados traen hora de salida (se cancelaron tras salir de la puerta); se conservan.
- Gate Return (FirstDepTime, TotalAddGTime, LongestAddGTime) vacio en 99.4 %.

### Cambiado
- `.gitignore`: se agregan excepciones para los CSV de `docs/` y `docs/calidad/`.

## [1.0.1] - Data Administrator

### Agregado
- `docs/catalogo_aerolineas.csv`: las 22 aerolíneas presentes en los datos, con tipo (tradicional, bajo costo, regional), anios de aparicion y fusiones.
- `sql/quality/checks.sql`: reglas R01 a R11 y conciliacion de filas por anio contra lo esperado segun los zip (67,249,397 filas). Sin correr todavia contra una base cargada.
- Seccion 3.7 del documento con el catalogo y sus advertencias.

## [1.0.2] - Data Administrator

### Cambiado
- `sql/quality/checks.sql`: la conciliacion por anio compara ahora los zip, `raw.load_log` y `raw.flights`, y marca cada anio como OK o REVISAR. Sin correr todavia contra una base cargada.
- `.gitignore`: se une con los cambios de `main` (lookups versionados y `data/logs/`).


## [1.1.0] - Data Administrator

### Agregado
- `calidad/verificar_descargas.py`: compara los zip descargados contra `docs/manifiesto_fuente.csv` y marca cada mes como OK, DISTINTO, CORRUPTO o FALTA.

## [1.1.1] - Data Administrator

### Corregido
- `docs/catalogo_aerolineas.csv`: el codigo OH son dos empresas (Comair en 2010, PSA Airlines en 2018-2020); antes figuraba solo como PSA. Se agrega la nota de anios sin datos en 9E, MQ y YV.
- Documento CRISP-DM, seccion 3.7: advertencia sobre codigos reutilizados y anios sin datos.

