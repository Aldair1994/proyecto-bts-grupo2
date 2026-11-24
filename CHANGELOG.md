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
