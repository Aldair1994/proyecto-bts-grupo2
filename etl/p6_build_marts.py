"""Paso 6 - Construye la capa de consumo (esquema mart) para el dashboard.

Uso:
    python etl/p6_build_marts.py

Recrea las vistas materializadas de sql/build/30_marts.sql a partir de dw.fact_flights.
Hay que correrlo después del modelo estrella (paso 5) y cada vez que se recargue la
tabla de hechos. Con los 67 M de vuelos tarda unos 10-20 minutos.
"""

from common import connect, get_logger
from config import SQL_DIR

log = get_logger("p6_build_marts")

MARTS_SQL = SQL_DIR / "build" / "30_marts.sql"
VISTAS = ["puntualidad_mensual_aerolinea", "aeropuerto_mensual", "patron_dia_hora",
          "serie_diaria", "rutas_anual"]


def main() -> None:
    log.info("Construyendo vistas del esquema mart")
    with connect() as conn:
        conn.execute(MARTS_SQL.read_text(encoding="utf-8"))
        conn.commit()
        for v in VISTAS:
            conn.execute(f"ANALYZE mart.{v}")
            n = conn.execute(f"SELECT count(*) FROM mart.{v}").fetchone()[0]
            log.info("mart.%s: %s filas", v, f"{n:,}")
        conn.commit()


if __name__ == "__main__":
    main()
