import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import datetime
import airportsdata

@st.cache_data
def load_airports():
    return airportsdata.load('IATA')

airports = load_airports()

def obtener_pais(iata_code):
    try:
        return airports[iata_code.upper()]['country']
    except:
        return ""

# Configuración de página
st.set_page_config(page_title="Buscador Vuelos", layout="wide")

# Inyección de CSS para fondo principal y diseño de la barra lateral
page_bg_img = """
<style>
/* Imagen de fondo principal con capa oscura */
.stApp {
    background-image: linear-gradient(rgba(14, 17, 23, 0.75), rgba(14, 17, 23, 0.85)), url("https://images.unsplash.com/photo-1542296332-2e4473faf563?q=80&w=2000&auto=format&fit=crop");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}

/* Diseño elegante para el panel lateral */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(17, 21, 30, 0.95) 0%, rgba(28, 33, 45, 0.95) 100%) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* Reducir el espacio superior */
.block-container {
    padding-top: 2rem !important;
}
</style>
"""
st.markdown(page_bg_img, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Buscador de Vuelos Low-Cost ✈️</h1>", unsafe_allow_html=True)

# --- BARRA LATERAL (CONFIGURACIÓN) ---
st.sidebar.header("Configuración de Búsqueda")
origen = st.sidebar.text_input("Origen (IATA)", value="MAD").upper()
destino = st.sidebar.text_input("Destino (IATA)", value="BER").upper()

hoy = datetime.date.today()

fecha_ida = st.sidebar.date_input("Fecha de Ida", min_value=hoy, value=hoy)
buscar_vuelta = st.sidebar.checkbox("Añadir vuelo de vuelta")

if buscar_vuelta:
    fecha_vuelta = st.sidebar.date_input("Fecha de Vuelta", min_value=fecha_ida, value=fecha_ida)

vuelo_directo = st.sidebar.checkbox("Vuelo Directo (Sin escalas)", value=False)
buscar_btn = st.sidebar.button("Buscar vuelos", type="primary", use_container_width=True)

# --- LÓGICA DE BÚSQUEDA ---
def consultar_api(orig, dest, fecha, solo_directos):
    api_key = st.secrets["SERPAPI_API_KEY"]
    params = {
        "engine": "google_flights",
        "departure_id": orig,
        "arrival_id": dest,
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
    
    pais_orig = obtener_pais(orig)
    pais_dest = obtener_pais(dest)

    for item in todos_los_vuelos:
        trayectos = item.get("flights", [])
        if not trayectos: continue
            
        escalas = len(trayectos) - 1
        if solo_directos and escalas > 0:
            continue
            
        escala_str = "Directo" if escalas == 0 else f"{escalas} escala(s)"
        
        primer_trayecto = trayectos[0]
        salida_dt = primer_trayecto.get("departure_airport", {}).get("time", " - ")
        fecha_salida, hora_salida = salida_dt.split(" ") if " " in salida_dt else (salida_dt, "")
        
        ultimo_trayecto = trayectos[-1]
        llegada_dt = ultimo_trayecto.get("arrival_airport", {}).get("time", " - ")
        fecha_llegada, hora_llegada = llegada_dt.split(" ") if " " in llegada_dt else (llegada_dt, "")
        
        aerolineas = ", ".join([v.get("airline", "") for v in trayectos])
        
        vuelos_limpios.append({
            "Aerolínea": aerolineas,
            "Precio": item.get("price"),
            "Origen": f"{orig} ({pais_orig})",
            "Destino": f"{dest} ({pais_dest})",
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
            
        df = df.sort_values(by="Precio").reset_index(drop=True)
        df["Precio"] = df["Precio"].apply(lambda x: f"{int(x)} €" if pd.notna(x) else "N/A")
        
        return df
    return pd.DataFrame()

def mostrar_tabla_con_metricas(df, titulo):
    st.subheader(titulo)
    if not df.empty:
        st.dataframe(df.head(5), hide_index=True, use_container_width=True)
        if len(df) > 5:
            with st.expander(f"Ver los {len(df)-5} resultados restantes"):
                st.dataframe(df.iloc[5:].reset_index(drop=True), hide_index=True, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        mejor_precio = df.iloc[0]["Precio"]
        mejor_aerolinea = df.iloc[0]["Aerolínea"]
        st.metric(label="🏆 Opción más barata", value=mejor_precio, delta=mejor_aerolinea, delta_color="off")
        st.markdown("<br><br>", unsafe_allow_html=True)
    else:
        st.warning("No se encontraron vuelos para esta ruta con los filtros seleccionados.")

# --- RENDERIZADO DE RESULTADOS ---
if buscar_btn:
    with st.status("Buscando tarifas de ida...", expanded=True) as status_ida:
        df_ida = consultar_api(origen, destino, fecha_ida, vuelo_directo)
        status_ida.update(label="¡Búsqueda de ida completada!", state="complete", expanded=False)
    mostrar_tabla_con_metricas(df_ida, "🛫 Trayecto de Ida")
    
    if buscar_vuelta:
        with st.status("Buscando tarifas de vuelta...", expanded=True) as status_vuelta:
            df_vuelta = consultar_api(destino, origen, fecha_vuelta, vuelo_directo)
            status_vuelta.update(label="¡Búsqueda de vuelta completada!", state="complete", expanded=False)
        mostrar_tabla_con_metricas(df_vuelta, "🛬 Trayecto de Vuelta")
