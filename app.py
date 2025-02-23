import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static
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

df = load_data(file_path)

# Přidání filtrů na druh a datum
species_column = "SpeciesName"  # Název sloupce s druhy ptáků
species_list = ["Vyber"] + ["Vše"] + sorted(df[species_column].unique())
selected_species = st.selectbox("Vyber druh ptáka:", species_list)

date_min = df["Datum"].min().date()
date_max = df["Datum"].max().date()

# Výběr roku nebo konkrétního rozsahu datumů
years = sorted(df["Datum"].dropna().dt.year.unique())
selected_year = st.selectbox("Vyberte rok:", ["Vlastní rozsah"] + years)

if selected_year == "Vlastní rozsah":
    date_from = st.date_input("Datum od:", date_min, min_value=date_min, max_value=date_max)
    date_to = st.date_input("Datum do:", date_max, min_value=date_min, max_value=date_max)
else:
    date_from = datetime(selected_year, 1, 1).date()
    date_to = datetime(selected_year, 12, 31).date()

# Přidání grafu s celkovým počtem pozorovaných druhů v každém roce
st.write("### Počet pozorovaných druhů v jednotlivých letech")
yearly_counts = df.groupby(df["Datum"].dt.year)[species_column].nunique().reset_index()
yearly_counts.rename(columns={"Datum": "Rok", species_column: "Počet druhů"}, inplace=True)
fig_yearly = px.bar(yearly_counts, x="Rok", y="Počet druhů", title="Celkový počet pozorovaných druhů podle roku", color_discrete_sequence=["green"])
st.plotly_chart(fig_yearly)

# Filtr na druh ptáka
if selected_species == "Vyber":
    filtered_data = pd.DataFrame(columns=df.columns)
elif selected_species == "Vše":
    filtered_data = df[(df["Datum"].dt.date >= date_from) & (df["Datum"].dt.date <= date_to)]
else:
    filtered_data = df[(df[species_column] == selected_species) & (df["Datum"].dt.date >= date_from) & (df["Datum"].dt.date <= date_to)]

# Přidání mapy s pozorováními
st.write("### Počet pozorování vybraného druhu v jednotlivých letech")
years_df = pd.DataFrame({"Rok": years})
if selected_species not in ["Vyber", "Vše"]:
    yearly_species_counts = df[df[species_column] == selected_species].groupby(df["Datum"].dt.year).size().reset_index(name="Počet pozorování")
    yearly_species_counts = years_df.merge(yearly_species_counts, left_on="Rok", right_on="Datum", how="left").fillna(0)
    yearly_species_counts["Počet pozorování"] = yearly_species_counts["Počet pozorování"].astype(int)
    fig_species_yearly = px.bar(yearly_species_counts, x="Rok", y="Počet pozorování", title=f"Počet pozorování druhu {selected_species} podle roku", color_discrete_sequence=["purple"])
    fig_species_yearly.update_yaxes(dtick=max(1, yearly_species_counts["Počet pozorování"].max() // 5))
    st.plotly_chart(fig_species_yearly)

st.write("### 10 nejčastěji pozorovaných druhů")
filtered_pie_data = df[(df["Datum"].dt.date >= date_from) & (df["Datum"].dt.date <= date_to)]
top_species = filtered_pie_data[species_column].value_counts().nlargest(10).reset_index()
top_species.columns = ["Druh", "Počet pozorování"]
fig_pie = px.pie(top_species, names="Druh", values="Počet pozorování", title="Podíl 10 nejčastějších druhů", hole=0.3)
st.plotly_chart(fig_pie)
st.write("#### Jmenovitý seznam 10 nejčastějších druhů")
st.write(top_species.to_html(index=False, escape=False), unsafe_allow_html=True)

st.write("### Mapa pozorování")
map_center = [df["Zeměpisná šířka"].mean(), df["Zeměpisná délka"].mean()]
m = folium.Map(location=map_center, zoom_start=6)

month_labels = {1: "Leden", 2: "Únor", 3: "Březen", 4: "Duben", 5: "Květen", 6: "Červen", 7: "Červenec", 8: "Srpen", 9: "Září", 10: "Říjen", 11: "Listopad", 12: "Prosinec"}
all_months = pd.DataFrame({"Měsíc": list(month_labels.values())})
if not filtered_data.empty:
    for _, row in filtered_data.iterrows():
        folium.Marker(
            location=[row["Zeměpisná šířka"], row["Zeměpisná délka"]],
            popup=f"{row['Místo pozorování']} ({row['Počet']} jedinců)",
        ).add_to(m)

folium_static(m)

# Přidání sloupcového grafu podle měsíců
month_labels = {1: "Leden", 2: "Únor", 3: "Březen", 4: "Duben", 5: "Květen", 6: "Červen", 7: "Červenec", 8: "Srpen", 9: "Září", 10: "Říjen", 11: "Listopad", 12: "Prosinec"}
if not filtered_data.empty:
    filtered_data["Měsíc"] = filtered_data["Datum"].dt.month.map(month_labels)
    monthly_counts = filtered_data.groupby("Měsíc").agg({"Počet": "sum", "Datum": "count"}).reset_index()
    monthly_counts.rename(columns={"Datum": "Počet pozorování", "Počet": "Počet jedinců"}, inplace=True)
    monthly_counts = all_months.merge(monthly_counts, on="Měsíc", how="left").fillna(0)
    monthly_counts["Počet pozorování"] = monthly_counts["Počet pozorování"].astype(int)
    monthly_counts["Počet jedinců"] = monthly_counts["Počet jedinců"].astype(int)
    monthly_counts.rename(columns={"Datum": "Počet pozorování", "Počet": "Počet jedinců"}, inplace=True)
    fig1 = px.bar(monthly_counts, x="Měsíc", y="Počet pozorování", title="Počet pozorování podle měsíců", color_discrete_sequence=["blue"])
    fig1.update_yaxes(dtick=max(1, monthly_counts["Počet pozorování"].max() // 5))
    st.plotly_chart(fig1)
    fig2 = px.bar(monthly_counts, x="Měsíc", y="Počet jedinců", title="Počet jedinců podle měsíců", color_discrete_sequence=["red"])
    fig2.update_yaxes(dtick=max(1, monthly_counts["Počet jedinců"].max() // 5))
    st.plotly_chart(fig2)

# Zobrazení filtrované tabulky
st.write(f"### Pozorování druhu: {selected_species}")
filtered_data_display = filtered_data.copy()
filtered_data_display["Počet"] = filtered_data_display["Počet"].apply(lambda x: 'x' if pd.isna(x) or x == '' else int(x))
filtered_data_display["Datum"] = filtered_data_display["Datum"].apply(lambda x: x.strftime('%d. %m. %Y') if pd.notna(x) else '')
st.write(filtered_data_display[["Datum", "Místo pozorování", "Počet", "Odkaz"]].to_html(escape=False), unsafe_allow_html=True)
