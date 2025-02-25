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

# ------------------
# Checkboxy pro zobrazení / skrytí grafů (nahoře na stránce)
# ------------------
show_bar_yearly = st.checkbox("Zobrazit graf: Počet pozorovaných druhů v jednotlivých letech", value=True)
show_bar_species_yearly = st.checkbox("Zobrazit graf: Počet pozorování vybraného druhu v jednotlivých letech", value=True)
show_pie_top_species = st.checkbox("Zobrazit koláčový graf nejčastějších druhů", value=True)
show_bar_monthly_obs = st.checkbox("Zobrazit graf počtu pozorování podle měsíců", value=True)
show_bar_monthly_count = st.checkbox("Zobrazit graf počtu jedinců podle měsíců", value=True)

# Přidání filtrů na druh a datum
species_column = "SpeciesName"
species_list = ["Vyber", "Vše"]
if df is not None and not df.empty and species_column in df.columns:
    species_list += sorted(set(df[species_column].dropna().unique()))
if df is not None and not df.empty and species_column in df.columns:
    species_list = ["Vyber", "Vše"] + sorted(df[species_column].dropna().unique())
if df is not None and not df.empty and species_column in df.columns:
    species_list = ["Vyber", "Vše"] + sorted(set(df[species_column].dropna().unique()))
selected_species = st.selectbox("Vyber druh ptáka:", species_list)

date_min = df["Datum"].min().date() if df is not None and not df.empty else datetime.today().date()
date_max = df["Datum"].max().date() if df is not None and not df.empty else datetime.today().date()

# Výběr roku nebo konkrétního rozsahu datumů
years = sorted(df["Datum"].dropna().dt.year.unique()) if df is not None and not df.empty else []
selected_year = st.selectbox("Vyberte rok:", ["Vlastní rozsah"] + years)

if selected_year == "Vlastní rozsah":
    date_from = st.date_input("Datum od:", date_min, min_value=date_min, max_value=date_max)
    date_to = st.date_input("Datum do:", date_max, min_value=date_min, max_value=date_max)
else:
    date_from = datetime(selected_year, 1, 1).date()
    date_to = datetime(selected_year, 12, 31).date()

# Filtr na druh ptáka
if selected_species == "Vyber":
    filtered_data = pd.DataFrame(columns=df.columns)
elif selected_species == "Vše":
    filtered_data = df[(df["Datum"].dt.date >= date_from) & (df["Datum"].dt.date <= date_to)]
else:
    filtered_data = df[(df[species_column] == selected_species) & (df["Datum"].dt.date >= date_from) & (df["Datum"].dt.date <= date_to)]

# ------------------
# GRAF 1: Počet pozorovaných druhů v jednotlivých letech
# ------------------
if df is not None and not df.empty:
    yearly_counts = df.groupby(df["Datum"].dt.year)[species_column].nunique().reset_index()
else:
    yearly_counts = pd.DataFrame(columns=["Datum", "Počet druhů"])
yearly_counts.rename(columns={"Datum": "Rok", species_column: "Počet druhů"}, inplace=True)
fig_yearly = px.bar(yearly_counts, x="Rok", y="Počet druhů", title="Celkový počet pozorovaných druhů podle roku", color_discrete_sequence=["green"])

if show_bar_yearly:
    st.write("### Počet pozorovaných druhů v jednotlivých letech")
    st.plotly_chart(fig_yearly)

# ------------------
# GRAF 2: Počet pozorování vybraného druhu v jednotlivých letech
# ------------------
years_df = pd.DataFrame({"Rok": years})
if selected_species not in ["Vyber", "Vše"]:
    yearly_species_counts = df[df[species_column] == selected_species].groupby(df["Datum"].dt.year).size().reset_index(name="Počet pozorování")
    yearly_species_counts = years_df.merge(yearly_species_counts, left_on="Rok", right_on="Datum", how="left").fillna(0)
    yearly_species_counts["Počet pozorování"] = yearly_species_counts["Počet pozorování"].astype(int)
    fig_species_yearly = px.bar(yearly_species_counts, x="Rok", y="Počet pozorování", title=f"Počet pozorování druhu {selected_species} podle roku", color_discrete_sequence=["purple"])
    fig_species_yearly.update_yaxes(dtick=max(1, yearly_species_counts["Počet pozorování"].max() // 5))
    if show_bar_species_yearly:
        st.write(f"### Počet pozorování druhu {selected_species} v jednotlivých letech")
        st.plotly_chart(fig_species_yearly)

# ------------------
# GRAF 3: 10 nejčastěji pozorovaných druhů (koláč)
# ------------------
filtered_pie_data = df[(df["Datum"].dt.date >= date_from) & (df["Datum"].dt.date <= date_to)]
top_species = filtered_pie_data[species_column].value_counts().nlargest(10).reset_index()
top_species["Druh"] = top_species.apply(lambda row: f"{row['Druh']} (" + str(row['Počet pozorování']) + ")", axis=1)
