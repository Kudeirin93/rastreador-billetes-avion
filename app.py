import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import datetime
import airportsdata

# Optimización: Cacheamos la base de datos de aeropuertos para que la app cargue más rápido
@st.cache_data
def load_airports():
    return airportsdata.load('IATA')

airports = load_airports()

def obtener_pais(iata_code):
    try:
        return airports[iata_code.upper()]['country']
    except:
        return ""

st.title("Buscador de Vuelos Low-Cost ✈️")

# --- BARRA LATERAL (CONFIGURACIÓN) ---
st.sidebar.header("Configuración de Búsqueda")
origen = st.sidebar.text_input("Origen (IATA)", value="MAD").upper()
destino = st.sidebar.text_input("Destino (IATA)", value="BER").upper()

fecha_ida = st.sidebar.date_input("Fecha de Ida")
buscar_vuelta = st.sidebar.checkbox("Añadir vuelo de vuelta")

if buscar_vuelta:
    fecha_vuelta = st.sidebar.date_input("Fecha de Vuelta")

vuelo_directo = st.sidebar.checkbox("Vuelo Directo (Sin escalas)", value=False)

# Botón de búsqueda también en la barra lateral
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
    
    # Añadir filtro nativo de Google Flights (1 = Solo vuelos directos)
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
        
        # Filtro de seguridad secundario
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
            "Precio (€)": item.get("price"),
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
        
        # Calcular tiempo total (Llegada - Salida)
        try:
            inicio = pd.to_datetime(df['Fecha Salida'] + ' ' + df['Hora Salida'])
            fin = pd.to_datetime(df['Fecha Llegada'] + ' ' + df['Hora Llegada'])
            duracion = fin - inicio
            df['Tiempo Total'] = duracion.dt.components['hours'].astype(str).str.zfill(2) + "h " + duracion.dt.components['minutes'].astype(str).str.zfill(2) + "m"
        except:
            df['Tiempo Total'] = "N/A"
            
        # Reordenar las columnas y mostrar primero el precio más bajo
        df = df.sort_values(by="Precio (€)").reset_index(drop=True)
        return df
    return pd.DataFrame()


def mostrar_tabla(df, titulo):
    st.subheader(titulo)
    if not df.empty:
        st.dataframe(df.head(5))
        if len(df) > 5:
            with st.expander(f"Ver los {len(df)-5} resultados restantes"):
                st.dataframe(df.iloc[5:].reset_index(drop=True))
    else:
        st.warning("No se encontraron vuelos para esta ruta con los filtros seleccionados.")

if buscar_btn:
    with st.spinner("Consultando tarifas de ida..."):
        df_ida = consultar_api(origen, destino, fecha_ida, vuelo_directo)
        mostrar_tabla(df_ida, "🛫 Trayecto de Ida")
        
    if buscar_vuelta:
        with st.spinner("Consultando tarifas de vuelta..."):
            df_vuelta = consultar_api(destino, origen, fecha_vuelta, vuelo_directo)
            mostrar_tabla(df_vuelta, "🛬 Trayecto de Vuelta")
