"""Utilidades comunes: logging a archivo con fecha y conexión a PostgreSQL."""

import logging
import sys
from datetime import datetime

import psycopg

from config import LOG_DIR


def get_logger(name: str) -> logging.Logger:
    """Logger que escribe en consola y en data/logs/pipeline_AAAAMMDD.log."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOG_DIR / f"pipeline_{datetime.now():%Y%m%d}.log"
    fileh = logging.FileHandler(logfile, encoding="utf-8")
    fileh.setFormatter(fmt)
    logger.addHandler(fileh)
    return logger


def connect(autocommit: bool = False) -> psycopg.Connection:
    """Conexión usando las variables estándar PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD."""
    return psycopg.connect(autocommit=autocommit)
