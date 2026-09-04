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
    padding-top: 1rem !important;
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
</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>Buscador de Vuelos Low-Cost ✈️</h1>", unsafe_allow_html=True)

# ============================================================
# DATOS AUXILIARES
# ============================================================

@st.cache_data
def load_airports():
    return airportsdata.load("IATA")

airports = load_airports()

# --- NUEVA FUNCIÓN: Generar lista de ciudades/aeropuertos ---
@st.cache_data
def obtener_opciones_aeropuertos():
    opciones = []
    for iata, info in airports.items():
        if len(iata) == 3 and info.get('city'):
            # Formato: "Ciudad - Nombre del Aeropuerto (IATA)"
            opciones.append(f"{info['city']} - {info.get('name', 'Aeropuerto')} ({iata})")
    return sorted(opciones)

opciones_busqueda = obtener_opciones_aeropuertos()

def buscar_indice_por_iata(iata, opciones):
    iata = iata.upper()
    for i, opc in enumerate(opciones):
        if opc.endswith(f"({iata})"):
            return i
    return 0


def selector_aeropuerto(label, iata_por_defecto, key_prefix):
    """Desplegable nativo de Streamlit (una sola fila). El propio combobox
    ya filtra por subcadena a medida que se escribe (ciudad, nombre del
    aeropuerto o código IATA, en cualquier posición del texto) — se
    comprobó que no hace falta un cuadro de búsqueda aparte."""
    return st.sidebar.selectbox(
        label,
        options=opciones_busqueda,
        index=buscar_indice_por_iata(iata_por_defecto, opciones_busqueda),
        key=f"{key_prefix}_select",
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
    months = {"Cualquier mes (próximos 6 meses)": 0}
    for offset in range(6):
        month_num = ((today.month - 1 + offset) % 12) + 1
        year = today.year + ((today.month - 1 + offset) // 12)
        months[f"{MONTH_NAMES[month_num]} {year}"] = month_num
    return months

MONTHS = build_explore_months()


def obtener_pais(iata_code):
    try:
        return airports[iata_code.upper()]["country"]
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

# ============================================================
# PERSISTENCIA LOCAL: HISTORICO Y ALERTAS
# ============================================================


def init_db():
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
                    travel_class TEXT NOT NULL,
                    adults INTEGER NOT NULL,
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
            conn.commit()
    except Exception:
        pass


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


def vuelos_a_df(results):
    rows = []

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
    df = df.sort_values(["Precio_Num", "Duración_Min"], na_position="last").reset_index(drop=True)
    df["Precio"] = df["Precio_Num"].apply(lambda x: f"{int(x)} €" if pd.notna(x) else "N/A")
    return df


DISPLAY_COLUMNS = [
    "Aerolínea",
    "Vuelo",
    "Precio",
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
    st.dataframe(df[DISPLAY_COLUMNS], hide_index=True, use_container_width=True)


def flight_label(row):
    return (
        f"{row.get('Precio', 'N/A')} · {row.get('Aerolínea', '')} · "
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


def booking_options_a_df(results):
    rows = []
    for option in results.get("booking_options", []) or []:
        separate = bool(option.get("separate_tickets"))
        for section in ("together", "departing", "returning"):
            data = option.get(section)
            if not data:
                continue
            baggage = data.get("baggage_prices") or []
            if isinstance(baggage, str):
                baggage = [baggage]
            rows.append({
                "Tramo": {
                    "together": "Todo el itinerario",
                    "departing": "Ida",
                    "returning": "Vuelta",
                }[section],
                "Proveedor": data.get("book_with", ""),
                "Precio": data.get("price"),
                "Billetes separados": "Sí" if separate else "No",
                "Equipaje": " · ".join(map(str, baggage)) if baggage else "",
                "Comercializado como": ", ".join(data.get("marketed_as", []) or []),
            })
    return pd.DataFrame(rows)


def mostrar_booking_options(booking_token, key_prefix):
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

            booking_df = booking_options_a_df(booking_result)
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
        "departure_id": origin,
        "arrival_id": destination,
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

# ============================================================
# MODO Y CONSUMO API
# ============================================================

st.sidebar.markdown(
    "<h2 style='margin-top: -40px;'>✈️ Menú Principal</h2>",
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

    # Cuadro de búsqueda + desplegable acotado (filtran por subcadena o fuzzy match)
    origen_seleccion = selector_aeropuerto("Origen (Ciudad o Aeropuerto)", def_origen, "origen")
    destino_seleccion = selector_aeropuerto("Destino (Ciudad o Aeropuerto)", def_destino, "destino")

    # Extracción automática del código IATA (los 3 caracteres entre paréntesis al final)
    origen = origen_seleccion.split("(")[-1].replace(")", "").strip()
    destino = destino_seleccion.split("(")[-1].replace(")", "").strip()
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
    buscar_cercanos_destino = col_cerc_d.checkbox("Cercanos llegada", value=False)
    radio_km_origen = st.sidebar.slider("Radio de salida (km)", min_value=50, max_value=600, value=100, step=10) if buscar_cercanos_origen else 0
    radio_km_destino = st.sidebar.slider("Radio de llegada (km)", min_value=50, max_value=600, value=100, step=10) if buscar_cercanos_destino else 0

    # Fila 2: búsqueda exhaustiva y fechas flexibles de ida.
    col_exh, col_flex_i = st.sidebar.columns(2)
    busqueda_exhaustiva = col_exh.checkbox(
        "Exhaustiva",
        value=True,
        help="Activa show_hidden + deep_search para aproximarse a los resultados del navegador.",
    )
    flex_ida = col_flex_i.checkbox("Flex. ida", value=False)

    # Fechas flexibles de vuelta sólo aplica en modo ida y vuelta: se añade
    # como fila extra (condicional) en vez de forzar una 3ª columna estrecha.
    flex_vuelta = st.sidebar.checkbox("Fechas flexibles de vuelta", value=False) if buscar_vuelta else False

    radio_ida = st.sidebar.slider("Días de margen (ida)", min_value=1, max_value=5, value=3) if flex_ida else 0
    radio_vuelta = st.sidebar.slider("Días de margen (vuelta)", min_value=1, max_value=5, value=3) if (buscar_vuelta and flex_vuelta) else 0

    # Cálculo multiplicativo de la matriz de llamadas
    consultas_ida = (1 + 2 * radio_ida) if flex_ida else 1
    consultas_vuelta = (1 + 2 * radio_vuelta) if flex_vuelta else 1
    coste_estimado = consultas_ida * consultas_vuelta

    if coste_estimado > 10:
        st.sidebar.warning(f"⚠️ La flexibilidad cruzada lanzará {coste_estimado} peticiones simultáneas a la API.")

    mostrar_consumo_api(coste_estimado)

    # ---> ESTE ES EL BOTÓN QUE FALTA <---
    buscar_btn = st.sidebar.button(
        "Buscar vuelos",
        type="primary",
        use_container_width=True,
        disabled=bool(incluir_aerolineas and excluir_aerolineas),
    )

    if buscar_btn:
        if not origen or not destino:
            st.error("Indica un origen y un destino.")
        elif origen == destino:
            st.error("Origen y destino no pueden ser iguales.")
        else:
            st.query_params["origen"] = origen
            st.query_params["destino"] = destino
            st.query_params["ida"] = fecha_ida.strftime("%Y-%m-%d")
            if buscar_vuelta:
                st.query_params["vuelta"] = fecha_vuelta.strftime("%Y-%m-%d")
            elif "vuelta" in st.query_params:
                del st.query_params["vuelta"]

            orig_query = obtener_lista_aeropuertos(origen, radio_km_origen) if buscar_cercanos_origen else origen
            dest_query = obtener_lista_aeropuertos(destino, radio_km_destino) if buscar_cercanos_destino else destino

            params = build_flight_params(
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

            try:
                with st.status("Buscando tarifas...", expanded=True) as status:
                    result = serp_search(params)
                    df = vuelos_a_df(result)
                    status.update(label="¡Búsqueda completada!", state="complete", expanded=False)

                st.session_state["flight_search"] = {
                    "params": params,
                    "result": result,
                    "df": df,
                    "origin": origen,
                    "destination": destino,
                    "outbound_date": fecha_ida,
                    "return_date": fecha_vuelta if buscar_vuelta else None,
                    "travel_class": CABIN_CLASSES[clase_sel],
                    "adults": adultos,
                    "flexible_ida": flex_ida,
                    "radius_ida": radio_ida,
                    "flexible_vuelta": flex_vuelta,
                    "radius_vuelta": radio_vuelta,
                }
                st.session_state.pop("return_search", None)

                if not df.empty and df["Precio_Num"].notna().any():
                    guardar_precio(
                        origen,
                        destino,
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
            st.metric("💰 Mejor precio detectado", f"{int(min_price)} €")

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
                mostrar_booking_options(df.loc[selected_idx, "_booking_token"], key_prefix=f"oneway_{selected_idx}")

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
                            return_df = vuelos_a_df(return_result)
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
                            if pd.notna(selected_row["Precio_Num"]):
                                st.metric("💰 Precio total de la combinación", f"{int(selected_row['Precio_Num'])} €")
                            mostrar_booking_options(
                                selected_row["_booking_token"],
                                key_prefix=f"roundtrip_{selected_return_idx}",
                            )

# ============================================================
# MODO 2: INSPIRAME
# ============================================================

else:
    st.subheader("🌍 Inspírame")
    st.caption("Busca destinos flexibles desde tu aeropuerto, filtrando por presupuesto y tipo de viaje.")

    st.sidebar.header("Explorar destinos")
    explore_origin = st.sidebar.text_input("Aeropuerto de salida (IATA)", value="MAD", key="explore_origin").upper().strip()
    explore_budget = st.sidebar.number_input("Presupuesto máximo de vuelo (€)", min_value=20, max_value=5000, value=150, step=10)
    explore_month_label = st.sidebar.selectbox("Mes", list(MONTHS.keys()), index=0)
    explore_duration_label = st.sidebar.selectbox("Duración del viaje", list(EXPLORE_DURATION.keys()), index=1)
    explore_interest_label = st.sidebar.selectbox("Tipo de destino", list(EXPLORE_INTEREST.keys()), index=0)
    explore_class_label = st.sidebar.selectbox("Clase", list(CABIN_CLASSES.keys()), index=0, key="explore_class")
    explore_adults = st.sidebar.number_input("Adultos", min_value=1, max_value=9, value=1, key="explore_adults")
    explore_children = st.sidebar.number_input("Niños", min_value=0, max_value=8, value=0, key="explore_children")
    explore_bags = st.sidebar.number_input("Equipajes de mano", min_value=0, max_value=int(explore_adults + explore_children), value=0, key="explore_bags")
    explore_stops_label = st.sidebar.selectbox("Escalas", list(STOPS_OPTIONS.keys()), index=0, key="explore_stops")
    explore_max_duration = st.sidebar.number_input("Duración máxima del vuelo (h)", min_value=0, max_value=30, value=0, key="explore_max_duration", help="0 = sin límite.")
    explore_include = st.sidebar.multiselect("Incluir solo aerolíneas", options=sorted(AIRLINES.keys()), key="explore_include")
    explore_exclude = st.sidebar.multiselect("Excluir aerolíneas", options=sorted(AIRLINES.keys()), key="explore_exclude")

    if explore_include and explore_exclude:
        st.sidebar.error("No puedes incluir y excluir aerolíneas simultáneamente.")

    mostrar_consumo_api(1)
    explore_btn = st.sidebar.button(
        "🌍 Buscar destinos",
        type="primary",
        use_container_width=True,
        disabled=bool(explore_include and explore_exclude),
    )

    if explore_btn:
        params = {
            "engine": "google_travel_explore",
            "departure_id": explore_origin,
            "type": "1",
            "month": MONTHS[explore_month_label],
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

        try:
            with st.status("Buscando destinos...", expanded=True) as status:
                params_json = json.dumps(params, sort_keys=True, separators=(",", ":"))
                result = consultar_explore(params_json)
                explore_df = explorar_a_df(result)
                status.update(label="¡Destinos encontrados!", state="complete", expanded=False)
            st.session_state["explore_search"] = {"params": params, "result": result, "df": explore_df}
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
            st.dataframe(
                explore_df[
                    [
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
                ],
                hide_index=True,
                use_container_width=True,
            )
            map_df = explore_df[["_lat", "_lon"]].dropna().rename(columns={"_lat": "lat", "_lon": "lon"})
            if not map_df.empty:
                st.map(map_df)
