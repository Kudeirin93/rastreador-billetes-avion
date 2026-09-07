import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import datetime

import airportsdata
import urllib.request
import json
import math
import sqlite3
from pathlib import Path

# ============================================================
# CONFIGURACION GENERAL
# ============================================================

st.set_page_config(page_title="Buscador Vuelos", page_icon="✈️", layout="wide")

CURRENCY = "EUR"
HL = "es"
GL = "es"
CACHE_TTL = 3600
DB_PATH = Path("flight_history.sqlite3")
ANYWHERE_OPTION = "🌍 Cualquier lugar"
ANYWHERE_STORAGE_KEY = "__ANYWHERE__"

page_bg_img = """
<style>
/* 1. Restaurar la imagen de fondo con degradado oscuro para la pantalla principal */
.stApp {
    background-image: linear-gradient(rgba(14, 17, 23, 0.75), rgba(14, 17, 23, 0.85)),
    url("https://images.unsplash.com/photo-1542296332-2e4473faf563?q=80&w=2000&auto=format&fit=crop") !important;
    background-size: cover !important;
    background-position: center !important;
    background-attachment: fixed !important;
}

/* 2. Restaurar colores, degradado y borde delimitador del panel lateral (Sidebar) */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(17, 21, 30, 0.95) 0%, rgba(28, 33, 45, 0.95) 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
}

/* 3. Ajustes de espaciado */
.block-container {
    padding-top: 2rem !important;
}
[data-testid="stStatusWidget"] {
    margin-top: -10px;
}
[data-testid="stMetric"] {
    padding-top: 0.5rem !important;
    padding-bottom: 0rem !important;
}
[data-testid="stSidebarUserContent"] {
    padding-top: 0.4rem !important;
    padding-bottom: 0.4rem !important;
}

/* 4. Forzar texto claro sobre el fondo oscuro, independientemente de si el
      usuario tiene activado el modo claro o el modo oscuro de Streamlit.
      El fondo de la app siempre es oscuro (imagen + degradado), así que el
      texto debe permanecer claro pase lo que pase con el tema del sistema. */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
.stApp [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stMarkdownContainer"] h1,
.stApp [data-testid="stMarkdownContainer"] h2,
.stApp [data-testid="stMarkdownContainer"] h3,
.stApp [data-testid="stMarkdownContainer"] h4,
.stApp [data-testid="stMetricLabel"] p,
.stApp [data-testid="stMetricValue"],
.stApp [data-testid="stCaptionContainer"] {
    color: #FAFAFA !important;
}

/* 5. Los campos de fecha (selector de año/mes/día) y los cuadros de texto
      numérico se dibujan siempre sobre una superficie blanca propia:
      su texto debe permanecer oscuro pase lo que pase con el tema. */
[data-testid="stDateInputField"] span[role="spinbutton"],
[data-testid="stDateInputField"] span[data-type="literal"] {
    color: #262730 !important;
}

/* 6. Desplegables de origen/destino: mostrar el triple de opciones antes
      de necesitar scroll (por defecto Streamlit limita el listbox a
      300px, unas 7-8 filas). Se cubren ambas variantes del componente
      selectbox que ha usado Streamlit (versiones recientes basadas en
      react-aria y versiones anteriores basadas en BaseWeb), además de un
      selector genérico por si cambia de nuevo en el futuro. */
[data-testid="stSelectboxVirtualDropdown"],
[data-testid="stSelectboxVirtualDropdown"] [role="listbox"],
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="menu"],
ul[role="listbox"],
div[role="listbox"] {
    max-height: min(900px, 85vh) !important;
}

/* 7. En columnas estrechas (checkboxes con tooltip de ayuda), el texto de
      la etiqueta no debe cortarse: que haga salto de línea en vez de
      recortarse con overflow. */
[data-testid="stSidebar"] [data-testid="stCheckbox"] label p {
    white-space: normal !important;
    line-height: 1.2 !important;
}

/* 8. Ajustar márgenes de los Títulos del Sidebar (Espacio abajo) */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.8rem !important; /* Espacio vital entre filas para evitar solapamientos */
}
[data-testid="stSidebar"] hr {
    margin: 1.2rem 0 1rem 0 !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    margin-top: 0.5rem !important;
    margin-bottom: 0.8rem !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    line-height: 1.15 !important;
}

/* 9. SUBIR EL TÍTULO PRINCIPAL (De forma segura sin romper columnas) */
[data-testid="stSidebarUserContent"] {
    padding-top: 0rem !important;
    padding-bottom: 0.4rem !important;
}
/* Movemos SOLO el texto h2 del primer bloque hacia arriba, dejando los inputs tranquilos */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:first-child h2 {
    margin-top: -3.5rem !important; 
}
</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>Buscador de Vuelos Low-Cost ✈️</h1>", unsafe_allow_html=True)

# ============================================================
# DATOS AUXILIARES
# ============================================================

# Diccionario de conversión de códigos ISO a nombres de países en español
PAISES_ES = {
    "AF": "Afganistán", "AL": "Albania", "DE": "Alemania", "AD": "Andorra", "AO": "Angola", "AG": "Antigua y Barbuda",
    "SA": "Arabia Saudita", "DZ": "Argelia", "AR": "Argentina", "AM": "Armenia", "AU": "Australia", "AT": "Austria",
    "BS": "Bahamas", "BD": "Bangladés", "BB": "Barbados", "BH": "Baréin", "BE": "Bélgica", "BZ": "Belice",
    "BJ": "Benín", "BY": "Bielorrusia", "BO": "Bolivia", "BA": "Bosnia y Herzegovina", "BW": "Botsuana",
    "BR": "Brasil", "BG": "Bulgaria", "BF": "Burkina Faso", "BI": "Burundi", "BT": "Bután", "CV": "Cabo Verde",
    "KH": "Camboya", "CM": "Camerún", "CA": "Canadá", "QA": "Catar", "TD": "Chad", "CL": "Chile", "CN": "China",
    "CY": "Chipre", "CO": "Colombia", "KM": "Comoras", "KP": "Corea del Norte", "KR": "Corea del Sur",
    "CI": "Costa de Marfil", "CR": "Costa Rica", "HR": "Croacia", "CU": "Cuba", "DK": "Dinamarca",
    "EC": "Ecuador", "EG": "Egipto", "SV": "El Salvador", "AE": "Emiratos Árabes Unidos", "ER": "Eritrea",
    "SK": "Eslovaquia", "SI": "Eslovenia", "ES": "España", "US": "Estados Unidos", "EE": "Estonia",
    "ET": "Etiopía", "PH": "Filipinas", "FI": "Finlandia", "FJ": "Fiyi", "FR": "Francia", "GA": "Gabón",
    "GM": "Gambia", "GE": "Georgia", "GH": "Ghana", "GD": "Granada", "GR": "Grecia", "GT": "Guatemala",
    "GN": "Guinea", "GQ": "Guinea Ecuatorial", "GW": "Guinea-Bisáu", "GY": "Guyana", "HT": "Haití",
    "HN": "Honduras", "HU": "Hungría", "IN": "India", "ID": "Indonesia", "IQ": "Irak", "IR": "Irán",
    "IE": "Irlanda", "IS": "Islandia", "MH": "Islas Marshall", "SB": "Islas Salomón", "IL": "Israel",
    "IT": "Italia", "JM": "Jamaica", "JP": "Japón", "JO": "Jordania", "KZ": "Kazajistán", "KE": "Kenia",
    "KG": "Kirguistán", "KI": "Kiribati", "KW": "Kuwait", "LA": "Laos", "LS": "Lesoto", "LV": "Letonia",
    "LB": "Líbano", "LR": "Liberia", "LY": "Libia", "LI": "Liechtenstein", "LT": "Lituania", "LU": "Luxemburgo",
    "MK": "Macedonia del Norte", "MG": "Madagascar", "MY": "Malasia", "MW": "Malaui", "MV": "Maldivas",
    "ML": "Malí", "MT": "Malta", "MA": "Marruecos", "MU": "Mauricio", "MR": "Mauritania", "MX": "México",
    "FM": "Micronesia", "MD": "Moldavia", "MC": "Mónaco", "MN": "Mongolia", "ME": "Montenegro",
    "MZ": "Mozambique", "MM": "Myanmar", "NA": "Namibia", "NR": "Nauru", "NP": "Nepal", "NI": "Nicaragua",
    "NE": "Níger", "NG": "Nigeria", "NO": "Noruega", "NZ": "Nueva Zelanda", "OM": "Omán", "NL": "Países Bajos",
    "PK": "Pakistán", "PW": "Palaos", "PA": "Panamá", "PG": "Papúa Nueva Guinea", "PY": "Paraguay",
    "PE": "Perú", "PL": "Polonia", "PT": "Portugal", "UK": "Reino Unido", "GB": "Reino Unido",
    "CF": "República Centroafricana", "CZ": "República Checa", "CG": "República del Congo",
    "CD": "República Democrática del Congo", "DO": "República Dominicana", "RW": "Ruanda", "RO": "Rumania",
    "RU": "Rusia", "WS": "Samoa", "KN": "San Cristóbal y Nieves", "SM": "San Marino",
    "VC": "San Vicente y las Granadinas", "LC": "Santa Lucía", "ST": "Santo Tomé y Príncipe",
    "SN": "Senegal", "RS": "Serbia", "SC": "Seychelles", "SL": "Sierra Leona", "SG": "Singapur",
    "SY": "Siria", "SO": "Somalia", "LK": "Sri Lanka", "SZ": "Esuatini", "ZA": "Sudáfrica", "SD": "Sudán",
    "SS": "Sudán del Sur", "SE": "Suecia", "CH": "Suiza", "SR": "Surinam", "TH": "Tailandia", "TZ": "Tanzania",
    "TJ": "Tayikistán", "TL": "Timor Oriental", "TG": "Togo", "TO": "Tonga", "TT": "Trinidad y Tobago",
    "TN": "Túnez", "TM": "Turkmenistán", "TR": "Turquía", "TV": "Tuvalu", "UA": "Ucrania", "UG": "Uganda",
    "UY": "Uruguay", "UZ": "Uzbekistán", "VU": "Vanuatu", "VE": "Venezuela", "VN": "Vietnam",
    "YE": "Yemen", "DJ": "Yibuti", "ZM": "Zambia", "ZW": "Zimbabue",
}

@st.cache_data
def load_airports():
    return airportsdata.load("IATA")

airports = load_airports()

@st.cache_data
def obtener_opciones_aeropuertos():
    opciones = []
    for iata, info in airports.items():
        if len(iata) == 3 and info.get('city'):
            ciudad = info.get('city', '').strip()
            codigo_pais = info.get('country', '').strip().upper()
            
            # Traducimos el código ISO al español
            nombre_pais = PAISES_ES.get(codigo_pais, codigo_pais)
            
            if ciudad:
                # Se cambia la coma por el guion espaciado
                opciones.append(f"{ciudad} - {nombre_pais} ({iata})")
                
    return sorted(list(set(opciones)))

opciones_busqueda = obtener_opciones_aeropuertos()

airports = load_airports()

def buscar_indice_por_iata(iata, opciones):
    iata = iata.upper()
    for i, opc in enumerate(opciones):
        if opc.endswith(f"({iata})"):
            return i
    return 0


def _opciones_desde_iatas(iatas, opciones):
    """Convierte una lista/cadena de IATA en las opciones visibles del multiselect."""
    if isinstance(iatas, str):
        iatas = [x.strip().upper() for x in iatas.split(",") if x.strip()]
    defaults = []
    for iata in iatas or []:
        for opc in opciones:
            if opc.endswith(f"({iata})"):
                defaults.append(opc)
                break
    return defaults


def extraer_iatas(selecciones):
    """Extrae y deduplica los códigos IATA de las opciones seleccionadas."""
    codigos = []
    for seleccion in selecciones or []:
        if seleccion == ANYWHERE_OPTION:
            continue
        try:
            codigo = seleccion.rsplit("(", 1)[-1].replace(")", "").strip().upper()
        except Exception:
            continue
        if len(codigo) == 3 and codigo not in codigos:
            codigos.append(codigo)
    return codigos


def seleccion_cualquier_lugar(selecciones):
    return ANYWHERE_OPTION in (selecciones or [])


def selector_aeropuertos(label, iatas_por_defecto, key_prefix, permitir_cualquier_lugar=False, cualquier_lugar_por_defecto=False):
    """Permite seleccionar uno o varios aeropuertos/ciudades simultáneamente.

    SerpApi acepta múltiples departure_id / arrival_id separados por comas.
    Para "Cualquier lugar" NO usamos engine=google_flights sin arrival_id,
    porque ese endpoint puede rechazar la petición con "Missing arrival_id".
    La búsqueda abierta se resuelve con Google Travel Explore y, después de
    elegir destino, se vuelve a Google Flights para mostrar vuelos concretos.
    """
    defaults = _opciones_desde_iatas(iatas_por_defecto, opciones_busqueda)
    if permitir_cualquier_lugar and cualquier_lugar_por_defecto:
        defaults = [ANYWHERE_OPTION]
    options = ([ANYWHERE_OPTION] if permitir_cualquier_lugar else []) + opciones_busqueda
    placeholder = (
        "🌍 Cualquier lugar o añade destinos..."
        if permitir_cualquier_lugar
        else "🔎 Añade una o varias ciudades/aeropuertos..."
    )
    return st.sidebar.multiselect(
        label,
        options=options,
        default=defaults,
        placeholder=placeholder,
        key=f"{key_prefix}_multi",
    )

AIRLINES = {
    "Aer Lingus (EI)": "EI",
    "Air Europa (UX)": "UX",
    "Air France (AF)": "AF",
    "Air Serbia (JU)": "JU",
    "American Airlines (AA)": "AA",
    "Austrian Airlines (OS)": "OS",
    "Binter Canarias (NT)": "NT",
    "British Airways (BA)": "BA",
    "Brussels Airlines (SN)": "SN",
    "Delta (DL)": "DL",
    "easyJet (U2)": "U2",
    "Emirates (EK)": "EK",
    "Etihad Airways (EY)": "EY",
    "Eurowings (EW)": "EW",
    "Iberia (IB)": "IB",
    "Iberia Express (I2)": "I2",
    "ITA Airways (AZ)": "AZ",
    "KLM (KL)": "KL",
    "LEVEL (LL)": "LL",
    "LOT (LO)": "LO",
    "Lufthansa (LH)": "LH",
    "Norwegian (DY)": "DY",
    "Norwegian Air Sweden (D8)": "D8",
    "Pegasus (PC)": "PC",
    "Qatar Airways (QR)": "QR",
    "Ryanair (FR)": "FR",
    "Ryanair UK (RK)": "RK",
    "SWISS (LX)": "LX",
    "TAP Air Portugal (TP)": "TP",
    "Transavia France (TO)": "TO",
    "Transavia (HV)": "HV",
    "Turkish Airlines (TK)": "TK",
    "United (UA)": "UA",
    "Volotea (V7)": "V7",
    "Vueling (VY)": "VY",
    "Wizz Air Malta (W4)": "W4",
    "Wizz Air Hungary (W6)": "W6",
    "Wizz Air UK (W9)": "W9",
}

CABIN_CLASSES = {
    "Turista": "1",
    "Turista Premium": "2",
    "Business": "3",
    "Primera Clase": "4",
}

STOPS_OPTIONS = {
    "Cualquier número de escalas": "0",
    "Solo directos": "1",
    "Máximo 1 escala": "2",
    "Máximo 2 escalas": "3",
}

SORT_OPTIONS = {
    "Mejores vuelos": "1",
    "Precio": "2",
    "Hora de salida": "3",
    "Hora de llegada": "4",
    "Duración": "5",
    "Emisiones": "6",
}

PRICE_LEVELS = {
    "low": "🟢 Bajo",
    "typical": "🟡 Habitual",
    "high": "🔴 Alto",
}

EXPLORE_DURATION = {
    "Fin de semana": "1",
    "1 semana": "2",
    "2 semanas": "3",
}

EXPLORE_INTEREST = {
    "Popular": None,
    "Naturaleza": "/g/11bc58l13w",
    "Playas": "/m/0b3yr",
    "Museos": "/m/09cmq",
    "Historia": "/m/03g3w",
    "Esquí": "/m/071k0",
}

MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

def build_explore_months():
    today = datetime.date.today()
    months = {}
    for offset in range(6):
        month_num = ((today.month - 1 + offset) % 12) + 1
        year = today.year + ((today.month - 1 + offset) // 12)
        months[f"{MONTH_NAMES[month_num]} {year}"] = month_num
    return months

# Meses concretos disponibles para explorar (próximos 6 meses). Se eligen
# uno o varios (no todos por defecto): es poco realista que el usuario
# tenga disponibilidad los 6 meses completos.
MONTHS = build_explore_months()


def obtener_pais(iata_code):
    try:
        codigo = airports[iata_code.upper()]["country"]
        return PAISES_ES.get(codigo, codigo)
    except Exception:
        return ""


def fmt_minutes(minutes):
    if minutes is None or pd.isna(minutes):
        return "N/A"
    minutes = int(minutes)
    return f"{minutes // 60:02d}h {minutes % 60:02d}m"


def unique_join(values):
    seen = []
    for value in values:
        value = (value or "").strip()
        if value and value not in seen:
            seen.append(value)
    return ", ".join(seen)


def obtener_info_cuenta(api_key):
    try:
        url = f"https://serpapi.com/account?api_key={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get("searches_per_month", "N/A"), data.get("total_searches_left", "N/A")
    except Exception:
        return None, None

# ============================================================
# AEROPUERTOS CERCANOS
# ============================================================


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def obtener_lista_aeropuertos(iata_base, radio_km):
    iata_base = iata_base.upper().strip()
    if iata_base not in airports:
        return iata_base

    lat_base = airports[iata_base]["lat"]
    lon_base = airports[iata_base]["lon"]

    cercanos = []
    for iata, info in airports.items():
        if len(iata) != 3:
            continue
        try:
            dist = haversine(lat_base, lon_base, info["lat"], info["lon"])
            if dist <= radio_km:
                cercanos.append((iata, dist))
        except Exception:
            continue

    cercanos.sort(key=lambda x: x[1])
    return ",".join([iata for iata, _ in cercanos[:5]])


def expandir_aeropuertos_cercanos(iatas_base, radio_km, max_por_base=5):
    """Expande varios aeropuertos base con sus aeropuertos cercanos y deduplica."""
    resultado = []
    for iata_base in iatas_base or []:
        encontrados = obtener_lista_aeropuertos(iata_base, radio_km).split(",")
        for codigo in encontrados[:max_por_base]:
            codigo = codigo.strip().upper()
            if codigo and codigo not in resultado:
                resultado.append(codigo)
    return ",".join(resultado)

# ============================================================
# PERSISTENCIA LOCAL: HISTORICO Y ALERTAS
# ============================================================


def init_db():
    """Inicializa las tablas locales usadas por histórico, alertas y presets.

    Nota: en Streamlit Community Cloud el fichero SQLite local es efímero.
    La capa se mantiene aislada para poder sustituirla más adelante por una
    base de datos persistente sin cambiar la lógica de la aplicación.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    outbound_date TEXT NOT NULL,
                    return_date TEXT,
                    travel_class TEXT,
                    adults INTEGER,
                    price REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    outbound_date TEXT NOT NULL,
                    return_date TEXT,
                    max_price REAL NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    config TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
    except Exception:
        pass


def guardar_busqueda(name, config_dict):
    name = (name or "").strip()
    if not name:
        return False
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO saved_searches (name, config, created_at) VALUES (?, ?, ?)",
                (name, json.dumps(config_dict, ensure_ascii=False), datetime.datetime.now().isoformat(timespec="seconds"))
            )
            conn.commit()
        return True
    except Exception:
        return False


def cargar_busquedas():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return pd.read_sql_query(
                "SELECT id, name, config, created_at FROM saved_searches ORDER BY created_at DESC",
                conn,
            )
    except Exception:
        return pd.DataFrame()


def eliminar_busqueda(b_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM saved_searches WHERE id = ?", (int(b_id),))
            conn.commit()
        return True
    except Exception:
        return False


def construir_config_guardable(search_state):
    """Extrae únicamente configuración reproducible, nunca resultados/tokens de selección."""
    return {
        "version": 2,
        "params": dict(search_state.get("params", {})),
        "detail_params": dict(search_state.get("detail_params", {})),
        "origin": search_state.get("origin", ""),
        "destination": search_state.get("destination", ""),
        "origin_ids": list(search_state.get("origin_ids", [])),
        "destination_ids": list(search_state.get("destination_ids", [])),
        "destination_anywhere": bool(search_state.get("destination_anywhere", False)),
        "outbound_date": str(search_state.get("outbound_date", "")),
        "return_date": str(search_state.get("return_date", "")) if search_state.get("return_date") else None,
        "travel_class": search_state.get("travel_class", "1"),
        "adults": int(search_state.get("adults", 1)),
        "children": int(search_state.get("children", 0)),
        "passengers": int(search_state.get("passengers", 1)),
        "flexible_ida": bool(search_state.get("flexible_ida", False)),
        "radius_ida": int(search_state.get("radius_ida", 0)),
        "flexible_vuelta": bool(search_state.get("flexible_vuelta", False)),
        "radius_vuelta": int(search_state.get("radius_vuelta", 0)),
    }


def resumen_config_guardada(config):
    origen = config.get("origin") or "Origen automático"
    destino = "Cualquier lugar" if config.get("destination_anywhere") else (config.get("destination") or "—")
    ida = config.get("outbound_date") or "—"
    vuelta = config.get("return_date")
    fechas = f"{ida} → {vuelta}" if vuelta else ida
    pax = config.get("passengers", 1)
    return f"{origen} → {destino} · {fechas} · {pax} viajero(s)"


def ejecutar_busqueda_guardada(config):
    """Repite una configuración guardada y reconstruye `flight_search`."""
    params = dict(config.get("params") or {})
    if not params:
        raise ValueError("La búsqueda guardada no contiene parámetros de SerpApi.")

    destino_anywhere = bool(config.get("destination_anywhere", False))

    # Compatibilidad con presets creados por la versión anterior: aquella
    # intentaba `google_flights` sin arrival_id y SerpApi respondía con
    # "Missing arrival_id parameter". Los migramos automáticamente a Explore.
    if destino_anywhere and params.get("engine") != "google_travel_explore":
        params = convertir_params_flights_a_explore(params)

    result = serp_search(params)
    pasajeros = max(1, int(config.get("passengers", 1)))
    if destino_anywhere:
        df = destinos_anywhere_a_df(result, num_pasajeros=pasajeros)
    else:
        df = vuelos_a_df(result, num_pasajeros=pasajeros)

    outbound_date = datetime.datetime.strptime(config["outbound_date"], "%Y-%m-%d").date()
    return_date = None
    if config.get("return_date"):
        return_date = datetime.datetime.strptime(config["return_date"], "%Y-%m-%d").date()

    detail_params = dict(config.get("detail_params") or {})
    if destino_anywhere and not detail_params:
        detail_params = detalle_flights_desde_explore(params)

    state = {
        "params": params,
        "detail_params": detail_params,
        "result": result,
        "df": df,
        "origin": config.get("origin", ""),
        "destination": config.get("destination", ANYWHERE_STORAGE_KEY if destino_anywhere else ""),
        "outbound_date": outbound_date,
        "return_date": return_date,
        "travel_class": config.get("travel_class", params.get("travel_class", "1")),
        "adults": int(config.get("adults", params.get("adults", 1))),
        "children": int(config.get("children", params.get("children", 0))),
        "passengers": pasajeros,
        "origin_ids": list(config.get("origin_ids", [])),
        "destination_ids": list(config.get("destination_ids", [])),
        "destination_anywhere": destino_anywhere,
        "flexible_ida": bool(config.get("flexible_ida", False)),
        "radius_ida": int(config.get("radius_ida", 0)),
        "flexible_vuelta": bool(config.get("flexible_vuelta", False)),
        "radius_vuelta": int(config.get("radius_vuelta", 0)),
    }
    st.session_state["flight_search"] = state
    st.session_state.pop("return_search", None)
    st.session_state.pop("anywhere_detail", None)

    if not df.empty and "Precio_Num" in df.columns and df["Precio_Num"].notna().any():
        guardar_precio(
            state["origin"],
            state["destination"],
            outbound_date,
            return_date,
            state["travel_class"],
            state["adults"],
            df["Precio_Num"].min(),
        )
    return state


def guardar_precio(origin, destination, outbound_date, return_date, travel_class, adults, price):
    if price is None or pd.isna(price):
        return
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO price_history
                (timestamp, origin, destination, outbound_date, return_date, travel_class, adults, price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.datetime.now().isoformat(timespec="seconds"),
                    origin,
                    destination,
                    str(outbound_date),
                    str(return_date) if return_date else None,
                    travel_class,
                    int(adults),
                    float(price),
                ),
            )
            conn.commit()
    except Exception:
        pass


def obtener_historico(origin, destination, outbound_date, return_date):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query(
                """
                SELECT timestamp, price
                FROM price_history
                WHERE origin = ?
                  AND destination = ?
                  AND outbound_date = ?
                  AND COALESCE(return_date, '') = COALESCE(?, '')
                ORDER BY timestamp
                """,
                conn,
                params=(
                    origin,
                    destination,
                    str(outbound_date),
                    str(return_date) if return_date else None,
                ),
            )
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception:
        return pd.DataFrame()


def crear_alerta(origin, destination, outbound_date, return_date, max_price):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO price_alerts
                (created_at, origin, destination, outbound_date, return_date, max_price, active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    datetime.datetime.now().isoformat(timespec="seconds"),
                    origin,
                    destination,
                    str(outbound_date),
                    str(return_date) if return_date else None,
                    float(max_price),
                ),
            )
            conn.commit()
        return True
    except Exception:
        return False


def alertas_activadas(origin, destination, outbound_date, return_date, current_price):
    if current_price is None or pd.isna(current_price):
        return pd.DataFrame()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return pd.read_sql_query(
                """
                SELECT id, max_price, created_at
                FROM price_alerts
                WHERE active = 1
                  AND origin = ?
                  AND destination = ?
                  AND outbound_date = ?
                  AND COALESCE(return_date, '') = COALESCE(?, '')
                  AND ? <= max_price
                ORDER BY max_price
                """,
                conn,
                params=(
                    origin,
                    destination,
                    str(outbound_date),
                    str(return_date) if return_date else None,
                    float(current_price),
                ),
            )
    except Exception:
        return pd.DataFrame()


def listar_alertas():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return pd.read_sql_query(
                """
                SELECT id, origin, destination, outbound_date, return_date, max_price, created_at
                FROM price_alerts
                WHERE active = 1
                ORDER BY created_at DESC
                """,
                conn,
            )
    except Exception:
        return pd.DataFrame()


def desactivar_alerta(alert_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE price_alerts SET active = 0 WHERE id = ?", (int(alert_id),))
            conn.commit()
        return True
    except Exception:
        return False


init_db()

# ============================================================
# SERPAPI: CAPA CACHEADA
# ============================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def ejecutar_serp(params_json):
    params = json.loads(params_json)
    params["api_key"] = st.secrets["SERPAPI_API_KEY"]
    search = GoogleSearch(params)
    result = search.get_dict()
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result


def serp_search(params):
    clean_params = {k: v for k, v in params.items() if v is not None and v != ""}
    params_json = json.dumps(clean_params, sort_keys=True, separators=(",", ":"))
    return ejecutar_serp(params_json)

# ============================================================
# PARSEO DE RESULTADOS
# ============================================================


def extraer_items_vuelos(results):
    return results.get("best_flights", []) + results.get("other_flights", [])


def vuelos_a_df(results, num_pasajeros=1):
    rows = []
    num_pasajeros = max(1, int(num_pasajeros or 1))

    for item_idx, item in enumerate(extraer_items_vuelos(results)):
        legs = item.get("flights", [])
        if not legs:
            continue

        first = legs[0]
        last = legs[-1]
        dep = first.get("departure_airport", {})
        arr = last.get("arrival_airport", {})
        dep_dt = dep.get("time", "")
        arr_dt = arr.get("time", "")
        dep_date, dep_time = dep_dt.split(" ", 1) if " " in dep_dt else (dep_dt, "")
        arr_date, arr_time = arr_dt.split(" ", 1) if " " in arr_dt else (arr_dt, "")

        airlines = unique_join([leg.get("airline", "") for leg in legs])
        flight_numbers = unique_join([leg.get("flight_number", "") for leg in legs])
        stops = max(0, len(legs) - 1)
        total_duration = item.get("total_duration")

        if total_duration is None:
            total_duration = sum(
                leg.get("duration", 0)
                for leg in legs
                if isinstance(leg.get("duration"), (int, float))
            )

        carbon = item.get("carbon_emissions", {}) or {}

        rows.append({
            "_row_id": item_idx,
            "Aerolínea": airlines,
            "Vuelo": flight_numbers,
            "Precio_Num": item.get("price"),
            "_Origen_IATA": dep.get("id", ""),
            "_Destino_IATA": arr.get("id", ""),
            "Origen": f"{dep.get('id', '')} ({obtener_pais(dep.get('id', ''))})",
            "Fecha Salida": dep_date,
            "Hora Salida": dep_time,
            "Destino": f"{arr.get('id', '')} ({obtener_pais(arr.get('id', ''))})",
            "Fecha Llegada": arr_date,
            "Hora Llegada": arr_time,
            "Escalas_Num": stops,
            "Escalas": "Directo" if stops == 0 else f"{stops} escala(s)",
            "Duración_Min": total_duration,
            "Tiempo Total": fmt_minutes(total_duration),
            "CO2_g": carbon.get("this_flight"),
            "Tipo": item.get("type", ""),
            "_departure_token": item.get("departure_token"),
            "_booking_token": item.get("booking_token"),
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["Precio_Num"] = pd.to_numeric(df["Precio_Num"], errors="coerce")
    df["Precio_Persona_Num"] = df["Precio_Num"] / num_pasajeros
    df = df.sort_values(["Precio_Num", "Duración_Min"], na_position="last").reset_index(drop=True)
    df["Precio"] = df["Precio_Num"].apply(lambda x: f"{int(round(x))} €" if pd.notna(x) else "N/A")
    df["Precio/persona"] = df["Precio_Persona_Num"].apply(
        lambda x: f"{int(round(x))} €" if pd.notna(x) else "N/A"
    )
    return df


DISPLAY_COLUMNS = [
    "Aerolínea",
    "Vuelo",
    "Precio",
    "Precio/persona",
    "Origen",
    "Fecha Salida",
    "Hora Salida",
    "Destino",
    "Fecha Llegada",
    "Hora Llegada",
    "Escalas",
    "Tiempo Total",
]


def mostrar_df_vuelos(df, titulo=None):
    if titulo:
        st.markdown(f"**{titulo}**")
    if df.empty:
        st.warning("No se encontraron vuelos con los filtros seleccionados.")
        return
    columnas = [c for c in DISPLAY_COLUMNS if c in df.columns]
    st.dataframe(df[columnas], hide_index=True, use_container_width=True)


def flight_label(row):
    return (
        f"{row.get('Precio', 'N/A')} total · {row.get('Precio/persona', 'N/A')} p/p · "
        f"{row.get('Aerolínea', '')} · "
        f"{row.get('Hora Salida', '')} → {row.get('Hora Llegada', '')} · {row.get('Escalas', '')}"
    )


# ============================================================
# PRICE INSIGHTS
# ============================================================


def mostrar_price_insights(results):
    insights = results.get("price_insights") or {}
    if not insights:
        return

    st.markdown("### 📊 Contexto de precio")
    c1, c2, c3 = st.columns(3)

    lowest = insights.get("lowest_price")
    level = insights.get("price_level")
    typical = insights.get("typical_price_range") or []

    with c1:
        st.metric("Precio más bajo detectado", f"{lowest} €" if lowest is not None else "N/A")
    with c2:
        st.metric("Nivel de precio", PRICE_LEVELS.get(level, level or "N/A"))
    with c3:
        st.metric("Rango habitual", f"{typical[0]}–{typical[1]} €" if len(typical) >= 2 else "N/A")

    history = insights.get("price_history") or []
    if history:
        hist = pd.DataFrame(history, columns=["timestamp", "Precio (€)"])
        hist["Fecha"] = pd.to_datetime(hist["timestamp"], unit="s", errors="coerce")
        hist = hist.dropna(subset=["Fecha"]).set_index("Fecha")[["Precio (€)"]]
        if not hist.empty:
            st.line_chart(hist)

# ============================================================
# BOOKING OPTIONS + EQUIPAJE
# ============================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def consultar_booking(booking_token):
    return serp_search({
        "engine": "google_flights",
        "booking_token": booking_token,
        "currency": CURRENCY,
        "hl": HL,
        "gl": GL,
    })


def booking_options_a_df(results, num_pasajeros=1):
    rows = []
    num_pasajeros = max(1, int(num_pasajeros or 1))

    for option in results.get("booking_options", []) or []:
        separate = bool(option.get("separate_tickets"))
        for section in ("together", "departing", "returning"):
            data = option.get(section)
            if not data:
                continue
            baggage = data.get("baggage_prices") or []
            if isinstance(baggage, str):
                baggage = [baggage]

            precio = pd.to_numeric(data.get("price"), errors="coerce")
            precio_persona = precio / num_pasajeros if pd.notna(precio) else None

            rows.append({
                "Tramo": {
                    "together": "Todo el itinerario",
                    "departing": "Ida",
                    "returning": "Vuelta",
                }[section],
                "Proveedor": data.get("book_with", ""),
                "Precio total": float(precio) if pd.notna(precio) else None,
                "Precio/persona": float(precio_persona) if precio_persona is not None else None,
                "Billetes separados": "Sí" if separate else "No",
                "Equipaje": " · ".join(map(str, baggage)) if baggage else "",
                "Comercializado como": ", ".join(data.get("marketed_as", []) or []),
            })
    return pd.DataFrame(rows)


def mostrar_booking_options(booking_token, key_prefix, num_pasajeros=1):
    if not booking_token:
        st.info("Google no devolvió un `booking_token` para este itinerario.")
        return

    if st.button("🧳 Ver precio final, vendedores y equipaje", key=f"{key_prefix}_booking_btn"):
        try:
            with st.spinner("Consultando opciones de compra..."):
                booking_result = consultar_booking(booking_token)

            top_baggage = booking_result.get("baggage_prices") or {}
            if top_baggage:
                st.markdown("**Política de equipaje detectada**")
                for tramo, valores in top_baggage.items():
                    texto = " · ".join(map(str, valores)) if isinstance(valores, list) else str(valores)
                    st.write(f"- **{tramo.capitalize()}**: {texto}")

            booking_df = booking_options_a_df(booking_result, num_pasajeros=num_pasajeros)
            if booking_df.empty:
                st.warning("No se han devuelto opciones de compra para este vuelo.")
            else:
                st.dataframe(booking_df, hide_index=True, use_container_width=True)
        except Exception as exc:
            st.error(f"No se pudieron recuperar las opciones de compra: {exc}")

# ============================================================
# PARAMETROS DE BUSQUEDA
# ============================================================


def airline_codes(selection):
    return [AIRLINES[name] for name in selection if name in AIRLINES]


def build_flight_params(
    origin,
    destination,
    outbound_date,
    return_date,
    travel_class,
    adults,
    children,
    infants_seat,
    infants_lap,
    bags,
    stops,
    include_airlines,
    exclude_airlines,
    max_price,
    outbound_hours,
    return_hours,
    max_duration_hours,
    layover_enabled,
    layover_range,
    exclude_conns,
    sort_by,
    exhaustive,
):
    is_roundtrip = return_date is not None

    params = {
        "engine": "google_flights",
        "outbound_date": outbound_date.strftime("%Y-%m-%d"),
        "type": "1" if is_roundtrip else "2",
        "travel_class": travel_class,
        "adults": int(adults),
        "children": int(children),
        "infants_in_seat": int(infants_seat),
        "infants_on_lap": int(infants_lap),
        "bags": int(bags),
        "currency": CURRENCY,
        "hl": HL,
        "gl": GL,
        "sort_by": sort_by,
    }

    if origin:
        params["departure_id"] = origin
    if destination:
        params["arrival_id"] = destination

    if is_roundtrip:
        params["return_date"] = return_date.strftime("%Y-%m-%d")

    if stops != "0":
        params["stops"] = stops

    include_codes = airline_codes(include_airlines)
    exclude_codes = airline_codes(exclude_airlines)
    if include_codes:
        params["include_airlines"] = ",".join(include_codes)
    elif exclude_codes:
        params["exclude_airlines"] = ",".join(exclude_codes)

    if max_price and max_price > 0:
        params["max_price"] = int(max_price)

    if outbound_hours != (0, 23):
        params["outbound_times"] = f"{outbound_hours[0]},{outbound_hours[1]}"

    if is_roundtrip and return_hours != (0, 23):
        params["return_times"] = f"{return_hours[0]},{return_hours[1]}"

    if max_duration_hours and max_duration_hours > 0:
        params["max_duration"] = int(max_duration_hours * 60)

    if layover_enabled:
        params["layover_duration"] = f"{int(layover_range[0])},{int(layover_range[1])}"

    if exclude_conns.strip():
        params["exclude_conns"] = ",".join(
            code.strip().upper() for code in exclude_conns.split(",") if code.strip()
        )

    if exhaustive:
        params["show_hidden"] = "true"
        params["deep_search"] = "true"

    return params


def build_oneway_params_from_selected(base_params, selected_row):
    """Construye una búsqueda one-way para valorar por separado un trayecto seleccionado."""
    params = dict(base_params)

    # Los parámetros de round-trip no son válidos en type=2.
    for key in (
        "return_date",
        "return_times",
        "departure_token",
        "booking_token",
        "multi_city_json",
        "selected_flights_json",
    ):
        params.pop(key, None)

    params["type"] = "2"
    params["departure_id"] = selected_row.get("_Origen_IATA", "")
    params["arrival_id"] = selected_row.get("_Destino_IATA", "")
    params["outbound_date"] = str(selected_row.get("Fecha Salida", ""))

    # Para el desglose interesa localizar el mismo vuelo, no volver a aplicar
    # la franja horaria original de la ida a una posible vuelta.
    params.pop("outbound_times", None)
    return params


def obtener_precio_trayecto_separado(base_params, selected_row, num_pasajeros):
    """Busca el precio one-way del mismo itinerario seleccionado.

    Devuelve (precio_total, precio_por_persona, calidad_match).
    Si el mismo vuelo no aparece como one-way, usa el precio mínimo de una
    alternativa comparable para ese aeropuerto/fecha y lo marca como estimación.
    """
    try:
        leg_params = build_oneway_params_from_selected(base_params, selected_row)
        if not leg_params.get("departure_id") or not leg_params.get("arrival_id") or not leg_params.get("outbound_date"):
            return None, None, "no_disponible"

        result = serp_search(leg_params)
        leg_df = vuelos_a_df(result, num_pasajeros=num_pasajeros)
        if leg_df.empty or not leg_df["Precio_Num"].notna().any():
            return None, None, "no_disponible"

        exact = leg_df[
            (leg_df["Vuelo"] == selected_row.get("Vuelo", ""))
            & (leg_df["_Origen_IATA"] == selected_row.get("_Origen_IATA", ""))
            & (leg_df["_Destino_IATA"] == selected_row.get("_Destino_IATA", ""))
            & (leg_df["Fecha Salida"] == selected_row.get("Fecha Salida", ""))
            & (leg_df["Hora Salida"] == selected_row.get("Hora Salida", ""))
        ]

        if not exact.empty and exact["Precio_Num"].notna().any():
            best = exact.sort_values("Precio_Num", na_position="last").iloc[0]
            return float(best["Precio_Num"]), float(best["Precio_Persona_Num"]), "mismo_vuelo"

        # Fallback: precio one-way mínimo para la misma ruta y fecha.
        best = leg_df.sort_values("Precio_Num", na_position="last").iloc[0]
        return float(best["Precio_Num"]), float(best["Precio_Persona_Num"]), "alternativa"

    except Exception:
        return None, None, "no_disponible"


def mostrar_resumen_precios_trayectos(base_params, outbound_row, return_row, num_pasajeros):
    """Muestra ida, vuelta y total desglosado, además del round-trip real de Google."""
    with st.spinner("Calculando el desglose ida / vuelta..."):
        ida_total, ida_pp, ida_match = obtener_precio_trayecto_separado(
            base_params, outbound_row, num_pasajeros
        )
        vuelta_total, vuelta_pp, vuelta_match = obtener_precio_trayecto_separado(
            base_params, return_row, num_pasajeros
        )

    roundtrip_total = pd.to_numeric(return_row.get("Precio_Num"), errors="coerce")
    roundtrip_pp = (
        float(roundtrip_total) / max(1, int(num_pasajeros))
        if pd.notna(roundtrip_total)
        else None
    )

    st.markdown("### 💶 Desglose del precio")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "🛫 Ida",
            f"{ida_total:.0f} €" if ida_total is not None else "N/D",
            help="Precio del trayecto comprado como billete solo ida.",
        )
        if ida_pp is not None:
            st.caption(f"{ida_pp:.0f} € por persona")

    with c2:
        st.metric(
            "🛬 Vuelta",
            f"{vuelta_total:.0f} €" if vuelta_total is not None else "N/D",
            help="Precio del trayecto comprado como billete solo ida en el sentido de vuelta.",
        )
        if vuelta_pp is not None:
            st.caption(f"{vuelta_pp:.0f} € por persona")

    suma_total = None
    suma_pp = None
    if ida_total is not None and vuelta_total is not None:
        suma_total = ida_total + vuelta_total
        suma_pp = suma_total / max(1, int(num_pasajeros))

    with c3:
        st.metric(
            "🧮 Ida + vuelta separadas",
            f"{suma_total:.0f} €" if suma_total is not None else "N/D",
        )
        if suma_pp is not None:
            st.caption(f"{suma_pp:.0f} € por persona")

    with c4:
        st.metric(
            "🎟️ Tarifa ida/vuelta Google",
            f"{float(roundtrip_total):.0f} €" if pd.notna(roundtrip_total) else "N/D",
            help="Precio real de la combinación round-trip seleccionada por Google Flights.",
        )
        if roundtrip_pp is not None:
            st.caption(f"{roundtrip_pp:.0f} € por persona")

    if ida_match == "alternativa" or vuelta_match == "alternativa":
        st.info(
            "Para algún tramo Google no publicó exactamente el mismo vuelo como tarifa one-way. "
            "En ese caso se muestra la alternativa one-way más barata de la misma ruta y fecha."
        )

    if suma_total is not None and pd.notna(roundtrip_total):
        diferencia = float(roundtrip_total) - suma_total
        if abs(diferencia) >= 1:
            if diferencia < 0:
                st.success(
                    f"Comprar la tarifa ida/vuelta conjunta ahorra aproximadamente {abs(diferencia):.0f} € "
                    "frente a comprar ambos trayectos por separado."
                )
            else:
                st.info(
                    f"Comprar ambos trayectos por separado sería aproximadamente {abs(diferencia):.0f} € "
                    "más barato que la tarifa ida/vuelta seleccionada."
                )



# ============================================================
# "CUALQUIER LUGAR": GOOGLE TRAVEL EXPLORE
# ============================================================


def build_anywhere_params(
    origin,
    outbound_date,
    return_date,
    travel_class,
    adults,
    children,
    infants_seat,
    infants_lap,
    bags,
    stops,
    include_airlines,
    exclude_airlines,
    max_price,
    max_duration_hours,
):
    """Construye una búsqueda abierta de destinos con Google Travel Explore.

    Google Flights (`engine=google_flights`) puede exigir `arrival_id` aunque
    aparezca como opcional en parte de la documentación. Para descubrir
    destinos sin `arrival_id`, SerpApi dispone de `google_travel_explore`.
    """
    is_roundtrip = return_date is not None

    params = {
        "engine": "google_travel_explore",
        "departure_id": origin,
        "outbound_date": outbound_date.strftime("%Y-%m-%d"),
        "type": "1" if is_roundtrip else "2",
        "travel_class": travel_class,
        "adults": int(adults),
        "children": int(children),
        "infants_in_seat": int(infants_seat),
        "infants_on_lap": int(infants_lap),
        "bags": int(bags),
        "travel_mode": "1",  # solo vuelos; evita resultados por carretera
        "currency": CURRENCY,
        "hl": HL,
        "gl": GL,
    }

    if is_roundtrip:
        params["return_date"] = return_date.strftime("%Y-%m-%d")

    if stops != "0":
        params["stops"] = stops

    include_codes = airline_codes(include_airlines)
    exclude_codes = airline_codes(exclude_airlines)
    if include_codes:
        params["include_airlines"] = ",".join(include_codes)
    elif exclude_codes:
        params["exclude_airlines"] = ",".join(exclude_codes)

    if max_price and max_price > 0:
        params["max_price"] = int(max_price)

    if max_duration_hours and max_duration_hours > 0:
        params["max_duration"] = int(max_duration_hours * 60)

    return params


def convertir_params_flights_a_explore(params):
    """Migra presets antiguos de 'Cualquier lugar' creados con google_flights."""
    params = dict(params or {})
    allowed = {
        "departure_id", "outbound_date", "return_date", "type", "travel_class",
        "adults", "children", "infants_in_seat", "infants_on_lap", "bags",
        "currency", "hl", "gl", "stops", "include_airlines", "exclude_airlines",
        "max_price", "max_duration",
    }
    converted = {k: v for k, v in params.items() if k in allowed and v not in (None, "")}
    converted["engine"] = "google_travel_explore"
    converted["travel_mode"] = "1"
    converted.pop("arrival_id", None)
    return converted


def detalle_flights_desde_explore(explore_params):
    """Crea una plantilla Google Flights para abrir un destino descubierto."""
    explore_params = dict(explore_params or {})
    allowed = {
        "departure_id", "outbound_date", "return_date", "type", "travel_class",
        "adults", "children", "infants_in_seat", "infants_on_lap", "bags",
        "currency", "hl", "gl", "stops", "include_airlines", "exclude_airlines",
        "max_price", "max_duration",
    }
    params = {k: v for k, v in explore_params.items() if k in allowed and v not in (None, "")}
    params["engine"] = "google_flights"
    params["sort_by"] = "1"
    params["show_hidden"] = "true"
    params["deep_search"] = "true"
    return params

# ============================================================
# FECHAS FLEXIBLES
# ============================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def obtener_calendario_precios(base_params_json, radius_ida, radius_vuelta):
    base_params = json.loads(base_params_json)
    base_out = datetime.datetime.strptime(base_params["outbound_date"], "%Y-%m-%d").date()
    base_return = None
    if base_params.get("return_date"):
        base_return = datetime.datetime.strptime(base_params["return_date"], "%Y-%m-%d").date()

    rows = []
    ida_deltas = range(-int(radius_ida), int(radius_ida) + 1)
    vuelta_deltas = range(-int(radius_vuelta), int(radius_vuelta) + 1) if base_return else [0]

    for d_ida in ida_deltas:
        out_date = base_out + datetime.timedelta(days=d_ida)
        if out_date < datetime.date.today():
            continue

        for d_vuelta in vuelta_deltas:
            ret_date = base_return + datetime.timedelta(days=d_vuelta) if base_return else None
            # Evitar combinaciones donde el viaje de vuelta es anterior al de ida
            if ret_date and ret_date < out_date:
                continue

            params = dict(base_params)
            params["outbound_date"] = out_date.strftime("%Y-%m-%d")
            if ret_date:
                params["return_date"] = ret_date.strftime("%Y-%m-%d")

            try:
                result = serp_search(params)
                items = extraer_items_vuelos(result)
                prices = [item.get("price") for item in items if isinstance(item.get("price"), (int, float))]
                if prices:
                    rows.append({
                        "Fecha ida": out_date.strftime("%d/%m"),
                        "Fecha vuelta": ret_date.strftime("%d/%m") if ret_date else None,
                        "Precio mínimo (€)": min(prices),
                    })
            except Exception:
                continue

    return pd.DataFrame(rows)

# ============================================================
# EXPLORAR / INSPIRAME
# ============================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def consultar_explore(params_json):
    params = json.loads(params_json)
    return serp_search(params)


def explorar_a_df(result):
    rows = []
    for d in result.get("destinations", []) or []:
        airport = d.get("destination_airport", {}) or {}
        rows.append({
            "Destino": d.get("name", ""),
            "País": d.get("country", ""),
            "Aeropuerto": airport.get("code", ""),
            "Ida": d.get("start_date", ""),
            "Vuelta": d.get("end_date", ""),
            "Vuelo (€)": d.get("flight_price"),
            "Hotel/noche": d.get("hotel_price"),
            "Duración": fmt_minutes(d.get("flight_duration")),
            "Escalas": d.get("number_of_stops"),
            "Aerolínea": d.get("airline", ""),
            "_lat": (d.get("gps_coordinates") or {}).get("latitude"),
            "_lon": (d.get("gps_coordinates") or {}).get("longitude"),
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["Vuelo (€)"] = pd.to_numeric(df["Vuelo (€)"], errors="coerce")
    return df.sort_values("Vuelo (€)", na_position="last").reset_index(drop=True)



def _precio_numerico(value):
    """Convierte precios numéricos o textos como '123 €' / '€123' a float."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return float(value)
        except Exception:
            return None
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        # Conserva dígitos y separadores habituales. La API normalmente devuelve
        # números, pero este fallback evita N/A si cambia el formato/localización.
        cleaned = "".join(ch for ch in raw if ch.isdigit() or ch in ",.-")
        if not cleaned:
            return None
        # 1.234,56 -> 1234.56 | 1,234.56 -> 1234.56 | 123,45 -> 123.45
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            parts = cleaned.split(",")
            if len(parts[-1]) in (1, 2):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except Exception:
            return None
    return None


def _extraer_precio_destino(d):
    """Obtiene el mejor precio disponible del registro Explore sin hacer otra API call."""
    candidatos = [
        d.get("flight_price"),
        d.get("price"),
        (d.get("flight") or {}).get("price") if isinstance(d.get("flight"), dict) else None,
        (d.get("cheapest_flight") or {}).get("price") if isinstance(d.get("cheapest_flight"), dict) else None,
    ]
    for candidato in candidatos:
        precio = _precio_numerico(candidato)
        if precio is not None:
            return precio

    # Fallback por si SerpApi incluyera vuelos anidados dentro del destino.
    flights = d.get("flights") or []
    precios = []
    if isinstance(flights, list):
        for flight in flights:
            if isinstance(flight, dict):
                p = _precio_numerico(flight.get("price"))
                if p is not None:
                    precios.append(p)
    return min(precios) if precios else None


def destinos_anywhere_a_df(result, num_pasajeros=1):
    """Normaliza todos los destinos devueltos por Google Travel Explore.

    IMPORTANTE: esta función NO lanza nuevas consultas. Una única respuesta
    Explore puede contener muchas alternativas de destino y su `flight_price`.
    """
    rows = []
    num_pasajeros = max(1, int(num_pasajeros or 1))

    for item_idx, d in enumerate(result.get("destinations", []) or []):
        airport = d.get("destination_airport", {}) or {}
        price = _extraer_precio_destino(d)
        destination_id = d.get("destination_id") or airport.get("location_id") or airport.get("code") or ""
        airport_code = airport.get("code", "")

        rows.append({
            "_row_id": item_idx,
            "Destino": d.get("name", ""),
            "País": d.get("country", ""),
            "Aeropuerto": airport_code,
            "Fecha Ida": d.get("start_date", ""),
            "Fecha Vuelta": d.get("end_date", ""),
            "Precio_Num": price,
            "Precio": f"{price:.0f} €" if price is not None else "N/A",
            "Precio/persona": f"{price / num_pasajeros:.2f} €" if price is not None else "N/A",
            "Duración": fmt_minutes(d.get("flight_duration")),
            "Escalas": (
                "Directo" if d.get("number_of_stops") == 0
                else f"{d.get('number_of_stops')} escala(s)" if d.get("number_of_stops") is not None
                else "N/A"
            ),
            "Aerolínea": d.get("airline", ""),
            "Ver en Google": d.get("link", ""),
            "_arrival_id": destination_id,
            "_arrival_airport": airport_code,
            "_serpapi_link": d.get("serpapi_link", ""),
            "_lat": (d.get("gps_coordinates") or {}).get("latitude"),
            "_lon": (d.get("gps_coordinates") or {}).get("longitude"),
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["Precio_Num"] = pd.to_numeric(df["Precio_Num"], errors="coerce")
    return df.sort_values(["Precio_Num", "Destino"], na_position="last").reset_index(drop=True)


def anywhere_destination_label(row):
    aeropuerto = f" ({row.get('Aeropuerto')})" if row.get("Aeropuerto") else ""
    return (
        f"{row.get('Destino', '')}{aeropuerto} · "
        f"{row.get('Precio', 'N/A')} total · {row.get('Precio/persona', 'N/A')} por persona"
    )

# ============================================================
# MODO Y CONSUMO API
# ============================================================

st.sidebar.markdown(
    "<h2>✈️ Menú Principal</h2>",
    unsafe_allow_html=True
)
modo = st.sidebar.radio("Modo", ["🔎 Buscar vuelos", "🌍 Inspírame"], index=0)


def mostrar_consumo_api(coste_estimado):
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Consumo de SerpApi")
    st.sidebar.info(
        f"⚡ **Peticiones máximas previstas al pulsar Buscar:** {coste_estimado}\n\n"
        "Las consultas idénticas pueden resolverse desde caché."
    )
    try:
        api_key = st.secrets["SERPAPI_API_KEY"]
        total_creditos, creditos_restantes = obtener_info_cuenta(api_key)
        if total_creditos is not None:
            st.sidebar.metric("Créditos Restantes (Mensuales)", f"{creditos_restantes} / {total_creditos}")
            if isinstance(total_creditos, int) and isinstance(creditos_restantes, int):
                pct = max(0.0, min(1.0, creditos_restantes / total_creditos))
                st.sidebar.progress(pct)
    except Exception:
        st.sidebar.warning("Configura `SERPAPI_API_KEY` en los secretos.")

# ============================================================
# MODO 1: BUSCAR VUELOS
# ============================================================

if modo == "🔎 Buscar vuelos":
    hoy = datetime.date.today()
    def_origen = st.query_params.get("origen", "MAD")
    def_destino = st.query_params.get("destino", "BER")
    def_destino_anywhere = def_destino == ANYWHERE_STORAGE_KEY
    if def_destino_anywhere:
        def_destino = ""

    try:
        def_ida = datetime.datetime.strptime(st.query_params.get("ida", ""), "%Y-%m-%d").date()
        if def_ida < hoy:
            def_ida = hoy
    except Exception:
        def_ida = hoy

    q_vuelta = st.query_params.get("vuelta", "")
    def_buscar_vuelta = bool(q_vuelta)
    try:
        def_vuelta = datetime.datetime.strptime(q_vuelta, "%Y-%m-%d").date()
        if def_vuelta < def_ida:
            def_vuelta = def_ida
    except Exception:
        def_vuelta = def_ida

    st.sidebar.header("Configuración de Búsqueda")

    # Selección múltiple, como en Google Flights: se pueden combinar varias
    # ciudades/aeropuertos de salida y varias de llegada en una sola búsqueda.
    origen_seleccion = selector_aeropuertos(
        "Origen (una o varias ciudades/aeropuertos)",
        def_origen,
        "origen",
    )
    destino_seleccion = selector_aeropuertos(
        "Destino (una o varias ciudades/aeropuertos)",
        def_destino,
        "destino",
        permitir_cualquier_lugar=True,
        cualquier_lugar_por_defecto=def_destino_anywhere,
    )

    origenes_iata = extraer_iatas(origen_seleccion)
    destinos_iata = extraer_iatas(destino_seleccion)
    destino_anywhere = seleccion_cualquier_lugar(destino_seleccion)
    # Si se marca Cualquier lugar, prevalece sobre cualquier destino concreto
    # que pudiera seguir seleccionado visualmente en el multiselect.
    if destino_anywhere:
        destinos_iata = []
    origen = ",".join(origenes_iata)
    # Para Fly to anywhere NO se envía arrival_id. serp_search elimina valores vacíos.
    destino = "" if destino_anywhere else ",".join(destinos_iata)

    if destino_anywhere:
        st.sidebar.caption(
            "🌍 Cualquier lugar: la primera consulta usa Google Travel Explore para descubrir destinos. "
            "Después podrás abrir uno y consultar sus vuelos concretos en Google Flights."
        )
    else:
        st.sidebar.caption(
            "Puedes añadir varios aeropuertos. La consulta se envía a Google Flights "
            "como una única búsqueda combinada."
        )
    fecha_ida = st.sidebar.date_input("Fecha de Ida", min_value=hoy, value=def_ida)
    buscar_vuelta = st.sidebar.checkbox(
        "Ida y vuelta",
        value=def_buscar_vuelta,
        help="Usa una búsqueda round-trip real; no suma dos billetes one-way.",
    )

    fecha_vuelta = None
    if buscar_vuelta:
        fecha_vuelta = st.sidebar.date_input(
            "Fecha de Vuelta",
            min_value=fecha_ida,
            value=max(def_vuelta, fecha_ida),
        )

    st.sidebar.markdown("---")
    st.sidebar.subheader("👥 Pasajeros y cabina")
    # (Se han eliminado los bebés con asiento/en regazo a petición del usuario.)
    # Fila 1: adultos y niños.
    col_ad, col_ni = st.sidebar.columns(2)
    adultos = col_ad.number_input("Adultos", min_value=1, max_value=9, value=1)
    ninos = col_ni.number_input("Niños", min_value=0, max_value=8, value=0)
    bebes_asiento = 0
    bebes_regazo = 0

    # Fila 2: clase y equipaje de mano.
    col_clase, col_equip = st.sidebar.columns(2)
    clase_sel = col_clase.selectbox("Clase de Cabina", list(CABIN_CLASSES.keys()), index=0)
    viajeros_con_equipaje = int(adultos + ninos)
    equipajes_mano = col_equip.number_input(
        "Equipaje mano",
        min_value=0,
        max_value=max(0, viajeros_con_equipaje),
        value=0,
        help="Filtro de carry-on. El equipaje facturado se consulta en las opciones de compra.",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎛️ Filtros avanzados")
    # Fila 1: escalas, orden y precio máximo.
    col_esc, col_ord, col_precio = st.sidebar.columns(3)
    escalas_sel = col_esc.selectbox("Escalas", list(STOPS_OPTIONS.keys()), index=0)
    ordenar_sel = col_ord.selectbox("Ordenar por", list(SORT_OPTIONS.keys()), index=0)
    precio_max = col_precio.number_input("Precio máx. (€)", min_value=0, max_value=10000, value=0, step=10, help="0 = sin límite.")

    # Fila 2: horas de salida (ida y, si aplica, vuelta) lado a lado.
    if buscar_vuelta:
        col_hida, col_hvuelta = st.sidebar.columns(2)
        horas_ida = col_hida.slider("Salida ida (h)", 0, 23, (0, 23))
        horas_vuelta = col_hvuelta.slider("Salida vuelta (h)", 0, 23, (0, 23))
    else:
        horas_ida = st.sidebar.slider("Hora de salida (h)", 0, 23, (0, 23))
        horas_vuelta = (0, 23)

    # El resto de filtros avanzados (menos usados) van en un desplegable
    # aparte para que las 2 filas de arriba no crezcan más.
    with st.sidebar.expander("Más filtros: escalas, conexiones y aerolíneas"):
        duracion_max = st.number_input("Duración máxima del trayecto (h)", min_value=0, max_value=48, value=0, help="0 = sin límite.")
        usar_escala = st.checkbox("Limitar duración de las escalas", value=False)
        rango_escala = (30, 360)
        if usar_escala:
            rango_escala = st.slider("Duración de escala (min)", min_value=30, max_value=720, value=(60, 300), step=15)

        excluir_conexiones = st.text_input("Excluir aeropuertos de conexión", placeholder="Ej.: LHR,CDG")
        incluir_aerolineas = st.multiselect("Incluir solo aerolíneas", options=sorted(AIRLINES.keys()))
        excluir_aerolineas = st.multiselect("Excluir aerolíneas", options=sorted(AIRLINES.keys()))
        if incluir_aerolineas and excluir_aerolineas:
            st.error("No puedes incluir y excluir aerolíneas simultáneamente.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🌍 Cercanos y cobertura")
    # Fila 1: aeropuertos cercanos (origen/destino).
    col_cerc_o, col_cerc_d = st.sidebar.columns(2)
    buscar_cercanos_origen = col_cerc_o.checkbox("Cercanos salida", value=False)
    buscar_cercanos_destino = col_cerc_d.checkbox(
        "Cercanos llegada",
        value=False,
        disabled=destino_anywhere,
        help="No aplica cuando el destino es Cualquier lugar." if destino_anywhere else None,
    )
    if destino_anywhere:
        buscar_cercanos_destino = False
    radio_km_origen = st.sidebar.slider("Radio de salida (km)", min_value=50, max_value=600, value=100, step=10) if buscar_cercanos_origen else 0
    radio_km_destino = st.sidebar.slider("Radio de llegada (km)", min_value=50, max_value=600, value=100, step=10) if buscar_cercanos_destino else 0

    # Fila 2: búsqueda exhaustiva y fechas flexibles de ida.
    col_exh, col_flex_i = st.sidebar.columns(2)
    busqueda_exhaustiva = col_exh.checkbox(
        "Exhaustiva",
        value=True,
        help="Activa show_hidden + deep_search para aproximarse a los resultados del navegador.",
    )
    flex_ida = col_flex_i.checkbox(
        "Flex. ida",
        value=False,
        disabled=destino_anywhere,
        help="Para 'Cualquier lugar' se usan las fechas elegidas directamente en Google Travel Explore." if destino_anywhere else None,
    )
    if destino_anywhere:
        flex_ida = False

    # Fechas flexibles de vuelta: casilla SIEMPRE visible (no desaparece),
    # simplemente se deshabilita si no hay "Ida y vuelta" activado.
    flex_vuelta = st.sidebar.checkbox(
        "Fechas flexibles de vuelta",
        value=False,
        disabled=(not buscar_vuelta) or destino_anywhere,
        help=(
            "Para 'Cualquier lugar' se usan las fechas elegidas directamente en Google Travel Explore."
            if destino_anywhere
            else (None if buscar_vuelta else "Actívala marcando antes 'Ida y vuelta'.")
        ),
    )
    if (not buscar_vuelta) or destino_anywhere:
        flex_vuelta = False

    radio_ida = st.sidebar.slider("Días de margen (ida)", min_value=1, max_value=5, value=3) if flex_ida else 0
    radio_vuelta = st.sidebar.slider("Días de margen (vuelta)", min_value=1, max_value=5, value=3) if (buscar_vuelta and flex_vuelta) else 0

    # Cálculo multiplicativo de la matriz de llamadas
    consultas_ida = (1 + 2 * radio_ida) if flex_ida else 1
    consultas_vuelta = (1 + 2 * radio_vuelta) if flex_vuelta else 1
    coste_estimado = consultas_ida * consultas_vuelta

    if coste_estimado > 10:
        st.sidebar.warning(f"⚠️ La flexibilidad cruzada lanzará {coste_estimado} peticiones simultáneas a la API.")

    # --------------------------------------------------------
    # BÚSQUEDAS GUARDADAS
    # --------------------------------------------------------
    st.sidebar.markdown("---")
    with st.sidebar.expander("⭐ Búsquedas guardadas", expanded=False):
        saved_df = cargar_busquedas()
        if saved_df.empty:
            st.caption("Todavía no hay configuraciones guardadas.")
        else:
            saved_ids = saved_df["id"].astype(int).tolist()
            saved_id = st.selectbox(
                "Configuración",
                options=saved_ids,
                format_func=lambda sid: saved_df.loc[saved_df["id"] == sid, "name"].iloc[0],
                key="saved_search_select",
            )
            saved_row = saved_df.loc[saved_df["id"] == saved_id].iloc[0]
            try:
                saved_config = json.loads(saved_row["config"])
                st.caption(resumen_config_guardada(saved_config))
                if saved_row.get("created_at"):
                    st.caption(f"Guardada: {str(saved_row['created_at']).replace('T', ' ')[:19]}")

                saved_q_ida = 1 + 2 * int(saved_config.get("radius_ida", 0)) if saved_config.get("flexible_ida") else 1
                saved_q_vuelta = 1 + 2 * int(saved_config.get("radius_vuelta", 0)) if saved_config.get("flexible_vuelta") else 1
                saved_cost = saved_q_ida * saved_q_vuelta
                if saved_cost > 1:
                    st.warning(f"Esta configuración flexible puede comprobar hasta {saved_cost} cruces de fechas.")

                st.download_button(
                    "⬇️ Exportar copia del preset",
                    data=json.dumps(saved_config, ensure_ascii=False, indent=2),
                    file_name=f"busqueda_{saved_id}.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"export_saved_{saved_id}",
                )

                c_run, c_del = st.columns(2)
                repetir_guardada = c_run.button(
                    "▶️ Repetir",
                    use_container_width=True,
                    key=f"run_saved_{saved_id}",
                )
                borrar_guardada = c_del.button(
                    "🗑️ Eliminar",
                    use_container_width=True,
                    key=f"delete_saved_{saved_id}",
                )

                if borrar_guardada:
                    if eliminar_busqueda(saved_id):
                        st.success("Búsqueda eliminada.")
                        st.rerun()
                    else:
                        st.error("No se pudo eliminar la búsqueda.")

                if repetir_guardada:
                    try:
                        with st.spinner("Repitiendo búsqueda guardada..."):
                            ejecutar_busqueda_guardada(saved_config)
                        st.success("Búsqueda actualizada con precios actuales.")
                    except Exception as exc:
                        st.error(f"No se pudo repetir la búsqueda: {exc}")
            except Exception:
                st.error("La configuración guardada no se puede leer.")

        st.markdown("---")
        preset_file = st.file_uploader(
            "Importar preset (.json)",
            type=["json"],
            key="import_saved_search_file",
        )
        if preset_file is not None:
            try:
                imported_config = json.loads(preset_file.getvalue().decode("utf-8"))
                st.caption(resumen_config_guardada(imported_config))
                imported_name = st.text_input(
                    "Nombre para el preset importado",
                    value=Path(preset_file.name).stem,
                    key="import_saved_search_name",
                )
                if st.button("📥 Importar", use_container_width=True, key="import_saved_search_btn"):
                    if guardar_busqueda(imported_name, imported_config):
                        st.success("Preset importado.")
                        st.rerun()
                    else:
                        st.error("No se pudo importar el preset.")
            except Exception:
                st.error("El archivo no contiene una configuración válida.")

    mostrar_consumo_api(coste_estimado)

    # ---> ESTE ES EL BOTÓN QUE FALTA <---
    buscar_btn = st.sidebar.button(
        "Buscar vuelos",
        type="primary",
        use_container_width=True,
        disabled=bool(incluir_aerolineas and excluir_aerolineas),
    )

    if buscar_btn:
        if not origenes_iata:
            st.error("Indica al menos un origen. 'Cualquier lugar' se aplica al destino, no al aeropuerto de salida.")
        elif (not destino_anywhere) and (not destinos_iata):
            st.error("Indica al menos un destino o selecciona 'Cualquier lugar'.")
        elif (not destino_anywhere) and len(origenes_iata) == 1 and len(destinos_iata) == 1 and origenes_iata[0] == destinos_iata[0]:
            st.error("Origen y destino no pueden ser iguales.")
        else:
            st.query_params["origen"] = origen
            st.query_params["destino"] = ANYWHERE_STORAGE_KEY if destino_anywhere else destino
            st.query_params["ida"] = fecha_ida.strftime("%Y-%m-%d")
            if buscar_vuelta:
                st.query_params["vuelta"] = fecha_vuelta.strftime("%Y-%m-%d")
            elif "vuelta" in st.query_params:
                del st.query_params["vuelta"]

            orig_query = (
                expandir_aeropuertos_cercanos(origenes_iata, radio_km_origen)
                if buscar_cercanos_origen
                else origen
            )
            dest_query = (
                ""
                if destino_anywhere
                else (
                    expandir_aeropuertos_cercanos(destinos_iata, radio_km_destino)
                    if buscar_cercanos_destino
                    else destino
                )
            )

            # Plantilla de Google Flights para abrir después un destino concreto.
            # Conserva todos los filtros que Google Travel Explore no admite
            # (horas, duración de escala, conexiones excluidas, orden, deep_search...).
            detail_params = build_flight_params(
                origin=orig_query,
                destination=dest_query,
                outbound_date=fecha_ida,
                return_date=fecha_vuelta if buscar_vuelta else None,
                travel_class=CABIN_CLASSES[clase_sel],
                adults=adultos,
                children=ninos,
                infants_seat=bebes_asiento,
                infants_lap=bebes_regazo,
                bags=equipajes_mano,
                stops=STOPS_OPTIONS[escalas_sel],
                include_airlines=incluir_aerolineas,
                exclude_airlines=excluir_aerolineas,
                max_price=precio_max,
                outbound_hours=horas_ida,
                return_hours=horas_vuelta,
                max_duration_hours=duracion_max,
                layover_enabled=usar_escala,
                layover_range=rango_escala,
                exclude_conns=excluir_conexiones,
                sort_by=SORT_OPTIONS[ordenar_sel],
                exhaustive=busqueda_exhaustiva,
            )

            if destino_anywhere:
                params = build_anywhere_params(
                    origin=orig_query,
                    outbound_date=fecha_ida,
                    return_date=fecha_vuelta if buscar_vuelta else None,
                    travel_class=CABIN_CLASSES[clase_sel],
                    adults=adultos,
                    children=ninos,
                    infants_seat=bebes_asiento,
                    infants_lap=bebes_regazo,
                    bags=equipajes_mano,
                    stops=STOPS_OPTIONS[escalas_sel],
                    include_airlines=incluir_aerolineas,
                    exclude_airlines=excluir_aerolineas,
                    max_price=precio_max,
                    max_duration_hours=duracion_max,
                )
            else:
                params = detail_params

            try:
                with st.status("Buscando destinos..." if destino_anywhere else "Buscando tarifas...", expanded=True) as status:
                    result = serp_search(params)
                    if destino_anywhere:
                        df = destinos_anywhere_a_df(result, num_pasajeros=int(adultos + ninos))
                    else:
                        df = vuelos_a_df(result, num_pasajeros=int(adultos + ninos))
                    status.update(label="¡Búsqueda completada!", state="complete", expanded=False)

                st.session_state["flight_search"] = {
                    "params": params,
                    "detail_params": detail_params,
                    "result": result,
                    "df": df,
                    "origin": origen,
                    "destination": ANYWHERE_STORAGE_KEY if destino_anywhere else destino,
                    "destination_anywhere": destino_anywhere,
                    "outbound_date": fecha_ida,
                    "return_date": fecha_vuelta if buscar_vuelta else None,
                    "travel_class": CABIN_CLASSES[clase_sel],
                    "adults": adultos,
                    "children": ninos,
                    "passengers": int(adultos + ninos),
                    "origin_ids": origenes_iata,
                    "destination_ids": destinos_iata,
                    "flexible_ida": flex_ida,
                    "radius_ida": radio_ida,
                    "flexible_vuelta": flex_vuelta,
                    "radius_vuelta": radio_vuelta,
                }
                st.session_state.pop("return_search", None)
                st.session_state.pop("anywhere_detail", None)

                if not df.empty and "Precio_Num" in df.columns and df["Precio_Num"].notna().any():
                    guardar_precio(
                        origen,
                        ANYWHERE_STORAGE_KEY if destino_anywhere else destino,
                        fecha_ida,
                        fecha_vuelta if buscar_vuelta else None,
                        CABIN_CLASSES[clase_sel],
                        adultos,
                        df["Precio_Num"].min(),
                    )
            except Exception as exc:
                st.error(f"Error consultando SerpApi: {exc}")
                st.session_state.pop("flight_search", None)

    search_state = st.session_state.get("flight_search")
    if search_state:
        if search_state.get("destination_anywhere"):
            df = search_state["df"]
            result = search_state["result"]
            is_roundtrip = search_state["return_date"] is not None
            pasajeros = max(1, int(search_state.get("passengers", 1)))

            st.markdown("---")
            st.subheader("🌍 Destinos para ‘Cualquier lugar’")
            st.caption(
                "Una única consulta a Google Travel Explore devuelve múltiples destinos y, cuando Google los publica, "
                "su mejor tarifa orientativa. La app muestra todas esas alternativas directamente y no abre una "
                "consulta adicional por cada ciudad."
            )

            if df.empty:
                st.warning("Google Travel Explore no devolvió destinos con estos filtros y fechas.")
            else:
                if df["Precio_Num"].notna().any():
                    min_price = float(df["Precio_Num"].min())
                    min_pp = min_price / pasajeros
                    c1, c2 = st.columns(2)
                    c1.metric("💰 Mejor precio agregado encontrado", f"{min_price:.0f} €")
                    c2.metric("👤 Mejor precio por persona", f"{min_pp:.0f} €")

                    triggered = alertas_activadas(
                        search_state["origin"],
                        search_state["destination"],
                        search_state["outbound_date"],
                        search_state["return_date"],
                        min_price,
                    )
                    if not triggered.empty:
                        thresholds = ", ".join(f"{int(x)} €" for x in triggered["max_price"])
                        st.success(
                            f"🔔 Alerta alcanzada para ‘Cualquier lugar’. "
                            f"Mejor precio actual: {int(min_price)} €. Umbrales: {thresholds}."
                        )

                # ------------------------------------------------------------
                # UNA SOLA CONSULTA: mostrar TODAS las alternativas devueltas
                # por Google Travel Explore. No preguntamos qué destino abrir
                # y no consumimos créditos adicionales automáticamente.
                # ------------------------------------------------------------
                priced_df = df[df["Precio_Num"].notna()].copy()
                unpriced_df = df[df["Precio_Num"].isna()].copy()

                st.markdown("### 💶 Todas las alternativas con tarifa")
                st.caption(
                    "La tabla usa exclusivamente la respuesta de la consulta de ‘Cualquier lugar’. "
                    "No se está haciendo una llamada adicional a SerpApi por cada ciudad."
                )

                if priced_df.empty:
                    st.warning(
                        "SerpApi ha devuelto destinos, pero ninguno incluye `flight_price` para los filtros actuales. "
                        "No se ha gastado ningún crédito adicional. Prueba a aumentar o quitar el precio máximo, "
                        "o a relajar otros filtros."
                    )
                else:
                    alternativas_cols = [
                        "Destino", "País", "Aeropuerto", "Fecha Ida", "Fecha Vuelta",
                        "Precio", "Precio/persona", "Duración", "Escalas", "Aerolínea", "Ver en Google",
                    ]
                    alternativas_cols = [c for c in alternativas_cols if c in priced_df.columns]
                    st.dataframe(
                        priced_df[alternativas_cols],
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "Ver en Google": st.column_config.LinkColumn(
                                "Google",
                                display_text="Abrir ↗",
                                help="Abre el resultado de Google Travel sin consumir otra consulta de SerpApi.",
                            )
                        } if "Ver en Google" in alternativas_cols else None,
                    )
                    st.success(
                        f"Se muestran {len(priced_df)} alternativas con precio usando la misma consulta de SerpApi."
                    )

                if not unpriced_df.empty:
                    with st.expander(f"Destinos devueltos sin tarifa disponible ({len(unpriced_df)})"):
                        st.caption(
                            "Google Travel Explore puede devolver tarjetas de destino sin `flight_price`. "
                            "Se mantienen separadas para no mezclar destinos sin tarifa con las alternativas comparables."
                        )
                        no_price_cols = [
                            "Destino", "País", "Aeropuerto", "Fecha Ida", "Fecha Vuelta",
                            "Duración", "Escalas", "Aerolínea", "Ver en Google",
                        ]
                        no_price_cols = [c for c in no_price_cols if c in unpriced_df.columns]
                        st.dataframe(
                            unpriced_df[no_price_cols],
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "Ver en Google": st.column_config.LinkColumn("Google", display_text="Abrir ↗")
                            } if "Ver en Google" in no_price_cols else None,
                        )

                # Diagnóstico gratuito: usa el JSON que YA hemos recibido.
                with st.expander("🧪 Diagnóstico de la respuesta de SerpApi", expanded=False):
                    st.write(
                        {
                            "destinos_totales": int(len(df)),
                            "destinos_con_precio": int(df["Precio_Num"].notna().sum()),
                            "destinos_sin_precio": int(df["Precio_Num"].isna().sum()),
                            "search_id": (result.get("search_metadata") or {}).get("id"),
                            "search_status": (result.get("search_metadata") or {}).get("status"),
                            "search_parameters": result.get("search_parameters", {}),
                        }
                    )
                    destinos_raw = result.get("destinations", []) or []
                    if destinos_raw:
                        st.caption("Primer destino tal como lo devolvió SerpApi (no genera una nueva consulta):")
                        st.json(destinos_raw[0])

            st.markdown("### 📈 Histórico local")
            hist = obtener_historico(
                search_state["origin"],
                search_state["destination"],
                search_state["outbound_date"],
                search_state["return_date"],
            )
            if hist.empty:
                st.caption("Aún no hay histórico suficiente para esta búsqueda abierta.")
            else:
                st.caption("El histórico representa el destino más barato encontrado en cada ejecución de ‘Cualquier lugar’.")
                st.line_chart(hist.set_index("timestamp")[["price"]])

            with st.expander("⭐ Guardar esta configuración de búsqueda"):
                st.caption(
                    "Guarda la configuración de ‘Cualquier lugar’. Al repetirla se volverán a descubrir "
                    "los destinos y precios disponibles para esas fechas."
                )
                default_name = f"{search_state.get('origin', '')} → Cualquier lugar"
                nombre_guardado = st.text_input(
                    "Nombre",
                    value=default_name,
                    key="saved_search_name_anywhere",
                )
                if st.button("💾 Guardar configuración", key="save_current_search_config_anywhere"):
                    config_guardable = construir_config_guardable(search_state)
                    if guardar_busqueda(nombre_guardado, config_guardable):
                        st.success("Configuración guardada.")
                    else:
                        st.error("No se pudo guardar la configuración.")

            with st.expander("🔔 Crear alerta de precio"):
                st.caption("La alerta se compara con el destino más barato encontrado en la búsqueda abierta.")
                default_alert = 50
                if not df.empty and df["Precio_Num"].notna().any():
                    default_alert = max(1, int(df["Precio_Num"].min() * 0.9))
                umbral = st.number_input(
                    "Avísame si aparece algún destino por debajo de (€)",
                    min_value=1,
                    max_value=10000,
                    value=default_alert,
                    key="alert_threshold_anywhere",
                )
                if st.button("Guardar alerta", key="save_alert_anywhere"):
                    ok = crear_alerta(
                        search_state["origin"],
                        search_state["destination"],
                        search_state["outbound_date"],
                        search_state["return_date"],
                        umbral,
                    )
                    if ok:
                        st.success("Alerta guardada.")
                    else:
                        st.error("No se pudo guardar la alerta.")

        else:
            df = search_state["df"]
            result = search_state["result"]
            params = search_state["params"]
            is_roundtrip = search_state["return_date"] is not None

            st.markdown("---")
            if is_roundtrip:
                st.subheader("🛫 Selecciona la ida")
                st.caption(
                    "Búsqueda round-trip real. Tras seleccionar la ida se consultan las vueltas compatibles mediante departure_token."
                )
            else:
                st.subheader("🛫 Resultados")

            mostrar_df_vuelos(df)

            if not df.empty and df["Precio_Num"].notna().any():
                min_price = df["Precio_Num"].min()
                min_pp = min_price / max(1, int(search_state.get("passengers", 1)))
                c_precio_total, c_precio_pp = st.columns(2)
                c_precio_total.metric("💰 Mejor precio agregado", f"{int(round(min_price))} €")
                c_precio_pp.metric("👤 Mejor precio por persona", f"{int(round(min_pp))} €")

                triggered = alertas_activadas(
                    search_state["origin"],
                    search_state["destination"],
                    search_state["outbound_date"],
                    search_state["return_date"],
                    min_price,
                )
                if not triggered.empty:
                    thresholds = ", ".join(f"{int(x)} €" for x in triggered["max_price"])
                    st.success(f"🔔 Alerta alcanzada. Precio actual: {int(min_price)} €. Umbrales: {thresholds}.")

            mostrar_price_insights(result)

            if search_state.get("flexible_ida") or search_state.get("flexible_vuelta"):
                st.markdown("### 📅 Fechas flexibles (Matriz de precios)")
                st.caption("Compara cruces de fechas para encontrar la combinación más barata.")
                try:
                    base_params_json = json.dumps(params, sort_keys=True, separators=(",", ":"))
                    with st.spinner(f"Construyendo matriz (hasta {coste_estimado} comprobaciones)..."):
                        cal_df = obtener_calendario_precios(
                            base_params_json,
                            search_state["radius_ida"],
                            search_state["radius_vuelta"]
                        )
                    if cal_df.empty:
                        st.info("No se han podido obtener precios para fechas cercanas.")
                    else:
                        # Si ambos están activos, dibuja una matriz (pivot table)
                        if search_state["radius_ida"] > 0 and search_state["radius_vuelta"] > 0 and search_state["return_date"]:
                            matriz = cal_df.pivot(index="Fecha ida", columns="Fecha vuelta", values="Precio mínimo (€)")
                            st.dataframe(matriz, use_container_width=True)
                        # Si solo uno es flexible, dibuja la gráfica lineal
                        else:
                            st.dataframe(cal_df, hide_index=True, use_container_width=True)
                            eje_x = "Fecha ida" if search_state["radius_ida"] > 0 else "Fecha vuelta"
                            st.line_chart(cal_df.set_index(eje_x)[["Precio mínimo (€)"]])
                except Exception as exc:
                    st.warning(f"No se pudo construir la matriz de precios: {exc}")

            st.markdown("### 📈 Histórico local")
            hist = obtener_historico(
                search_state["origin"],
                search_state["destination"],
                search_state["outbound_date"],
                search_state["return_date"],
            )
            if hist.empty:
                st.caption("Aún no hay histórico suficiente para esta búsqueda.")
            else:
                st.line_chart(hist.set_index("timestamp")[["price"]])

            with st.expander("⭐ Guardar esta configuración de búsqueda"):
                st.caption(
                    "Guarda los parámetros, no los resultados. Al repetirla se vuelve a consultar SerpApi "
                    "y el nuevo precio se añade al histórico local."
                )
                default_name_dest = "Cualquier lugar" if search_state.get("destination_anywhere") else search_state.get("destination", "")
                default_name = f"{search_state.get('origin', '')} → {default_name_dest}"
                nombre_guardado = st.text_input(
                    "Nombre",
                    value=default_name,
                    key="saved_search_name",
                )
                if st.button("💾 Guardar configuración", key="save_current_search_config"):
                    config_guardable = construir_config_guardable(search_state)
                    if guardar_busqueda(nombre_guardado, config_guardable):
                        st.success("Configuración guardada. Ya aparecerá en 'Búsquedas guardadas' del menú lateral.")
                    else:
                        st.error("No se pudo guardar la configuración. Comprueba el nombre y el almacenamiento local.")

            with st.expander("🔔 Crear alerta de precio"):
                st.caption(
                    "La alerta se guarda localmente y se comprueba al ejecutar la app/búsqueda. Para email o push en segundo plano hace falta un job externo."
                )
                default_alert = 50
                if not df.empty and df["Precio_Num"].notna().any():
                    default_alert = max(1, int(df["Precio_Num"].min() * 0.9))
                umbral = st.number_input("Avísame si el precio baja a (€)", min_value=1, max_value=10000, value=default_alert, key="alert_threshold")
                if st.button("Guardar alerta", key="save_alert"):
                    ok = crear_alerta(
                        search_state["origin"],
                        search_state["destination"],
                        search_state["outbound_date"],
                        search_state["return_date"],
                        umbral,
                    )
                    if ok:
                        st.success("Alerta guardada.")
                    else:
                        st.error("No se pudo guardar la alerta.")

            if not is_roundtrip and not df.empty:
                st.markdown("### 🧳 Precio final y equipaje")
                selectable = [idx for idx in df.index if pd.notna(df.loc[idx, "Precio_Num"])]
                if selectable:
                    selected_idx = st.selectbox(
                        "Selecciona un vuelo",
                        options=selectable,
                        format_func=lambda i: flight_label(df.loc[i]),
                        key="oneway_booking_select",
                    )
                    mostrar_booking_options(
                        df.loc[selected_idx, "_booking_token"],
                        key_prefix=f"oneway_{selected_idx}",
                        num_pasajeros=search_state.get("passengers", 1),
                    )

            if is_roundtrip and not df.empty:
                valid_outbound = [idx for idx in df.index if df.loc[idx, "_departure_token"]]
                if not valid_outbound:
                    st.warning("Google no devolvió `departure_token` para las idas encontradas.")
                else:
                    selected_outbound_idx = st.selectbox(
                        "Ida seleccionada",
                        options=valid_outbound,
                        format_func=lambda i: flight_label(df.loc[i]),
                        key="roundtrip_outbound_select",
                    )
                    selected_departure_token = df.loc[selected_outbound_idx, "_departure_token"]

                    if st.button("🔁 Ver vueltas compatibles", type="primary", key="load_returns"):
                        return_params = dict(params)
                        return_params["departure_token"] = selected_departure_token
                        try:
                            with st.spinner("Buscando vueltas compatibles..."):
                                return_result = serp_search(return_params)
                                return_df = vuelos_a_df(return_result, num_pasajeros=search_state.get("passengers", 1))
                            st.session_state["return_search"] = {
                                "departure_token": selected_departure_token,
                                "result": return_result,
                                "df": return_df,
                            }
                        except Exception as exc:
                            st.error(f"No se pudieron recuperar las vueltas: {exc}")
                            st.session_state.pop("return_search", None)

                    return_state = st.session_state.get("return_search")
                    if return_state and return_state.get("departure_token") == selected_departure_token:
                        return_df = return_state["df"]
                        st.markdown("### 🛬 Vueltas compatibles")
                        mostrar_df_vuelos(return_df)

                        if not return_df.empty:
                            selectable_returns = [idx for idx in return_df.index if pd.notna(return_df.loc[idx, "Precio_Num"])]
                            if selectable_returns:
                                selected_return_idx = st.selectbox(
                                    "Selecciona la combinación de vuelta",
                                    options=selectable_returns,
                                    format_func=lambda i: flight_label(return_df.loc[i]),
                                    key="roundtrip_return_select",
                                )
                                selected_row = return_df.loc[selected_return_idx]
                                selected_outbound_row = df.loc[selected_outbound_idx]

                                if pd.notna(selected_row["Precio_Num"]):
                                    total_comb = float(selected_row["Precio_Num"])
                                    pp_comb = total_comb / max(1, int(search_state.get("passengers", 1)))
                                    c_total, c_pp = st.columns(2)
                                    c_total.metric("💰 Precio total de la combinación", f"{total_comb:.0f} €")
                                    c_pp.metric("👤 Precio por persona", f"{pp_comb:.0f} €")

                                # Desglose económico por trayecto. Estas dos consultas one-way
                                # quedan cacheadas por serp_search, por lo que no se repiten
                                # mientras los parámetros sean idénticos.
                                mostrar_resumen_precios_trayectos(
                                    params,
                                    selected_outbound_row,
                                    selected_row,
                                    search_state.get("passengers", 1),
                                )

                                mostrar_booking_options(
                                    selected_row["_booking_token"],
                                    key_prefix=f"roundtrip_{selected_return_idx}",
                                    num_pasajeros=search_state.get("passengers", 1),
                                )

# ============================================================
# MODO 2: INSPIRAME
# ============================================================

else:
    st.subheader("🌍 Inspírame")
    st.caption("Busca destinos flexibles desde tu aeropuerto, filtrando por presupuesto y tipo de viaje.")

    st.sidebar.header("Explorar destinos")

    # Fila 1: aeropuerto de salida y presupuesto.
    col_org, col_bud = st.sidebar.columns(2)
    explore_origin = col_org.text_input("Salida (IATA)", value="MAD", key="explore_origin").upper().strip()
    explore_budget = col_bud.number_input("Presup. máx. (€)", min_value=20, max_value=5000, value=150, step=10)

    # Meses a explorar: selección múltiple de meses concretos en vez de un
    # único desplegable — es poco probable que el usuario tenga
    # disponibilidad los 6 meses completos.
    explore_month_labels = st.sidebar.multiselect(
        "Meses a explorar",
        options=list(MONTHS.keys()),
        default=list(MONTHS.keys())[:1],
        help="Elige uno o varios meses concretos; se consultan todos y se combinan los resultados.",
    )

    # Fila 2: duración del viaje y tipo de destino.
    col_dur, col_int = st.sidebar.columns(2)
    explore_duration_label = col_dur.selectbox("Duración", list(EXPLORE_DURATION.keys()), index=1)
    explore_interest_label = col_int.selectbox("Tipo destino", list(EXPLORE_INTEREST.keys()), index=0)

    # Fila 3: clase y escalas.
    col_clase, col_esc = st.sidebar.columns(2)
    explore_class_label = col_clase.selectbox("Clase", list(CABIN_CLASSES.keys()), index=0, key="explore_class")
    explore_stops_label = col_esc.selectbox("Escalas", list(STOPS_OPTIONS.keys()), index=0, key="explore_stops")

    # Fila 4: adultos y niños.
    col_ad, col_ni = st.sidebar.columns(2)
    explore_adults = col_ad.number_input("Adultos", min_value=1, max_value=9, value=1, key="explore_adults")
    explore_children = col_ni.number_input("Niños", min_value=0, max_value=8, value=0, key="explore_children")

    # Fila 5: equipaje de mano y duración máxima del vuelo.
    col_bags, col_maxdur = st.sidebar.columns(2)
    explore_bags = col_bags.number_input("Equip. mano", min_value=0, max_value=int(explore_adults + explore_children), value=0, key="explore_bags")
    explore_max_duration = col_maxdur.number_input("Dur. máx. (h)", min_value=0, max_value=30, value=0, key="explore_max_duration", help="0 = sin límite.")

    # Aerolíneas: filtro secundario, plegado para no ocupar espacio fijo.
    with st.sidebar.expander("Incluir / excluir aerolíneas"):
        explore_include = st.multiselect("Incluir solo aerolíneas", options=sorted(AIRLINES.keys()), key="explore_include")
        explore_exclude = st.multiselect("Excluir aerolíneas", options=sorted(AIRLINES.keys()), key="explore_exclude")
        if explore_include and explore_exclude:
            st.error("No puedes incluir y excluir aerolíneas simultáneamente.")

    mostrar_consumo_api(1)
    explore_btn = st.sidebar.button(
        "🌍 Buscar destinos",
        type="primary",
        use_container_width=True,
        disabled=bool(explore_include and explore_exclude) or not explore_month_labels,
    )
    if not explore_month_labels:
        st.sidebar.caption("⚠️ Elige al menos un mes para poder buscar.")

    if explore_btn:

        def build_explore_params(month_num):
            params = {
                "engine": "google_travel_explore",
                "departure_id": explore_origin,
                "type": "1",
                "month": month_num,
                "travel_duration": EXPLORE_DURATION[explore_duration_label],
                "travel_class": CABIN_CLASSES[explore_class_label],
                "adults": int(explore_adults),
                "children": int(explore_children),
                "bags": int(explore_bags),
                "max_price": int(explore_budget),
                "currency": CURRENCY,
                "hl": HL,
                "gl": GL,
            }
            if STOPS_OPTIONS[explore_stops_label] != "0":
                params["stops"] = STOPS_OPTIONS[explore_stops_label]
            if explore_max_duration > 0:
                params["max_duration"] = int(explore_max_duration * 60)
            interest = EXPLORE_INTEREST[explore_interest_label]
            if interest:
                params["interest"] = interest
            include_codes = airline_codes(explore_include)
            exclude_codes = airline_codes(explore_exclude)
            if include_codes:
                params["include_airlines"] = ",".join(include_codes)
            elif exclude_codes:
                params["exclude_airlines"] = ",".join(exclude_codes)
            return params

        try:
            with st.status("Buscando destinos...", expanded=True) as status:
                dfs = []
                last_result = None
                for mes_label in explore_month_labels:
                    status.update(label=f"Consultando {mes_label}...")
                    params = build_explore_params(MONTHS[mes_label])
                    params_json = json.dumps(params, sort_keys=True, separators=(",", ":"))
                    result = consultar_explore(params_json)
                    last_result = result
                    df_mes = explorar_a_df(result)
                    if not df_mes.empty:
                        df_mes = df_mes.copy()
                        df_mes["Mes consultado"] = mes_label
                        dfs.append(df_mes)

                if dfs:
                    explore_df = pd.concat(dfs, ignore_index=True)
                    # Si un mismo destino aparece en varios meses, nos quedamos
                    # con la combinación más barata.
                    if "Vuelo (€)" in explore_df.columns:
                        explore_df = (
                            explore_df.sort_values("Vuelo (€)", na_position="last")
                            .drop_duplicates(subset=["Destino", "Aeropuerto"], keep="first")
                            .reset_index(drop=True)
                        )
                else:
                    explore_df = pd.DataFrame()

                status.update(label="¡Destinos encontrados!", state="complete", expanded=False)
            st.session_state["explore_search"] = {
                "months": explore_month_labels,
                "result": last_result,
                "df": explore_df,
            }
        except Exception as exc:
            st.error(f"Error consultando Google Travel Explore: {exc}")
            st.session_state.pop("explore_search", None)

    explore_state = st.session_state.get("explore_search")
    if explore_state:
        explore_df = explore_state["df"]
        if explore_df.empty:
            st.warning("No se encontraron destinos con ese presupuesto y filtros.")
        else:
            if explore_df["Vuelo (€)"].notna().any():
                st.metric("💸 Destino más barato", f"{int(explore_df['Vuelo (€)'].dropna().min())} €")
            columnas_explore = [
                "Destino",
                "País",
                "Aeropuerto",
                "Ida",
                "Vuelta",
                "Vuelo (€)",
                "Hotel/noche",
                "Duración",
                "Escalas",
                "Aerolínea",
            ]
            if "Mes consultado" in explore_df.columns and len(explore_state.get("months", [])) > 1:
                columnas_explore.append("Mes consultado")
            st.dataframe(
                explore_df[columnas_explore],
                hide_index=True,
                use_container_width=True,
            )
            map_df = explore_df[["_lat", "_lon"]].dropna().rename(columns={"_lat": "lat", "_lon": "lon"})
            if not map_df.empty:
                st.map(map_df)
