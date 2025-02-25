import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static

# 1) Hlavní funkce pro načtení dat
@st.cache_data
def load_data():
    # Sem bys vložil kód pro načtení CSV (např. s delimiterem atd.)
    df = pd.DataFrame({
        "Datum": pd.date_range("2023-01-01", periods=5, freq="D"),
        "SpeciesName": ["Kos", "Vrabec", "Vrabec", "Straka", "Kos"],
        "Počet": [1,2,4,3,2],
        "Místo pozorování": ["Park", "Střecha", "Zahrada", "Les", "Park"]
    })
    return df

df = load_data()

# Vytvoříme si tři záložky
tabs = st.tabs(["Filtry", "Grafy", "Mapa a Tabulka"])

# ---------------------------
# ZÁLOŽKA 1: FILTRY
# ---------------------------
with tabs[0]:
    st.header("Filtry")
    # Tady se nastaví filtry, např. výběr druhu:
    species_list = ["Vše"] + sorted(df["SpeciesName"].unique())
    selected_species = st.selectbox("Vyber druh ptáka:", species_list)
    
    # Tady by mohla být logika pro filtr podle data, aktivity atd.
    # ...
    
    # Výsledek: filtered_data
    if selected_species == "Vše":
        filtered_data = df
    else:
        filtered_data = df[df["SpeciesName"] == selected_species]

    # Protože budeme with tabs[1] a with tabs[2] potřebovat stejná "filtered_data",
    # můžeme si ho uložit třeba do st.session_state (pokud ho chceme předávat).
    st.session_state["filtered_data"] = filtered_data


# ---------------------------
# ZÁLOŽKA 2: GRAF
# ---------------------------
with tabs[1]:
    st.header("Grafy")

    # Načteme si data, která jsme vyfiltrovali v první záložce
    filtered_data = st.session_state.get("filtered_data", df)

    # Ukázkový graf (počet záznamů pro každý druh)
    if not filtered_data.empty:
        fig = px.bar(
            filtered_data["SpeciesName"].value_counts().reset_index(),
            x="index", y="SpeciesName",
            title="Počet pozorování jednotlivých druhů"
        )
        st.plotly_chart(fig)
    else:
        st.warning("Žádná data pro zobrazení grafu.")


# ---------------------------
# ZÁLOŽKA 3: MAPA a TABULKA
# ---------------------------
with tabs[2]:
    st.header("Mapa a Tabulka")

    filtered_data = st.session_state.get("filtered_data", df)

    # 1) Mapa (ukázka)
    # Např. napevno střed (v reálu by sis spočítal průměr souřadnic)
    fol_map = folium.Map(location=[49.8175, 15.4730], zoom_start=7)
    
    # Jen demonstrace bez reálných souřadnic:
    for _, row in filtered_data.iterrows():
        folium.Marker(
            location=[49.1, 15.3],
            popup=f"{row['Místo pozorování']}: {row['Počet']} jedinců"
        ).add_to(fol_map)

    folium_static(fol_map)

    # 2) Tabulka
    if not filtered_data.empty:
        st.dataframe(filtered_data)
    else:
        st.warning("Žádná data pro zobrazení v tabulce.")
