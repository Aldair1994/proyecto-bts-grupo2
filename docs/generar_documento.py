#!/usr/bin/env python3
"""Genera Documento_CRISP-DM_Grupo2.docx (parte del Data Administrator) y docs/diccionario_datos.csv.
Uso (desde la raiz del repo): python docs/generar_documento.py   (requiere pandas y python-docx)
Si ya existen docs/calidad/q_*.csv (salida de calidad/perfilado_calidad.py), el informe de calidad las incluye."""
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

B = Path(__file__).resolve().parent.parent   # raiz del repo
sys.path.insert(0, str(B / "calidad"))
from diccionario import CAMPOS, EVENTOS, LOOKUPS, REGLAS  # noqa: E402

OUT = B / "docs" / "Documento_CRISP-DM_Grupo2.docx"
(B / "docs").mkdir(exist_ok=True)
pd.DataFrame(EVENTOS, columns=["id", "inicio", "fin", "tipo", "evento", "alcance", "tratamiento"]
             ).to_csv(B / "docs" / "eventos_externos.csv", index=False, encoding="utf-8-sig")

import importlib.util  # noqa: E402

_cfg = B / "etl" / "config.py"
RAW_MAP = {}
if _cfg.exists():
    _sp = importlib.util.spec_from_file_location("etl_config", _cfg)
    _m = importlib.util.module_from_spec(_sp)
    _sp.loader.exec_module(_m)
    RAW_MAP = {k: v[0] for k, v in _m.COLUMNS.items()}
N_RAW = len(RAW_MAP)
pd.DataFrame([c + (RAW_MAP.get(c[0], "no se carga"),) for c in CAMPOS],
             columns=["campo_bts", "tipo_sql", "categoria_bts", "descripcion", "unidad_formato", "nulos_esperados", "uso", "columna_en_raw_flights"]
             ).to_csv(B / "docs" / "diccionario_datos.csv", index=False, encoding="utf-8-sig")

doc = Document()
s = doc.sections[0]
s.left_margin = s.right_margin = Cm(2.5)
s.top_margin = s.bottom_margin = Cm(2.3)
st = doc.styles["Normal"]
st.font.name = "Arial"
st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.15
for nombre, tam in (("Heading 1", 15), ("Heading 2", 12.5), ("Heading 3", 11)):
    h = doc.styles[nombre]
    h.font.name, h.font.size, h.font.bold = "Arial", Pt(tam), True
    h.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    h.paragraph_format.space_before = Pt(14 if nombre == "Heading 1" else 10)


def p(texto, italica=False, centrado=False):
    par = doc.add_paragraph()
    r = par.add_run(texto)
    r.italic = italica
    if centrado:
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return par


def lista(items):
    for t in items:
        doc.add_paragraph(t, style="List Bullet")


def sombrear(celda, color):
    tcPr = celda._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), color)
    tcPr.append(sh)


def tabla(encabezado, filas, anchos=None, tam=8.5):
    t = doc.add_table(rows=1, cols=len(encabezado))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, e in enumerate(encabezado):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(e)
        r.bold, r.font.size = True, Pt(tam)
        sombrear(c, "D9E2F3")
    for fila in filas:
        cs = t.add_row().cells
        for i, v in enumerate(fila):
            cs[i].text = ""
            cs[i].paragraphs[0].add_run(str(v)).font.size = Pt(tam)
            cs[i].paragraphs[0].paragraph_format.space_after = Pt(0)
    if anchos:
        for fila in t.rows:
            for i, w in enumerate(anchos):
                fila.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def toc():
    par = doc.add_paragraph()
    r = par.add_run()
    for tipo, txt in (("begin", None), (None, 'TOC \\o "1-2" \\h \\z \\u'), ("separate", None), (None, "Clic derecho y Actualizar campo para ver el indice."), ("end", None)):
        if tipo:
            f = OxmlElement("w:fldChar")
            f.set(qn("w:fldCharType"), tipo)
            r._r.append(f)
        elif txt.startswith("TOC"):
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = txt
            r._r.append(it)
        else:
            tt = OxmlElement("w:t")
            tt.text = txt
            r._r.append(tt)


# ------------------------------------------------------------------ portada
for _ in range(5):
    doc.add_paragraph()
p("Proyecto integrador de Análisis de Datos (CRISP-DM)", centrado=True).runs[0].font.size = Pt(20)
p("Vuelos comerciales de Estados Unidos, 2010 a 2020", centrado=True).runs[0].font.size = Pt(14)
p("Fuente: Bureau of Transportation Statistics, TranStats (On-Time Reporting Carrier)", italica=True, centrado=True)
doc.add_paragraph()
p("Grupo 2", centrado=True)
p("Rol del autor: Data Administrator (depuración, diccionario de datos, metadatos, versionado y gobierno de datos)", centrado=True)
p("Curso: Análisis de Datos", centrado=True)
p("Noviembre de 2026", centrado=True)
doc.add_page_break()
doc.add_heading("Contenido", 1)
toc()
doc.add_page_break()

# ------------------------------------------------------------------ 1
doc.add_heading("1. Cómo leer este documento", 1)
p("Este es el documento formal CRISP-DM del grupo 2, y quien lo lidera es el Data Administrator. Aquí queda todo lo que "
  "le toca a ese rol: el diccionario de datos, los metadatos, las reglas de calidad, el versionado y el gobierno. También "
  "dejamos redactado el borrador de Business Understanding y los lineamientos de preparación, para que los demás perfiles "
  "(BI Analyst, Data Analyst y Data Engineering) los completen con sus hallazgos, su modelo y su dashboard sin tener que "
  "empezar de cero.")
p("Los apartados que dependen de correr el pipeline sobre los datos reales aparecen marcados como pendientes. Cuando se "
  "descarguen los 132 archivos mensuales y corra el script de calidad, esas tablas se llenan solas al regenerar el documento.")
tabla(["Fase CRISP-DM", "Peso", "Qué aporta el Data Administrator"], [
    ("Business Understanding", "10 %", "Redacción del documento, supuestos, riesgos y restricciones de datos"),
    ("Data Understanding", "15 %", "Inventario de fuentes, diccionario de datos, informe de calidad"),
    ("Data Preparation", "20 %", "Reglas de limpieza y validación, definición de variables derivadas, cuarentena"),
    ("Modelo en estrella", "20 %", "Convenciones de nombres, llaves y metadatos de cada tabla"),
    ("Dashboard", "15 %", "Definición oficial de cada KPI para que el tablero y los datos coincidan"),
    ("Análisis final e insights", "20 %", "Trazabilidad: toda cifra citada se puede rastrear a su versión del dataset"),
], anchos=[4.2, 1.6, 10.2])

# ------------------------------------------------------------------ 2
doc.add_heading("2. Business Understanding", 1)
doc.add_heading("2.1 Problema y objetivos del negocio", 2)
p("Un retraso en un vuelo le cuesta tiempo al pasajero y plata a la aerolínea y al aeropuerto. Las autoridades reportan miles "
  "de millones de minutos perdidos cada año, pero la información viene en archivos mensuales de más de cien columnas que nadie "
  "lee completos. Nuestro trabajo es convertir once años de ese reporte (2010 a 2020) en un modelo ordenado y en un tablero que "
  "responda dónde, cuándo y con quién se atrasan más los vuelos. Los usuarios del resultado son un analista de operaciones de "
  "una aerolínea o de un aeropuerto, y un pasajero frecuente que quiere decidir con qué aerolínea y a qué hora viajar.")
p("Escogimos cinco objetivos, uno más de los cuatro mínimos que pide el curso:")
tabla(["Id", "Objetivo", "Indicador y meta de referencia"], [
    ("O1", "Identificar los aeropuertos con mayor incidencia de retrasos", "Porcentaje de salidas con 15 minutos o más de retraso por aeropuerto, ranking de los 20 peores con al menos 10 mil operaciones al año"),
    ("O2", "Determinar patrones estacionales en los vuelos", "Retraso promedio y porcentaje de vuelos retrasados por mes, día de la semana y franja horaria"),
    ("O3", "Calcular qué aerolíneas tienen mejor desempeño puntual", "Porcentaje de llegadas a tiempo (menos de 15 minutos de retraso) por aerolínea y año"),
    ("O4", "Analizar el impacto del clima y la geografía en los retrasos", "Participación de WeatherDelay y NASDelay en los minutos totales de retraso, por estado y región"),
    ("O5", "Medir el efecto de las cancelaciones y desviaciones", "Tasa de cancelación y de desvío por causa (A, B, C, D) y por año, con corte especial en 2020"),
], anchos=[1.1, 6.4, 8.5])
doc.add_heading("2.2 Definición oficial de los KPI iniciales", 2)
p("Dejamos cada KPI definido una sola vez, con su fórmula, para que el modelo, el dashboard y el informe digan lo mismo. "
  "Un vuelo cuenta como retrasado cuando llega o sale con 15 minutos o más sobre lo programado, que es el umbral que usa el propio BTS.")
tabla(["KPI", "Fórmula", "Universo"], [
    ("Puntualidad de llegada", "Vuelos con ArrDelay < 15 / vuelos operados", "Vuelos no cancelados ni desviados"),
    ("Puntualidad de salida", "Vuelos con DepDelay < 15 / vuelos operados", "Vuelos no cancelados ni desviados"),
    ("Retraso promedio de llegada", "Promedio de ArrDelayMinutes", "Vuelos no cancelados ni desviados"),
    ("Tasa de cancelación", "Vuelos con Cancelled = 1 / vuelos programados", "Todos los registros"),
    ("Tasa de desvío", "Vuelos con Diverted = 1 / vuelos programados", "Todos los registros"),
    ("Participación por causa", "Minutos de cada causa / suma de minutos de las cinco causas", "Vuelos con ArrDelay >= 15"),
], anchos=[4.2, 7.3, 4.5])
doc.add_heading("2.3 Preguntas de negocio", 2)
lista([
    "¿Cuáles son los 20 aeropuertos con más retrasos de salida y cambia ese ranking entre 2010 y 2020?",
    "¿En qué meses y franjas del día se concentran los retrasos? ¿Hay diferencia clara entre viernes y martes?",
    "¿Qué aerolíneas son más puntuales y cuánto pesa el tamaño de la aerolínea en ese resultado?",
    "¿Qué proporción del retraso viene de causas que la aerolínea controla (CarrierDelay, LateAircraftDelay) frente al clima y el espacio aéreo?",
    "¿Los estados del noreste pierden más minutos por clima que los del sur? ¿Y en invierno?",
    "¿Cómo se comportó la puntualidad en 2020, cuando el tráfico cayó casi a la mitad?",
    "¿Cuánto cambia la puntualidad según la distancia del vuelo?",
])
doc.add_heading("2.3.1 Lista de requerimientos analíticos", 3)
lista([
    "Detalle diario por vuelo con los 11 años completos, sin muestreos.",
    "Dimensiones de aerolínea, aeropuerto y fecha con sus nombres descriptivos (tablas Get Lookup).",
    "Calendario de feriados de Estados Unidos para el análisis estacional.",
    "Bandera de atípicos en lugar de borrar registros, para poder filtrar en el reporte.",
    "Dashboard con filtros por fecha, aerolínea y aeropuerto, y mapa por aeropuerto.",
])
doc.add_heading("2.4 Evaluación de la situación", 2)
tabla(["Aspecto", "Situación"], [
    ("Fuentes", "BTS TranStats, tabla On-Time Reporting Carrier; tablas Get Lookup para aerolíneas, aeropuertos y causas de cancelación"),
    ("Permisos y privacidad", "Datos públicos y agregados por vuelo, sin información de pasajeros. No hay datos personales"),
    ("Volumen", "67.2 millones de registros en 132 archivos mensuales (3.2 GB comprimidos)"),
    ("Infraestructura", "Base en contenedor Docker, pipeline en Python y SQL, dashboard en Looker Studio, Power BI o Tableau"),
    ("Costo", "Cero en licencias; el costo real es tiempo de descarga y espacio en disco (varios GB descomprimidos)"),
    ("Dependencias", "El sitio de BTS debe estar disponible; el modelo en estrella depende de que la limpieza cierre primero"),
], anchos=[3.8, 12.2])
doc.add_heading("2.5 Supuestos, riesgos y restricciones", 2)
tabla(["Riesgo o supuesto", "Impacto", "Mitigación"], [
    ("Volumen de 65 millones de filas en una laptop", "Alto: se traba la carga y el dashboard", "Cargar por mes con COPY, índices al final, agregados precalculados para el tablero"),
    ("Cambios de aerolíneas por fusiones (US Airways con American, Virgin America con Alaska, entre otras)", "Medio: series por aerolínea con quiebres", "Documentar las fusiones en dim_airline y analizar con la aerolínea tal como reporta BTS cada año"),
    ("Las horas vienen en hora local, sin zona", "Medio: no se pueden comparar horas entre costas sin convertir", "Mapa aeropuerto a zona horaria y columna en UTC en la capa limpia"),
    ("Causas de retraso solo vienen para llegadas con 15 minutos o más", "Medio: no se pueden promediar causas sobre todos los vuelos", "Definir el universo en cada KPI y avisarlo en el dashboard"),
    ("2020 es atípico por la pandemia", "Alto: sesga tendencias y los modelos", "Descargar 2020 completo, perfilarlo aparte, reportar con y sin ese año y usar dim_fecha.periodo_covid como variable"),
    ("Cambios de definición de columnas en el período", "Bajo", "Comparar esquemas mensuales antes de cargar"),
], anchos=[5.6, 4.4, 6.0])
doc.add_heading("2.4 Plan de trabajo por rol", 2)
tabla(["Entregable de fase", "Responsable principal", "Apoyo"], [
    ("Documento Business Understanding, Canvas Data Product", "Data Administrator", "BI Analyst"),
    ("Inventario de fuentes, diccionario, informe de calidad", "Data Administrator", "Data Analyst (EDA)"),
    ("Scripts ETL y dataset limpio", "Data Engineering", "Data Administrator (reglas)"),
    ("Modelo en estrella y carga en Docker", "Data Engineering", "BI Analyst (diseño)"),
    ("KPI, wireframes y dashboard", "BI Analyst", "Data Administrator (definiciones)"),
    ("Hallazgos, insights y modelos (3 mínimos)", "Data Analyst", "Todo el equipo"),
], anchos=[7.0, 4.6, 4.4])
doc.add_heading("2.6 Canvas Data Product", 2)
tabla(["Bloque", "Contenido"], [
    ("Usuarios", "Analistas de operaciones de aerolíneas y aeropuertos; pasajeros frecuentes"),
    ("Problema", "Los retrasos se reportan en archivos enormes y no se ven patrones sin un modelo ordenado"),
    ("Producto de datos", "Modelo estrella en SQL, dataset limpio y dashboard público de puntualidad 2010 a 2020"),
    ("Fuentes", "BTS On-Time Reporting Carrier, tablas Get Lookup, calendario de feriados federales, lista de aeropuertos FAA (opcional), clima (opcional)"),
    ("Métricas de éxito", "KPI del dashboard iguales a los calculados directo de la fuente; ranking reproducible"),
    ("Riesgos", "Volumen, fusiones de aerolíneas, horas locales, año 2020"),
    ("Responsables", "Grupo 2: un Data Administrator, un BI Analyst, un Data Analyst y Data Engineering"),
], anchos=[3.8, 12.2])

# ------------------------------------------------------------------ 3
doc.add_heading("3. Data Understanding", 1)
doc.add_heading("3.1 Inventario de fuentes", 2)
tabla(["Fuente", "Contenido", "Cobertura", "Método de obtención"], [
    ("BTS TranStats, On-Time Reporting Carrier", f"Un registro por vuelo, 109 columnas; el pipeline carga {N_RAW} en raw.flights", "Enero 2010 a diciembre 2020, 132 archivos mensuales", "Descarga mensual con etl/p1_download.py. El manifiesto con hash SHA-256 de cada archivo está en docs/manifiesto_fuente.csv"),
    ("BTS Get Lookup Table", "Descripción de aerolíneas, aeropuertos y causas de cancelación", "Vigente al día de descarga", "etl/p4_load_reference.py baja las de aerolíneas y aeropuertos; la descarga manual desde la interfaz BTS queda como respaldo (ver README)"),
    ("Feriados federales de EE. UU.", "Fechas de feriados", "2010 a 2020", "Se carga en el esquema ref con etl/p4_load_reference.py"),
    ("Lista de aeropuertos FAA (opcional)", "Coordenadas y zona horaria", "Vigente", "Descarga pública, se versiona su fecha"),
    ("Clima (opcional)", "Condiciones por aeropuerto y día", "2010 a 2020", "Fuente pública por definir con el Data Analyst"),
], anchos=[3.8, 4.6, 3.8, 3.8])
p("El BTS publica estos datos en dominio público y los reportan las aerolíneas con al menos 1 % de los ingresos nacionales de "
  "pasajeros, así que no cubre a las aerolíneas pequeñas. Es una limitación que mencionamos en las conclusiones.")
doc.add_heading("3.2 Diccionario de datos", 2)
p("Elegimos los campos de las ocho categorías que pide el enunciado. Cada uno trae su tipo SQL propuesto, la unidad y si se "
  "esperan nulos, porque en esta fuente un nulo casi siempre tiene una explicación de negocio (por ejemplo, un vuelo cancelado "
  "no tiene hora de llegada). La última columna dice cómo se llama el campo en raw.flights, o 'no se carga' cuando el ETL no lo "
  "trae. El mismo contenido se entrega en docs/diccionario_datos.csv, y docs/columnas.md tiene la justificación de cada columna que carga el pipeline.")
cats = {}
for c in CAMPOS:
    cats.setdefault(c[2], []).append(c)
for cat, campos in cats.items():
    doc.add_heading(cat, 3)
    tabla(["Campo BTS", "Tipo SQL", "Descripción", "Unidad", "Nulos", "En raw.flights"],
          [(c[0], c[1], c[3], c[4], c[5], RAW_MAP.get(c[0], "no se carga")) for c in campos], anchos=[3.2, 1.8, 4.8, 2.0, 2.2, 2.6], tam=7.5)
doc.add_heading("Tablas Get Lookup y su destino", 3)
tabla(["Lookup BTS", "Se une con", "Destino en el modelo"], LOOKUPS, anchos=[4.0, 6.5, 5.5])
doc.add_heading("3.3 Metadatos técnicos y de negocio", 2)
tabla(["Metadato", "Valor"], [
    ("Nombre del conjunto", "bts_ontime_g2_2010_2020"),
    ("Propietario del dato", "Bureau of Transportation Statistics, U.S. Department of Transportation"),
    ("Custodio en el proyecto", "Data Administrator, grupo 2"),
    ("Granularidad", "Un vuelo programado por fila"),
    ("Clave natural", "FlightDate + Reporting_Airline + Flight_Number_Reporting_Airline + Origin + Dest + CRSDepTime"),
    ("Frecuencia de actualización de la fuente", "Mensual; para este proyecto el corte es estático (2010 a 2020)"),
    ("Codificación y formato", "CSV dentro de ZIP, UTF-8, separador coma, fechas AAAA-MM-DD, horas hhmm local"),
    ("Clasificación", "Público, sin datos personales"),
    ("Licencia y cita", "Dominio público; se cita como Bureau of Transportation Statistics (2024), TranStats Data Library"),
], anchos=[5.0, 11.0])
doc.add_heading("3.4 Observaciones sobre la fuente que afectan el análisis", 2)
lista([
    "Las horas vienen en hora local y en formato hhmm como entero. Medianoche puede aparecer como 2400 y las horas menores a 1000 pierden el cero a la izquierda.",
    "Un retraso negativo significa adelanto. Por eso la fuente trae también DepDelayMinutes y ArrDelayMinutes, que llegan a cero como mínimo.",
    "Los vuelos cancelados no traen horas reales ni retrasos, y los desviados no traen llegada. Esos nulos son legítimos y no se imputan.",
    "Las cinco columnas de causa de retraso solo se llenan cuando la llegada se atrasó 15 minutos o más.",
    "Las aerolíneas se fusionan en el período (por ejemplo Continental con United, AirTran con Southwest, US Airways con American, Virgin America con Alaska). Comparar una aerolínea entre 2010 y 2020 sin tomar eso en cuenta engaña.",
    "El año 2020 es el primer año de la pandemia y trae una caída fuerte del tráfico y un salto de cancelaciones desde marzo. Esos valores son reales, así que no se tratan como errores: 2020 se descarga completo aunque el resto sea muestra, se perfila aparte y se reporta con y sin ese año.",
])
doc.add_heading("3.5 Informe de calidad de datos", 2)
p("Medimos la calidad con trece reglas agrupadas por dimensión. Cada regla está implementada en calidad/perfilado_calidad.py y "
  "genera su conteo por archivo mensual, de modo que cualquier problema se rastrea hasta el mes que lo trae.")
tabla(["Id", "Dimensión", "Regla", "Tratamiento"], REGLAS, anchos=[1.0, 2.6, 7.4, 5.0], tam=8)
resumen = B / "docs" / "calidad" / "q_resumen_reglas.csv"
nulos = B / "docs" / "calidad" / "q_nulos_por_columna.csv"
if resumen.exists():
    df = pd.read_csv(resumen)
    df.columns = ["Métrica", "Total", "% de filas"]
    doc.add_heading("Resultado de la corrida de calidad", 3)
    tabla(list(df.columns), [(r[0], f"{int(r[1]):,}", f"{r[2]:.4f}") for r in df.itertuples(index=False)], anchos=[7.0, 4.0, 4.0])
    if nulos.exists():
        nd = pd.read_csv(nulos)
        nd = nd[nd["nulos"] > 0].sort_values("nulos", ascending=False).head(20)
        doc.add_heading("Columnas con más nulos", 3)
        tabla(["Columna", "Nulos", "% de filas"], [(r[0], f"{int(r[1]):,}", f"{r[2]:.2f}") for r in nd.itertuples(index=False)], anchos=[7.0, 4.0, 4.0])
    doc.add_heading("Lectura de la corrida completa", 3)
    p("La corrida cubre los 132 archivos mensuales de enero de 2010 a diciembre de 2020: 67,249,397 vuelos en 4,018 días.", italica=True)
    lista([
        "La fuente viene bastante limpia. No hay nulos en los campos obligatorios, ni banderas inválidas, ni horas fuera de rango, ni distancias no positivas. Hay 4 duplicados de la clave natural y 2 casos donde las causas no suman el retraso de llegada.",
        "Hay 969 vuelos normales sin retraso reportado (0.0014 %) y 352 donde ArrDel15 no coincide con ArrDelay (0.0005 %). Son pocos. En el modelo en estrella, los 352 sin ArrDel15 quedan con estado_vuelo 'Sin dato'; la cuarentena por código de regla sigue como propuesta.",
        "La regla R06 salió más estricta que la realidad. 39,234 vuelos cancelados (0.058 % del total, entre 600 y 1,200 por mes) sí traen hora de salida, porque se cancelaron después de salir de la puerta. No es error de captura: se conservan y se marcan con una bandera, no se rechazan.",
        "Los nulos grandes son legítimos. Las cinco causas de retraso vienen vacías en 82.1 % de los registros porque solo aplican a llegadas con 15 minutos o más. CancellationCode viene vacío en 98.1 % porque solo aplica a cancelados. ArrDelay vacío en 2.17 % corresponde a los cancelados y desviados.",
        "Las tres columnas de Gate Return (FirstDepTime, TotalAddGTime, LongestAddGTime) están vacías en 99.4 % de las filas. Que estén casi siempre vacías es lo esperado: solo traen valor los vuelos que regresaron a la puerta, unos 400 mil. Si la pregunta de regresos a puerta se queda en la lista final se conservan; si se descarta, no hace falta usarlas en el modelo en estrella ni en el dashboard.",
        "Se cancelaron 1,302,027 vuelos (1.94 %) y se desviaron 156,836 (0.23 %). Entre 2010 y 2019 la cancelación anual va de 1.17 % (2016) a 2.18 % (2014). En 2020 sube a 5.99 %, con 281,034 vuelos cancelados.",
        "El volumen anual baja de 7.4 millones de vuelos en 2019 a 4.7 millones en 2020. La tasa diaria de cancelación antes de 2020 tiene mediana de 0.87 %. Entre el 20 de marzo y el 10 de abril de 2020 va de 19.9 % a 53.2 %, con el pico del 30 de marzo. Esto confirma con datos el evento E24.",
        "Antes de 2020, los días más extremos son tormentas de invierno y huracanes: 33.6 % el 1 de febrero de 2011, 27.8 % el 29 de octubre de 2012 (Sandy), 27.5 % el 13 de febrero de 2014, 25.0 % el 14 de marzo de 2017 y 24.5 % el 23 de enero de 2016 (Jonas). Los eventos E26 a E30 se agregaron a la tabla porque el dato los mostró y no estaban en la lista inicial.",
        "El dato también confirma el vórtice polar del 6 de enero de 2014 (19 %), Irene el 28 de agosto de 2011 (20.8 %) y la falla de Southwest alrededor del 21 de julio de 2016. El 28 de enero de 2019 llega a 7.3 %, pero con estos datos no podemos separar el cierre de gobierno de otras causas; queda sin confirmar.",
    ])
    doc.add_heading("Verificación de la carga en el servidor", 3)
    p("El 26 de noviembre de 2026 comprobamos la base ya cargada (commit 9b8209f), en modo de solo lectura. La evidencia está en docs/calidad/servidor/.")
    tabla(["Control", "Resultado"], [
        ("Zips descargados contra el manifiesto SHA-256", "132 de 132 OK"),
        ("Filas por año: zip, raw.load_log y raw.flights", "11 de 11 años OK, con 12 meses cada uno"),
        ("Reglas de calidad y totales de control", "13 de 13 iguales a lo medido en la fuente"),
        ("raw.flights contra dw.fact_flights", "67,249,397 filas en ambas; diferencia 0"),
    ], anchos=[9.0, 7.0])
    p("La puntualidad se cita sobre vuelos operados (no cancelados ni desviados): 80.9 % en 2019 y 90.2 % en 2020. Sobre vuelos "
      "programados da 79.2 % y 84.6 %. El alza de 2020 coincide con la caída del tráfico, pero estas consultas no demuestran la causa.")
else:
    p("[PENDIENTE] Aquí se insertan los conteos de cada regla y el porcentaje de nulos por columna. Se llenan al correr "
      "00_descarga_bts.py, luego 01_perfilado_calidad.py, y regenerar este documento.", italica=True)

doc.add_heading("3.6 Eventos externos del período 2010 a 2020", 2)
p("Revisamos qué pasó en esos once años fuera de la operación normal de las aerolíneas. Sobre terrorismo la respuesta es corta: "
  "en este período no hubo en Estados Unidos un ataque que paralizara el espacio aéreo como el del 11 de septiembre de 2001, que "
  "queda fuera de nuestro rango. Lo que sí hubo fueron incidentes locales de seguridad, como el tiroteo en LAX en 2013 y el de Fort "
  "Lauderdale en 2017, que cerraron terminales por horas. Los marcamos, pero no justifican cortar la serie.")
p("Lo que de verdad mueve los datos son otras cosas: la pandemia de 2020, la suspensión de los Boeing 737 MAX desde marzo de 2019, "
  "el cierre de gobierno de diciembre de 2018 a enero de 2019, huracanes y tormentas de invierno grandes, fallas informáticas de "
  "Southwest y Delta en 2016, el incendio del centro de control de Chicago en 2014, y cambios regulatorios y corporativos que "
  "alteran las series. Dos de ellos merecen atención especial. La regla de la demora en pista de tres horas, vigente desde abril de "
  "2010, hace que las aerolíneas cancelen vuelos antes de arriesgar la multa, así que la tasa de cancelación de 2010 no es "
  "comparable del todo con la de años anteriores. Y la suspensión del 737 MAX se traslapa con la pandemia, de modo que en 2020 "
  "hay que separar los dos efectos por aerolínea antes de atribuirle todo al COVID.")
p("Las fechas las armamos con fuentes de referencia general y las confirmamos con los datos: el script de calidad generó "
  "q_cancelaciones_diarias.csv, y un evento real tiene que verse como un pico de cancelaciones ese mismo día. Si una fecha no "
  "aparece en el dato, se corrige o se descarta. El mismo contenido está en docs/eventos_externos.csv.")
tabla(["Id", "Inicio", "Fin", "Tipo", "Evento", "Tratamiento"],
      [(e[0], e[1], e[2], e[3], e[4], e[6]) for e in EVENTOS], anchos=[1.0, 2.0, 2.0, 2.2, 5.6, 3.6], tam=7.5)
p("Proponemos guardar esta tabla como ref_eventos_externos y unirla a dim_fecha con una columna es_evento (0/1) y otra evento_id. "
  "Así Data Analyst puede incluir o excluir esos días con un filtro, sin borrar nada de la fuente.")

doc.add_heading("3.7 Catálogo de aerolíneas", 2)
p("BTS no clasifica a las aerolíneas, así que armamos un catálogo con las 22 que aparecen en los datos: tradicionales, de bajo costo "
  "y regionales. La clasificación es criterio del equipo a partir del modelo de negocio conocido de cada aerolínea, no una "
  "categoría oficial, y está en docs/catalogo_aerolineas.csv. Sirve para la pregunta de aerolíneas de bajo costo contra tradicionales.")
cat = pd.read_csv(B / "docs" / "catalogo_aerolineas.csv")
tabla(["Código", "Aerolínea", "Tipo", "Años en los datos", "Vuelos", "Nota"],
      [(r.reporting_airline, r.nombre_comun, r.tipo_aerolinea,
        f"{r.anio_inicio_en_datos} a {r.anio_fin_en_datos}", f"{int(r.vuelos_2010_2020):,}", "" if pd.isna(r.nota) else r.nota)
       for r in cat.itertuples()], anchos=[1.3, 3.6, 2.0, 2.2, 2.2, 4.7], tam=7.5)
p("Cuatro cosas afectan cualquier comparación entre aerolíneas. Spirit solo aparece desde 2015, y Allegiant y Republic desde 2018, "
  "porque BTS solo recoge a las que superan cierto tamaño; comparar 2010 contra 2020 por aerolínea deja fuera a esas. Varias "
  "desaparecen por fusión (Continental, AirTran, US Airways, Virgin America, ExpressJet). Y los regionales (SkyWest, Envoy, Endeavor, "
  "PSA, Mesa, Republic, ExpressJet) vuelan para las grandes, así que un ranking que los mezcle con ellas confunde dos cosas distintas. "
  "Por último, un código puede pasar de una empresa a otra o tener años vacíos: OH es Comair en 2010 y PSA de 2018 a 2020, "
  "y 9E, MQ y YV no tienen datos en todos los años. Los años de la tabla son el primero y el último con datos.")

# ------------------------------------------------------------------ 4
doc.add_heading("4. Gobierno de datos y versionado", 1)
doc.add_heading("4.1 Roles y responsabilidades", 2)
tabla(["Rol", "Responsabilidad sobre el dato"], [
    ("Data Administrator", "Custodio. Aprueba diccionario, reglas de calidad, definición de KPI y cada cambio de versión"),
    ("Data Engineering", "Implementa las reglas en el ETL y publica la capa limpia; avisa si una regla no se puede cumplir"),
    ("BI Analyst", "Usa las definiciones oficiales de KPI; pide cambios a través del Data Administrator"),
    ("Data Analyst", "Consume solo versiones publicadas; reporta anomalías encontradas en el EDA"),
], anchos=[4.0, 12.0])
doc.add_heading("4.2 Capas y linaje", 2)
tabla(["Capa", "Contenido", "Quién escribe"], [
    ("data/raw_zip y data/parquet", "ZIP mensuales de BTS y su conversión a Parquet con solo las columnas seleccionadas", "etl/p1_download.py y p2_to_parquet.py"),
    ("raw", f"raw.flights: {N_RAW} columnas tipadas, una partición por año de 2010 a 2020", "etl/p3_load_raw.py"),
    ("ref", "Lookups de BTS (aerolíneas, aeropuertos) y feriados de EE. UU.", "etl/p4_load_reference.py"),
    ("dw", "Modelo estrella: fact_flights particionada por año y sus dimensiones", "etl/p5_build_star.py"),
    ("cuarentena (propuesta)", "Registros que fallen una regla R01 a R13, con el código de la regla; aún no existe en el ETL", "Por acordar con Data Engineering"),
], anchos=[2.6, 10.0, 3.4])
p("Para el linaje proponemos que cada versión del dataset registre qué archivos del manifiesto la alimentaron y cuántas filas entraron "
  "y salieron en cada paso. El log de data/logs ya guarda parte de eso; falta cruzarlo con los hashes del manifiesto.")
doc.add_heading("4.3 Convenciones de nombres", 2)
lista([
    "Tablas en minúsculas y snake_case: fact_flights, dim_airline, dim_airport, dim_fecha, dim_vuelo.",
    "Llaves sustitutas con sufijo _id (airline_id, fecha_id). La llave natural de BTS se conserva como columna aparte.",
    "Columnas del modelo en español como pide el enunciado (retraso_salida, retraso_llegada, estado_vuelo); las de raw.flights usan el nombre de BTS en snake_case.",
    "Fechas en formato ISO, horas en minutos desde medianoche o en TIME, nunca como hhmm entero en el modelo final.",
    "Banderas en SMALLINT 0/1 con prefijo es_ (es_cancelado, es_desviado, es_atipico, es_feriado).",
])
doc.add_heading("4.4 Versionado", 2)
p("Versionamos tres cosas por separado y las amarramos con una etiqueta.")
tabla(["Qué", "Cómo", "Ejemplo"], [
    ("Código y documentación", "Repositorio GitHub, ramas por rol y merge a main con revisión de otro compañero", "Tag v1.0.0"),
    ("Fuente cruda", "Manifiesto con SHA-256, tamaño y fecha de descarga por archivo, versionado en Git; los ZIP no se suben", "docs/manifiesto_fuente.csv"),
    ("Dataset limpio", "Versión semántica MAYOR.MENOR.PARCHE. Mayor si cambia el esquema, menor si cambia una regla, parche si se corrige un dato", "bts_clean_v1.2.0.parquet"),
], anchos=[4.0, 8.4, 3.6])
p("Cada versión del dataset lleva un archivo CHANGELOG con la fecha, el motivo y el conteo de filas antes y después. Si un número "
  "del informe final no cuadra con el dashboard, la primera pregunta es en qué versión se calculó cada uno.")
doc.add_heading("4.5 Control de cambios sobre reglas y KPI", 2)
p("Un cambio en una regla de calidad o en la fórmula de un KPI se pide por escrito en un issue del repositorio, lo aprueba el "
  "Data Administrator y sube la versión del dataset. Con esto evitamos el clásico caso de dos compañeros calculando la puntualidad "
  "de forma distinta y presentando cifras que no se parecen.")

# ------------------------------------------------------------------ 5
doc.add_heading("5. Lineamientos para Data Preparation", 1)
doc.add_heading("5.1 Selección, limpieza y estandarización", 2)
lista([
    f"El pipeline carga {N_RAW} de las 109 columnas de BTS en raw.flights. El diccionario documenta además {len(CAMPOS) - N_RAW} campos de la fuente que hoy no se cargan, por si el equipo los necesita.",
    "No se borra ningún vuelo por tener retraso extremo. Proponemos marcarlo con es_atipico (aún no implementado) y se decide en cada análisis. Esto sigue el principio de cargar todo y filtrar en el reporte.",
    "Los duplicados exactos de la clave natural se identifican y se cuentan en el log (en la fuente son solo 4).",
    "Las horas se convierten a minutos desde medianoche. El 2400 pasa a 0 y se suma un día cuando corresponde a la llegada.",
    "Zonas horarias: se le asigna a cada aeropuerto su zona IANA y se calcula salida y llegada en UTC, que es lo que permite comparar entre costas.",
])
doc.add_heading("5.2 Variables derivadas", 2)
tabla(["Variable", "Definición propuesta", "Estado"], [
    ("retraso_total", "Minutos de retraso positivo en la llegada (equivale a ArrDelayMinutes); nulo si el vuelo se canceló o se desvió. retraso_salida y retraso_llegada conservan el signo", "Implementada en sql/build/20_fact_flights.sql"),
    ("categoria_retraso", "Sin retraso (0 o menos), Leve (1 a 14), Moderado (15 a 59), Severo (60 a 179), Extremo (180 o más); nulo si cancelado o desviado", "Implementada"),
    ("estado_vuelo", "Cancelado, Desviado, Sin dato (operado sin ArrDel15: 352 vuelos), Retrasado (ArrDel15) o A tiempo, en ese orden de prioridad", "Implementada"),
    ("semana", "Semana ISO del año de FlightDate (dim_fecha.semana_iso)", "Implementada"),
    ("trimestre", "Trimestre calculado desde la fecha (dim_fecha.trimestre)", "Implementada"),
    ("es_evento", "1 si la fecha cae dentro de un evento de ref_eventos_externos; evento_id con el código", "Propuesta"),
    ("es_feriado", "Verdadero si la fecha es feriado federal de EE. UU. (dim_fecha.es_feriado)", "Implementada"),
    ("periodo_covid", "Verdadero desde el 1 de marzo de 2020 (dim_fecha.periodo_covid). Si el equipo quiere separar caída (marzo a junio) y recuperación (julio a diciembre) habría que agregar una columna", "Implementada como bandera simple"),
    ("franja_horaria", "Madrugada (antes de las 6), Mañana, Tarde (12 a 17) y Noche, según el bloque de salida programada (dim_bloque_horario)", "Implementada"),
], anchos=[3.2, 10.0, 2.8])
doc.add_heading("5.3 Integración", 2)
p("Unimos con las tablas Get Lookup por los identificadores numéricos (DOT), no por los códigos de texto, porque un código IATA "
  "puede reasignarse a otro aeropuerto con los años. Antes y después de cada unión se compara el conteo de filas y se registra "
  "en el log. Una unión que pierde registros es un error, no un detalle.")

doc.add_heading("5.4 Tratamiento de eventos externos en la capa de datos", 2)
p("Desde el gobierno de datos nuestra regla es sencilla: ningún período ni evento se borra de la fuente ni del dataset limpio. "
  "Los eventos de la sección 3.6, incluida la pandemia de 2020, se conservan completos y se identifican con periodo_covid, que ya existe en dim_fecha, "
  "y con es_evento y evento_id, que proponemos agregar a esa dimensión. Así cualquier compañero puede incluirlos o excluirlos con un filtro, y "
  "la versión del dataset deja claro con qué reglas se construyó.")
lista([
    "La tabla ref_eventos_externos se versiona junto al dataset; cambiar una fecha o agregar un evento sube la versión menor.",
    "periodo_covid usa la misma definición para todo el grupo: verdadero desde el 1 de marzo de 2020. Si el equipo la cambia, se registra en el CHANGELOG.",
    "Como casi todos los grupos de la clase tienen 2020 dentro de su rango, conviene acordar la definición con ellos para que las cifras sean comparables. El grupo 2 termina en diciembre de 2020, así que no observa la recuperación posterior.",
    "Qué períodos se excluyen en cada análisis o en el entrenamiento de los modelos lo deciden Data Analyst y el equipo. Cada cifra del informe debe decir si incluye o no esos períodos.",
])

# ------------------------------------------------------------------ 6
doc.add_heading("6. Pendientes del Data Administrator", 1)
tabla(["Tarea", "Estado"], [
    ("Diccionario de datos, metadatos y reglas de calidad", "Listo en este documento y en docs/"),
    ("Scripts de descarga y perfilado", "Listos y corridos con los 132 archivos"),
    ("Confirmar que etl/p4_load_reference.py carga bien las lookups de BTS", "Hecho: versionadas en data/lookups/"),
    ("Informe de calidad con cifras reales", "Listo, sección 3.5"),
    ("Acordar con el equipo la definición de periodo_covid y de los eventos", "Pendiente"),
    ("Revisar con Data Engineering que las reglas R01 a R13 queden en el ETL", "Pendiente"),
    ("Repositorio GitHub con ramas y CHANGELOG", "Hecho"),
    ("Etiqueta de versión en Git", "Pendiente"),
    ("Integrar secciones de los demás roles y exportar a PDF", "Pendiente"),
], anchos=[11.0, 5.0])

doc.add_heading("Referencias", 1)
for r in [
    "Bureau of Transportation Statistics. (2024). TranStats Data Library. U.S. Department of Transportation. https://www.transtats.bts.gov/",
    "Han, J., Kamber, M., & Pei, J. (2022). Data mining: Concepts and techniques (4th ed.). Morgan Kaufmann.",
    "Kimball, R., & Ross, M. (2013). The data warehouse toolkit: The definitive guide to dimensional modeling (3rd ed.). Wiley.",
    "Larose, D. T., & Larose, C. D. (2019). Discovering knowledge in data: An introduction to data mining (3rd ed.). Wiley.",
    "Sharma, S. (2021). Data engineering with Python. Packt Publishing.",
]:
    doc.add_paragraph(r)

# actualizar campos (indice) al abrir
ajustes = doc.settings.element
uf = OxmlElement("w:updateFields")
uf.set(qn("w:val"), "true")
ajustes.append(uf)
doc.save(OUT)
print("Guardado", OUT)
