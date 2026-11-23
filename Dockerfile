FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# El código (etl/) y el SQL (sql/) se montan como volúmenes desde docker-compose,
# así que no hace falta reconstruir la imagen al editarlos.
CMD ["python", "etl/run_pipeline.py", "--help"]
