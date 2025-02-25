import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static
from folium.plugins import HeatMap
from datetime import datetime

# Cesta k souboru
import os

# Zajištění individuálního souboru CSV pro každého uživatele
if "file_path" not in st.session_state:
    st.session_state["file_path"] = "pozorovani.csv"

uploaded_file = st.file_uploader("Nahrajte soubor CSV", type=["csv"])

if uploaded_file is not None:
    file_path = uploaded_file
else:
    file_path = "pozorovani.csv"

# Načtení dat
@st.cache_data
def load_data(file):
    try:
        df = pd.read_csv(file, delimiter=';', encoding='utf-8-sig')
        if df.empty:
            st.error("Nahraný soubor je prázdný. Nahrajte platný CSV soubor.")
            st.stop()
    except pd.errors.EmptyDataError:
        st.error("Soubor je prázdný nebo neplatný. Nahrajte prosím platný CSV soubor.")
        st.stop()
    df.rename(columns={
        "Date": "Datum",
        "SiteName": "Místo pozorování",
        "CountMin": "Počet",
        "ItemLink": "Odkaz",
        "Latitude": "Zeměpisná šířka",
        "Longitude": "Zeměpisná délka"
    }, inplace=True)
    df["Datum"] = pd.to_datetime(df["Datum"], format='%Y-%m-%d', errors='coerce')
    df = df.reset_index(drop=True)  # Odstranění prvního sloupce s indexem
    df["Odkaz"] = df["Odkaz"].apply(lambda x: f'<a href="{x}" target="_blank">link</a>' if pd.notna(x) else "")
    df["Počet"].fillna(1, inplace=True)  # Nahrazení chybějících hodnot v Počet hodnotou 1
    df["Místo pozorování"].fillna("", inplace=True)  # Nahrazení NaN prázdným polem
    df["Počet"] = df["Počet"].astype(int)  # Převod na celá čísla
    return df

df = None
if uploaded_file is None and not os.path.exists("pozorovani.csv"):
    st.warning("Prosím nahrajte soubor CSV, než aplikace začne pracovat.")
    st.stop()

if uploaded_file is not None or os.path.exists("pozorovani.csv"): 
    df = load_data(file_path)

# Přidání filtrů na druh a datum
species_column = "SpeciesName"  # Název sloupce s druhy ptáků
species_list = ["Vyber", "Vše"]
if df is not None and not df.empty and species_column in df.columns:
    species_list += sorted(set(df[species_column].dropna().unique()))
selected_species = st.selectbox("Vyber druh ptáka:", species_list)

date_min = df["Datum"].min().date() if df is not None and not df.empty else datetime.today().date()
date_max = df["Datum"].max().date() if df is not None and not df.empty else datetime.today().date()

date_from = st.date_input("Datum od:", date_min, min_value=date_min, max_value=date_max)
date_to = st.date_input("Datum do:", date_max, min_value=date_min, max_value=date_max)

# Filtrování dat podle výběru
df_filtered = df[(df["Datum"].dt.date >= date_from) & (df["Datum"].dt.date <= date_to)]
if selected_species != "Vše" and selected_species != "Vyber":
    df_filtered = df_filtered[df_filtered[species_column] == selected_species]

# Mapa s heatmapou
st.write("### Heatmapa četnosti pozorování")
if not df_filtered.empty and df_filtered[['Zeměpisná šířka', 'Zeměpisná délka']].notna().all().all():
    map_center = [df_filtered["Zeměpisná šířka"].mean(), df_filtered["Zeměpisná délka"].mean()]
else:
    map_center = [49.8175, 15.4730]  # Výchozí souřadnice pro Českou republiku

m = folium.Map(location=map_center, zoom_start=6)
if not df_filtered.empty:
    heat_data = df_filtered.dropna(subset=["Zeměpisná šířka", "Zeměpisná délka", "Počet"])
    heat_data = heat_data.groupby(["Zeměpisná šířka", "Zeměpisná délka"])["Počet"].sum().reset_index()
    heatmap_layer = HeatMap(heat_data.values.tolist(), radius=10)
    m.add_child(heatmap_layer)

folium_static(m)

st.write("### Filtrovaná data")
st.write(df_filtered[["Datum", "Místo pozorování", "Počet", "Odkaz"]].to_html(escape=False), unsafe_allow_html=True)
