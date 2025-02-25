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
    df = df.reset_index(drop=True)
    df["Odkaz"] = df["Odkaz"].apply(lambda x: f'<a href="{x}" target="_blank">link</a>' if pd.notna(x) else "")
    df["Počet"].fillna(1, inplace=True)
    df["Místo pozorování"].fillna("", inplace=True)
    df["Počet"] = df["Počet"].astype(int)
    return df

df = None
if uploaded_file is None and not os.path.exists("pozorovani.csv"):
    st.warning("Prosím nahrajte soubor CSV, než aplikace začne pracovat.")
    st.stop()

if uploaded_file is not None or os.path.exists("pozorovani.csv"): 
    df = load_data(file_path)

# Přidání filtrů na druh a datum
species_column = "SpeciesName"
species_list = ["Vyber", "Vše"]
if df is not None and not df.empty and species_column in df.columns:
    species_list += sorted(set(df[species_column].dropna().unique()))
selected_species = st.selectbox("Vyber druh ptáka:", species_list)

date_min = df["Datum"].min().date() if df is not None and not df.empty else datetime.today().date()
date_max = df["Datum"].max().date() if df is not None and not df.empty else datetime.today().date()

date_from = st.date_input("Datum od:", date_min, min_value=date_min, max_value=date_max)
date_to = st.date_input("Datum do:", date_max, min_value=date_min, max_value=date_max)

df_filtered = df[(df["Datum"].dt.date >= date_from) & (df["Datum"].dt.date <= date_to)]
if selected_species != "Vše" and selected_species != "Vyber":
    df_filtered = df_filtered[df_filtered[species_column] == selected_species]

# Heatmapa četnosti pozorování
st.write("### Heatmapa četnosti pozorování")
map_center = [df_filtered["Zeměpisná šířka"].mean(), df_filtered["Zeměpisná délka"].mean()] if not df_filtered.empty else [49.8175, 15.4730]
m_heatmap = folium.Map(location=map_center, zoom_start=6)
if not df_filtered.empty:
    heat_data = df_filtered.dropna(subset=["Zeměpisná šířka", "Zeměpisná délka", "Počet"])
    heat_data = heat_data.groupby(["Zeměpisná šířka", "Zeměpisná délka"])["Počet"].sum().reset_index()
    HeatMap(heat_data.values.tolist(), radius=10).add_to(m_heatmap)
folium_static(m_heatmap)

# Mapa s jednotlivými pozorováními
st.write("### Mapa jednotlivých pozorování")
m_markers = folium.Map(location=map_center, zoom_start=6)
if not df_filtered.empty:
    for _, row in df_filtered.iterrows():
        folium.Marker(
            location=[row["Zeměpisná šířka"], row["Zeměpisná délka"]],
            popup=f"{row['Místo pozorování']} ({row['Počet']} jedinců)",
        ).add_to(m_markers)
folium_static(m_markers)

# Obnovení všech původních grafů
st.write("### Počet pozorovaných druhů v jednotlivých letech")
yearly_counts = df.groupby(df["Datum"].dt.year)[species_column].nunique().reset_index()
yearly_counts.rename(columns={"Datum": "Rok", species_column: "Počet druhů"}, inplace=True)
fig_yearly = px.bar(yearly_counts, x="Rok", y="Počet druhů", title="Celkový počet pozorovaných druhů podle roku")
st.plotly_chart(fig_yearly)

st.write("### 10 nejčastěji pozorovaných druhů")
top_species = df[species_column].value_counts().nlargest(10).reset_index()
top_species.columns = ["Druh", "Počet pozorování"]
fig_pie = px.pie(top_species, names="Druh", values="Počet pozorování", title="Podíl 10 nejčastějších druhů", hole=0.3)
st.plotly_chart(fig_pie)
