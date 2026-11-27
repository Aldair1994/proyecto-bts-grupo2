# Proyecto Integrador de Análisis de Datos (CRISP-DM): Grupo 2

Análisis de puntualidad de vuelos en EE. UU. con datos de **BTS TranStats**, de **2010 a 2020**.
Curso: Introducción al Análisis de Datos, Maestría en Ingeniería en Ciencias de la Computación, USAC EEP.

| Rol | Integrante |
|---|---|
| Data Administrator | Marvin |
| BI Analyst | Melani |
| Data Analyst | Mynor |
| Data Engineering | Aldair, Edwin |

## Arquitectura

```
BTS (zip mensual) ─▶ p1_download ─▶ p2_to_parquet ─▶ p3_load_raw ─▶ raw.flights (particionada por año)
                                                                          │
BTS Get Lookup Table + feriados ─▶ p4_load_reference ─▶ ref.*             │
                                                         └──────┬─────────┘
                                                                ▼
                                                     p5_build_star ─▶ dw.* (modelo estrella) ─▶ Dashboard
```

| Capa | Contenido |
|---|---|
| `raw` | 46 columnas seleccionadas de BTS, tipadas. Una partición por año, de 2010 a 2020 |
| `ref` | Lookups de BTS (aerolíneas, aeropuertos), feriados de EE. UU. y coordenadas (opcional) |
| `dw`  | `fact_flights` (particionada por año) + `dim_fecha`, `dim_airline`, `dim_airport`, `dim_bloque_horario`, `dim_cancelacion` |
| `mart` | Vistas materializadas resumidas para el dashboard (ver [`docs/marts.md`](docs/marts.md)) |

El detalle de cada columna y las reglas de negocio están en [`docs/columnas.md`](docs/columnas.md).

## Estructura

```
├── docker-compose.yml      # PostgreSQL 16 + contenedor del ETL
├── Dockerfile              # imagen Python del ETL
├── .env.example            # credenciales de ejemplo (copiar a .env)
├── sql/
│   ├── init/               # se ejecuta solo al crear la base: esquemas y tablas
│   └── build/              # construye el modelo estrella (lo corre p5_build_star.py)
├── etl/
│   ├── config.py           # rango de años, rutas y columnas seleccionadas
│   ├── p1_download.py … p5_build_star.py
│   └── run_pipeline.py     # orquestador
├── docs/columnas.md        # diccionario de datos inicial
└── data/                   # zips, parquet, lookups y logs (no se suben a git)
```

## Manual de instalación

### Requisitos
- Docker y Docker Compose
- Disco: unos 10 GB libres durante la carga (los zips se borran al convertirlos a Parquet)
- RAM recomendada: 16 GB (con 8 GB, bajar `shared_buffers` a 2GB en `docker-compose.yml`)

### 1. Levantar la base
```bash
git clone <url-del-repo>
cd proyecto-bts-grupo2
cp .env.example .env        # y cambiar la contraseña
docker compose up -d db
```
La primera vez se crean solos los esquemas `raw`, `ref` y `dw` con sus particiones.

### 2. Correr el pipeline
```bash
# Todo de una vez (descarga, Parquet, carga, referencias y modelo estrella)
docker compose run --rm etl python etl/run_pipeline.py --start 2010 --end 2020

# O repartido entre dos personas:
docker compose run --rm etl python etl/run_pipeline.py --start 2010 --end 2015 --steps download parquet
docker compose run --rm etl python etl/run_pipeline.py --start 2016 --end 2020 --steps download parquet
# ... después, con todos los Parquet en data/parquet/:
docker compose run --rm etl python etl/run_pipeline.py --steps load reference star
```

Cada paso se puede repetir sin duplicar datos: los meses ya descargados, convertidos o cargados se omiten. Los zips se conservan por defecto (para regenerar el Parquet si cambian las columnas); para liberar espacio usar `--delete-zip`. Para recargar un mes: `python etl/p3_load_raw.py --start 2015 --end 2015 --force`.

Los logs quedan en `data/logs/pipeline_AAAAMMDD.log`.

### 3. Conectarse
- **Power BI / DBeaver / pgAdmin:** host del servidor, puerto `5432`, base `bts` y el usuario y la contraseña del `.env`.
- Para el dashboard, usar las tablas del esquema `dw`.

### Tablas de referencia (lookups)
`data/lookups/L_UNIQUE_CARRIERS.csv` y `data/lookups/L_AIRPORT_ID.csv` se descargaron a mano con el botón *Get Lookup Table* de BTS (la descarga automática devuelve HTML) y están versionadas en el repositorio, así que no hay que volver a bajarlas.

### Si falla la descarga de BTS
- **Zips mensuales:** se pueden bajar a mano desde la página de BTS y guardar en `data/raw_zip/` con el nombre `bts_ontime_AAAA_MM.zip`.

## Pendientes
- [ ] Confirmar las columnas cuando el grupo cierre las preguntas de negocio
- [ ] `data/lookups/airport_coords.csv` (latitud, longitud y zona horaria) para el mapa y la estandarización horaria
- [ ] Limpieza adicional (duplicados, valores fuera de rango) según el informe de calidad
- [ ] Dataset final para los modelos (Data Analyst)

## Uso de IA
Partes del código de este repositorio se generaron con asistencia de IA (Claude, de Anthropic) y el equipo las revisó, probó y ajustó. Se documenta como pide el curso.
