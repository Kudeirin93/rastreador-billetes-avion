import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import datetime
import airportsdata

# Cargar base de datos de aeropuertos para obtener el país
airports = airportsdata.load('IATA')

def obtener_pais(iata_code):
    try:
        return airports[iata_code.upper()]['country']
    except:
        return ""

st.title("Buscador de Vuelos Low-Cost ✈️")

# Configuración de búsqueda en la barra lateral
st.sidebar.header("Ruta")
origen = st.sidebar.text_input("Origen (IATA)", value="MAD").upper()
destino = st.sidebar.text_input("Destino (IATA)", value="BER").upper()

# Selectores de fecha para Ida y Vuelta
col_ida, col_vuelta = st.columns(2)
with col_ida:
    fecha_ida = st.date_input("Fecha de Ida")
with col_vuelta:
    buscar_vuelta = st.checkbox("Añadir vuelo de vuelta")
    if buscar_vuelta:
        fecha_vuelta = st.date_input("Fecha de Vuelta")

def consultar_api(origen, destino, fecha):
    api_key = st.secrets["SERPAPI_API_KEY"]
    params = {
        "engine": "google_flights",
        "departure_id": origen,
        "arrival_id": destino,
        "outbound_date": fecha.strftime("%Y-%m-%d"),
        "currency": "EUR",
        "hl": "es",
        "type": "2",
        "api_key": api_key
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    
    todos_los_vuelos = results.get("best_flights", []) + results.get("other_flights", [])
    vuelos_limpios = []
    
    pais_orig = obtener_pais(origen)
    pais_dest = obtener_pais(destino)

    for item in todos_los_vuelos:
        trayectos = item.get("flights", [])
        if not trayectos: continue
            
        escalas = len(trayectos) - 1
        escala_str = "Directo" if escalas == 0 else f"{escalas} escala(s)"
        
        primer_trayecto = trayectos[0]
        salida_aeropuerto = primer_trayecto.get("departure_airport", {}).get("id")
        salida_dt = primer_trayecto.get("departure_airport", {}).get("time", " - ")
        fecha_salida, hora_salida = salida_dt.split(" ") if " " in salida_dt else (salida_dt, "")
        
        ultimo_trayecto = trayectos[-1]
        llegada_aeropuerto = ultimo_trayecto.get("arrival_airport", {}).get("id")
        llegada_dt = ultimo_trayecto.get("arrival_airport", {}).get("time", " - ")
        fecha_llegada, hora_llegada = llegada_dt.split(" ") if " " in llegada_dt else (llegada_dt, "")
        
        aerolineas = ", ".join([v.get("airline", "") for v in trayectos])
        
        vuelos_limpios.append({
            "Aerolínea": aerolineas,
            "Precio (€)": item.get("price"),
            "Origen": f"{salida_aeropuerto} ({pais_orig})",
            "Destino": f"{llegada_aeropuerto} ({pais_dest})",
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
            # Formato "XXh YYm"
            df['Tiempo Total'] = duracion.dt.components['hours'].astype(str).str.zfill(2) + "h " + duracion.dt.components['minutes'].astype(str).str.zfill(2) + "m"
        except:
            df['Tiempo Total'] = "N/A"
            
        # Ordenar por precio y estructurar columnas
        df = df.sort_values(by="Precio (€)").reset_index(drop=True)
        return df
    return pd.DataFrame()

def mostrar_tabla(df, titulo):
    st.subheader(titulo)
    if not df.empty:
        # Mostrar los 5 más baratos por defecto
        st.dataframe(df.head(5))
        
        # Desplegable para el resto
        if len(df) > 5:
            with st.expander(f"Ver los {len(df)-5} resultados restantes"):
                st.dataframe(df.iloc[5:].reset_index(drop=True))
    else:
        st.warning("No se encontraron vuelos para esta ruta.")

if st.button("Buscar vuelos"):
    with st.spinner("Consultando tarifas..."):
        # Buscar Ida
        df_ida = consultar_api(origen, destino, fecha_ida)
        mostrar_tabla(df_ida, "🛫 Trayecto de Ida")
        
        # Buscar Vuelta (si está marcado)
        if buscar_vuelta:
            df_vuelta = consultar_api(destino, origen, fecha_vuelta)
            mostrar_tabla(df_vuelta, "🛬 Trayecto de Vuelta")
