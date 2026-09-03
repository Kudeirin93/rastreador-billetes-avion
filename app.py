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
        # Usar los secretos de Streamlit para la API Key
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

        # Aquí pegas exactamente el mismo código del bucle for 
        # que armamos antes para llenar la lista 'vuelos_limpios'
        # ... (código de limpieza) ...

        # Mostrar la tabla interactiva en la app
        st.dataframe(pd.DataFrame(vuelos_limpios))
