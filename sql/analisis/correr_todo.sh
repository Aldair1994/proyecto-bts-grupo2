#!/usr/bin/env bash
# correr_todo.sh -- ejecuta las consultas de sql/analisis/0*.sql y guarda cada una en su CSV.
#
# Uso:  ./correr_todo.sh [--anio AAAA] [--solo NN] [--salida DIR]
#   --anio AAAA  limita a ese año reemplazando "BETWEEN 20100101 AND 20201231" por el rango del año.
#                AVISO: las consultas con rango propio (p. ej. 2010-2020-02 en 04_estacionalidad,
#                2019-2020 en 08_covid_2020) NO se modifican.
#   --solo NN    corre solo el archivo que empieza por NN (p. ej. --solo 02).
#   --salida DIR carpeta base de resultados (por defecto sql/analisis/resultados/).
#
# Conexión: variables estándar de psql. Por defecto PGHOST=localhost PGPORT=5432 PGUSER=bts_admin
# PGDATABASE=bts (PGPASSWORD si hace falta). En el servidor se accede por túnel SSH:
#   ssh -N -L 5432:localhost:5432 ubuntu@100.55.222.111
#
# Salida: <DIR>/AAAAMMDD/<archivo>_<N.M>.csv (uno por consulta, p. ej. 02_puntualidad_aerolineas_2.1.csv),
#   tiempos.csv (archivo,consulta,segundos,estado) y errores.log. Una consulta que falla se anota y
#   se sigue con la siguiente. `resultados/` NO se versiona (tiene su propio .gitignore).
# Cada consulta se identifica por su cabecera "-- N.M ..." y se corre en un trozo aparte.

set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PGHOST="${PGHOST:-localhost}" PGPORT="${PGPORT:-5432}" \
       PGUSER="${PGUSER:-bts_admin}" PGDATABASE="${PGDATABASE:-bts}"
ANIO=""; SOLO=""; BASE="$DIR/resultados"

while [ $# -gt 0 ]; do
  case "$1" in
    --anio)   ANIO="${2:-}"; shift 2 ;;
    --solo)   SOLO="${2:-}"; shift 2 ;;
    --salida) BASE="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "Opción desconocida: $1" >&2; exit 2 ;;
  esac
done
if [ -n "$ANIO" ] && ! [[ "$ANIO" =~ ^[0-9]{4}$ ]]; then echo "--anio debe ser AAAA" >&2; exit 2; fi
command -v psql >/dev/null || { echo "psql no está en el PATH" >&2; exit 2; }

OUT="$BASE/$(date +%Y%m%d)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT"
echo "archivo,consulta,segundos,estado" > "$OUT/tiempos.csv"
: > "$OUT/errores.log"

if [ -n "$ANIO" ]; then
  echo "Limitando a $ANIO (las consultas con rango propio, como 2010-2020-02 o 2019-2020, no se modifican)."
fi
echo "Conexión: $PGUSER@$PGHOST:$PGPORT/$PGDATABASE  ->  $OUT"

ahora() { if [ -n "${EPOCHREALTIME:-}" ]; then echo "${EPOCHREALTIME/,/.}"; else date +%s; fi; }

ok=0; fallas=0; n_archivos=0
for f in "$DIR"/${SOLO}*.sql; do
  [ -e "$f" ] || { echo "No hay archivos que coincidan con '${SOLO}*.sql'" >&2; exit 2; }
  case "$(basename "$f")" in 0*) ;; *) continue ;; esac
  base="$(basename "$f" .sql)"; n_archivos=$((n_archivos+1))
  rm -f "$TMP"/trozo_*
  # Parte el archivo en trozos por cabecera "-- N.M ..."; lo anterior a la primera cabecera se descarta.
  awk -v dir="$TMP" '
    /^-- [0-9]+\.[0-9]+ / { id=$2; out=dir "/trozo_" id ".sql" }
    out != "" { print > out }
  ' "$f"
  for t in "$TMP"/trozo_*.sql; do
    [ -e "$t" ] || continue
    id="$(basename "$t" .sql)"; id="${id#trozo_}"
    if [ -n "$ANIO" ]; then
      sed -i.bak "s/BETWEEN 20100101 AND 20201231/BETWEEN ${ANIO}0101 AND ${ANIO}1231/g" "$t" && rm -f "$t.bak"
    fi
    csv="$OUT/${base}_${id}.csv"
    t0="$(ahora)"
    if psql -X -v ON_ERROR_STOP=1 --csv -f "$t" -o "$csv" 2> "$TMP/err.txt"; then
      estado="ok"; ok=$((ok+1))
    else
      estado="error"; fallas=$((fallas+1)); rm -f "$csv"
      { echo "[$base $id]"; cat "$TMP/err.txt"; } >> "$OUT/errores.log"
    fi
    seg="$(awk -v a="$t0" -v b="$(ahora)" 'BEGIN{printf "%.2f", b-a}')"
    echo "$base,$id,$seg,$estado" >> "$OUT/tiempos.csv"
    printf '  %-34s %-5s %8ss  %s\n' "$base" "$id" "$seg" "$estado"
  done
done

[ -s "$OUT/errores.log" ] || rm -f "$OUT/errores.log"
echo "Resumen: $n_archivos archivo(s), $ok consulta(s) ok, $fallas con error. Tiempos: $OUT/tiempos.csv"
[ "$fallas" -eq 0 ] || { echo "Errores en $OUT/errores.log"; exit 1; }
