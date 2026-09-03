import streamlit as st
import pandas as pd
from serpapi import GoogleSearch

st.title("Buscador de Vuelos Low-Cost ✈️")

# Controles de configuración para el usuario
col1, col2, col3 = st.columns(3)
with col1:
    origen = st.text_input("Origen (IATA)", value="MAD")
with col2:
    destino = st.text_input("Destino (IATA)", value="BER")
with col3:
    fecha = st.date_input("Fecha de salida")

if st.button("Buscar vuelos"):
    with st.spinner("Buscando las mejores tarifas..."):
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
        
        # Unir mejores opciones y otros vuelos
        todos_los_vuelos = results.get("best_flights", []) + results.get("other_flights", [])
        vuelos_limpios = []

        # Procesar y estructurar los datos
        for item in todos_los_vuelos:
            trayectos = item.get("flights", [])
            if not trayectos:
                continue
                
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
            emisiones = item.get("carbon_emissions", {}).get("this_flight")
            
            vuelos_limpios.append({
                "Aerolínea": aerolineas,
                "Precio (€)": item.get("price"),
                "Origen": salida_aeropuerto,
                "Fecha Salida": fecha_salida,
                "Hora Salida": hora_salida,
                "Destino": llegada_aeropuerto,
                "Fecha Llegada": fecha_llegada,
                "Hora Llegada": hora_llegada,
                "Tipo": escala_str,
                "Emisión CO2 (g)": emisiones
            })

        # Mostrar la tabla interactiva en la app
        if vuelos_limpios:
            df_vuelos = pd.DataFrame(vuelos_limpios)
            df_vuelos = df_vuelos.sort_values(by="Precio (€)").reset_index(drop=True)
            st.dataframe(df_vuelos)
        else:
            st.warning("No se encontraron vuelos o hubo un problema con la búsqueda.")
