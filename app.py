import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import datetime
import airportsdata
import urllib.request
import json
import math

@st.cache_data
def load_airports():
    return airportsdata.load('IATA')

airports = load_airports()

def obtener_pais(iata_code):
    try:
        return airports[iata_code.upper()]['country']
    except:
        return ""

def obtener_info_cuenta(api_key):
    try:
        url = f"https://serpapi.com/account?api_key={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data.get("searches_per_month", "N/A"), data.get("total_searches_left", "N/A")
    except:
        return None, None

# --- CÁLCULO DE DISTANCIAS Y AEROPUERTOS CERCANOS ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def obtener_lista_aeropuertos(iata_base, radio_km):
    iata_base = iata_base.upper()
    if iata_base not in airports:
        return iata_base # Si no lo encuentra, devuelve el original
        
    lat_base = airports[iata_base]['lat']
    lon_base = airports[iata_base]['lon']
    
    cercanos = []
    for iata, info in airports.items():
        if len(iata) == 3: # Asegurar que es un código IATA válido
            dist = haversine(lat_base, lon_base, info['lat'], info['lon'])
            if dist <= radio_km:
                cercanos.append((iata, dist))
                
    # Ordenar por distancia y limitar a los 5 más cercanos para no saturar la API de Google
    cercanos.sort(key=lambda x: x[1])
    lista_final = [c[0] for c in cercanos[:5]]
    return ",".join(lista_final)

st.set_page_config(page_title="Buscador Vuelos", layout="wide")

page_bg_img = """
<style>
.stApp {
    background-image: linear-gradient(rgba(14, 17, 23, 0.75), rgba(14, 17, 23, 0.85)), url("https://images.unsplash.com/photo-1542296332-2e4473faf563?q=80&w=2000&auto=format&fit=crop");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(17, 21, 30, 0.95) 0%, rgba(28, 33, 45, 0.95) 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}
.block-container {
    padding-top: 2rem !important;
}
[data-testid="stStatusWidget"] {
    margin-top: -10px;
}
</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)
st.markdown("<h1 style='text-align: center;'>Buscador de Vuelos Low-Cost ✈️</h1><br>", unsafe_allow_html=True)

# --- BARRA LATERAL (CONFIGURACIÓN) ---
st.sidebar.header("Configuración de Búsqueda")
origen = st.sidebar.text_input("Origen (IATA)", value="MAD").upper()
destino = st.sidebar.text_input("Destino (IATA)", value="BER").upper()

hoy = datetime.date.today()

fecha_ida = st.sidebar.date_input("Fecha de Ida", min_value=hoy, value=hoy)
buscar_vuelta = st.sidebar.checkbox("Añadir vuelo de vuelta")

if buscar_vuelta:
    fecha_vuelta = st.sidebar.date_input("Fecha de Vuelta", min_value=fecha_ida, value=fecha_ida)

# Selector de aeropuertos cercanos
buscar_cercanos = st.sidebar.checkbox("Incluir aeropuertos cercanos", value=False)
if buscar_cercanos:
    radio_km = st.sidebar.slider("Radio de búsqueda (km)", min_value=50, max_value=300, value=100, step=10)
else:
    radio_km = 0

vuelo_directo = st.sidebar.checkbox("Vuelo Directo (Sin escalas)", value=False)
mostrar_tendencia = st.sidebar.checkbox("Mostrar tendencia de precios", value=False)
buscar_btn = st.sidebar.button("Buscar vuelos", type="primary", use_container_width=True)

# --- PANEL DE CONSUMO API ---
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Consumo de SerpApi")

coste_estimado = 1
if buscar_vuelta: coste_estimado += 1
if mostrar_tendencia:
    coste_estimado += 7
    if buscar_vuelta: coste_estimado += 7

st.sidebar.info(f"⚡ **Coste estimado de esta consulta:** {coste_estimado} créditos")

try:
    api_key = st.secrets["SERPAPI_API_KEY"]
    total_creditos, creditos_restantes = obtener_info_cuenta(api_key)
    
    if total_creditos is not None:
        st.sidebar.metric("Créditos Restantes", f"{creditos_restantes} / {total_creditos}")
        if isinstance(total_creditos, int) and isinstance(creditos_restantes, int):
            porcentaje_restante = max(0.0, min(1.0, creditos_restantes / total_creditos))
            st.sidebar.progress(porcentaje_restante)
except Exception as e:
    st.sidebar.warning("Configura tu SERPAPI_API_KEY en los secretos para ver tu consumo.")


# --- LÓGICA DE BÚSQUEDA ---
def consultar_api(orig_query, dest_query, fecha, solo_directos):
    api_key = st.secrets["SERPAPI_API_KEY"]
    params = {
        "engine": "google_flights",
        "departure_id": orig_query,
        "arrival_id": dest_query,
        "outbound_date": fecha.strftime("%Y-%m-%d"),
        "currency": "EUR",
        "hl": "es",
        "type": "2",
        "api_key": api_key
    }
    if solo_directos:
        params["stops"] = "1"
        
    search = GoogleSearch(params)
    results = search.get_dict()
    
    todos_los_vuelos = results.get("best_flights", []) + results.get("other_flights", [])
    vuelos_limpios = []

    for item in todos_los_vuelos:
        trayectos = item.get("flights", [])
        if not trayectos: continue
            
        escalas = len(trayectos) - 1
        if solo_directos and escalas > 0: continue
            
        escala_str = "Directo" if escalas == 0 else f"{escalas} escala(s)"
        primer_trayecto = trayectos[0]
        
        # Identificamos el aeropuerto EXACTO desde el que sale/llega el vuelo (útil si hay cercanos)
        salida_aeropuerto = primer_trayecto.get("departure_airport", {}).get("id", "")
        salida_dt = primer_trayecto.get("departure_airport", {}).get("time", " - ")
        fecha_salida, hora_salida = salida_dt.split(" ") if " " in salida_dt else (salida_dt, "")
        
        ultimo_trayecto = trayectos[-1]
        llegada_aeropuerto = ultimo_trayecto.get("arrival_airport", {}).get("id", "")
        llegada_dt = ultimo_trayecto.get("arrival_airport", {}).get("time", " - ")
        fecha_llegada, hora_llegada = llegada_dt.split(" ") if " " in llegada_dt else (llegada_dt, "")
        
        pais_salida = obtener_pais(salida_aeropuerto)
        pais_llegada = obtener_pais(llegada_aeropuerto)
        
        aerolineas = ", ".join([v.get("airline", "") for v in trayectos])
        
        vuelos_limpios.append({
            "Aerolínea": aerolineas,
            "Precio_Num": item.get("price", 0),
            "Origen": f"{salida_aeropuerto} ({pais_salida})",
            "Destino": f"{llegada_aeropuerto} ({pais_llegada})",
            "Fecha Salida": fecha_salida,
            "Hora Salida": hora_salida,
            "Fecha Llegada": fecha_llegada,
            "Hora Llegada": hora_llegada,
            "Escalas": escala_str,
        })
        
    if vuelos_limpios:
        df = pd.DataFrame(vuelos_limpios)
        try:
            inicio = pd.to_datetime(df['Fecha Salida'] + ' ' + df['Hora Salida'])
            fin = pd.to_datetime(df['Fecha Llegada'] + ' ' + df['Hora Llegada'])
            duracion = fin - inicio
            df['Tiempo Total'] = duracion.dt.components['hours'].astype(str).str.zfill(2) + "h " + duracion.dt.components['minutes'].astype(str).str.zfill(2) + "m"
        except:
            df['Tiempo Total'] = "N/A"
            
        df = df.sort_values(by="Precio_Num").reset_index(drop=True)
        df["Precio"] = df["Precio_Num"].apply(lambda x: f"{int(x)} €" if pd.notna(x) else "N/A")
        return df.drop(columns=["Precio_Num"])
    return pd.DataFrame()

def obtener_tendencia_precios(orig_query, dest_query, fecha_base, solo_directos):
    datos_tendencia = []
    for delta in range(-3, 4):
        fecha_eval = fecha_base + datetime.timedelta(days=delta)
        if fecha_eval < datetime.date.today(): continue
            
        api_key = st.secrets["SERPAPI_API_KEY"]
        params = {
            "engine": "google_flights",
            "departure_id": orig_query,
            "arrival_id": dest_query,
            "outbound_date": fecha_eval.strftime("%Y-%m-%d"),
            "currency": "EUR",
            "hl": "es",
            "type": "2",
            "api_key": api_key
        }
        if solo_directos:
            params["stops"] = "1"
            
        try:
            search = GoogleSearch(params)
            res = search.get_dict()
            vuelos = res.get("best_flights", []) + res.get("other_flights", [])
            if vuelos:
                precio_min = min([v.get("price", 9999) for v in vuelos if v.get("price")])
                datos_tendencia.append({"Fecha": fecha_eval, "Precio (€)": precio_min})
        except:
            pass
    return pd.DataFrame(datos_tendencia)

def mostrar_tabla_y_datos(df, orig_query, dest_query, fecha, solo_directos, con_tendencia):
    if not df.empty:
        st.dataframe(df.head(5), hide_index=True, use_container_width=True)
        if len(df) > 5:
            with st.expander(f"Ver los {len(df)-5} resultados restantes"):
                st.dataframe(df.iloc[5:].reset_index(drop=True), hide_index=True, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        mejor_precio = df.iloc[0]["Precio"]
        
        if con_tendencia:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric(label=f"💰 Mejor precio ({fecha.strftime('%d/%m')})", value=mejor_precio)
            with col2:
                df_tendencia = obtener_tendencia_precios(orig_query, dest_query, fecha, solo_directos)
                if not df_tendencia.empty:
                    st.markdown("**Tendencia de precios (±3 días)**")
                    st.line_chart(df_tendencia.set_index("Fecha"))
        else:
            st.metric(label=f"💰 Mejor precio para el {fecha.strftime('%d/%m/%Y')}", value=mejor_precio)
            
        st.markdown("<hr>", unsafe_allow_html=True)
    else:
        st.warning("No se encontraron vuelos para esta ruta con los filtros seleccionados.")

# --- RENDERIZADO DE RESULTADOS ---
if buscar_btn:
    # 1. Preparar las consultas expandidas (Aeropuertos cercanos si aplica)
    orig_query = obtener_lista_aeropuertos(origen, radio_km) if buscar_cercanos else origen
    dest_query = obtener_lista_aeropuertos(destino, radio_km) if buscar_cercanos else destino

    col_tit_ida, col_stat_ida = st.columns([1, 3])
    with col_tit_ida:
        st.subheader("🛫 Trayecto de Ida")
    with col_stat_ida:
        with st.status("Buscando tarifas de ida...", expanded=True) as status_ida:
            df_ida = consultar_api(orig_query, dest_query, fecha_ida, vuelo_directo)
            status_ida.update(label="¡Búsqueda de ida completada!", state="complete", expanded=False)
            
    mostrar_tabla_y_datos(df_ida, orig_query, dest_query, fecha_ida, vuelo_directo, mostrar_tendencia)
    
    if buscar_vuelta:
        col_tit_vue, col_stat_vue = st.columns([1, 3])
        with col_tit_vue:
            st.subheader("🛬 Trayecto de Vuelta")
        with col_stat_vue:
            with st.status("Buscando tarifas de vuelta...", expanded=True) as status_vuelta:
                df_vuelta = consultar_api(dest_query, orig_query, fecha_vuelta, vuelo_directo)
                status_vuelta.update(label="¡Búsqueda de vuelta completada!", state="complete", expanded=False)
                
        mostrar_tabla_y_datos(df_vuelta, dest_query, orig_query, fecha_vuelta, vuelo_directo, mostrar_tendencia)
