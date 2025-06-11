import streamlit as st
import pandas as pd
import altair as alt
import pydeck as pdk
from supabase import create_client, Client
from sklearn.linear_model import LinearRegression
import numpy as np
import plotly.express as px

# --- Configuração Supabase ---
url = "https://kyrfsylobmsdjlrrpful.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt5cmZzeWxvYm1zZGpscnJwZnVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUzNTY4MzEsImV4cCI6MjA2MDkzMjgzMX0.DkPGAw89OH6MPNnCvimfsVJICr5J9n9hcgdgF17cP34"
supabase: Client = create_client(url, key)



# --- Configuração da página ---
st.set_page_config(layout="wide", page_title="SIMPREDE", page_icon="🌍")

st.markdown("""
    <style>
        .title-container {
            text-align: center;
            line-height: 1.2;
            margin-bottom: 1.5em;
            padding: 1.5em;
            background-color: #f0f2f6;
            border-radius: 16px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.05);
        }

        .title-container h1 {
            margin-bottom: 0.2em;
            font-size: 2.8em;
            color: #003366;
        }

        .title-container h3 {
            margin: 0;
            font-weight: normal;
            color: #333;
        }

        .title-container .subtitle-small {
            margin-top: 0.5em;
            font-size: 1.1em;
            color: #000000;
        }

        hr {
            border: none;
            border-top: 1px solid #ccc;
            margin: 1em 0 2em 0;
        }
    </style>

    <div class="title-container">
        <h1>SIMPREDE</h1>
        <h3>Sistema Inteligente de Monitorização e Previsão de Desastres Naturais</h3>
        <div class="subtitle-small">Universidade Aberta</div>
    </div>
    <hr>
""", unsafe_allow_html=True)







# --- Carregamento de dados ---
@st.cache_data
def carregar_disasters():
    data = supabase.table("disasters").select("id, year, month, type, subtype, date").execute().data
    df = pd.DataFrame(data)
    df["type"] = df["type"].str.capitalize()
    df = df[df["type"].isin(["Flood", "Landslide"])]
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.dropna(subset=["year", "month", "date"])


@st.cache_data
def carregar_localizacoes_disasters():
    data = supabase.table("location").select("id, latitude, longitude, district, municipality").execute().data
    df = pd.DataFrame(data)
    return df.dropna(subset=["latitude", "longitude"])

@st.cache_data
def carregar_scraper():
    data = supabase.table("google_scraper_ocorrencias").select("id, type, year, month, latitude, longitude, district").execute().data
    df = pd.DataFrame(data)
    df["type"] = df["type"].str.capitalize()
    df = df[df["type"].isin(["Flood", "Landslide"])]
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    return df.dropna(subset=["year", "month", "latitude", "longitude"])



# --- Carregamento ---
df_disasters_raw = carregar_disasters()
df_loc_disasters = carregar_localizacoes_disasters()
df_scraper = carregar_scraper()
df_disasters = df_disasters_raw.groupby(["year", "month", "type"]).size().reset_index(name="ocorrencias")


# === Parte 1 ===
st.markdown("<h2 style='text-align: center;'>Ocorrências Históricas de Desastres</h2>", unsafe_allow_html=True)


# --- Agrupar dados históricos por mês/tipo ---
df_disasters = df_disasters_raw.groupby(["year", "month", "type"]).size().reset_index(name="ocorrencias")
df_disasters["date"] = pd.to_datetime(
    df_disasters["year"].astype(str) + "-" + df_disasters["month"].astype(str).str.zfill(2) + "-01"
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### Dados Históricos (por mês e tipo)")
    st.dataframe(df_disasters, use_container_width=True)

with col2:
    tipo_graf1 = st.radio("Selecionar tipo de desastre (gráfico):", ["Todos", "Flood", "Landslide"], horizontal=True, key="graf1")
    df_g1 = df_disasters.copy()
    if tipo_graf1 != "Todos":
        df_g1 = df_g1[df_g1["type"] == tipo_graf1]
    max_y = df_g1["ocorrencias"].max() if not df_g1.empty else 0
    chart_disasters = alt.Chart(df_g1).mark_line(point=True).encode(
        x=alt.X("date:T", title="Data"),
        y=alt.Y("ocorrencias:Q", scale=alt.Scale(domain=[0, max_y + 1])),
        color=alt.Color("type:N", legend=alt.Legend(orient="top"))
    ).properties(
        height=400,
        title="Evolução Mensal de Ocorrências Históricas"
    )
    st.altair_chart(chart_disasters, use_container_width=True)

with col3:
    tipo_mapa_1 = st.radio("Selecionar tipo de desastre (mapa):", ["Todos", "Flood", "Landslide"], horizontal=True, key="mapa1")
    df_merge1 = pd.merge(df_disasters_raw, df_loc_disasters, on="id")
    if tipo_mapa_1 != "Todos":
        df_merge1 = df_merge1[df_merge1["type"] == tipo_mapa_1]
    if not df_merge1.empty:
        st.pydeck_chart(pdk.Deck(
            initial_view_state=pdk.ViewState(
                latitude=df_merge1["latitude"].mean(),
                longitude=df_merge1["longitude"].mean(),
                zoom=5.0
            ),
            layers=[pdk.Layer(
                "ScatterplotLayer",
                data=df_merge1,
                get_position='[longitude, latitude]',
                get_radius=8000,
                get_color='[0, 0, 200, 160]',
                pickable=True
            )],
            map_style="mapbox://styles/mapbox/light-v9"
        ), height=400)
    else:
        st.warning("Sem dados de localização disponíveis.")


# === Parte 2 ===
st.markdown("<h2 style='text-align: center;'>Ocorrências Recentes (Fonte: Google Scraper)</h2>", unsafe_allow_html=True)



# ❗ Criar df_scraper_grouped ANTES de qualquer uso
df_scraper_grouped = df_scraper.groupby(["year", "month", "type"]).size().reset_index(name="ocorrencias")
df_scraper_grouped["data"] = pd.to_datetime(
    df_scraper_grouped["year"].astype(int).astype(str) + '-' +
    df_scraper_grouped["month"].astype(int).astype(str).str.zfill(2)
)

col4, col5, col6 = st.columns(3)

with col4:
    st.markdown("#### Dados Recentes (Scraper)")
    st.dataframe(df_scraper_grouped, use_container_width=True)



with col5:
    tipo_graf2 = st.radio("Selecionar tipo de desastre (gráfico):", ["Todos", "Flood", "Landslide"], horizontal=True, key="graf2")
    df_g2 = df_scraper_grouped.copy()
    if tipo_graf2 != "Todos":
        df_g2 = df_g2[df_g2["type"] == tipo_graf2]
    max_y2 = df_g2["ocorrencias"].max()
    chart_scraper = alt.Chart(df_g2).mark_line(point=True).encode(
        x=alt.X("data:T", title="Data"),
        y=alt.Y("ocorrencias:Q", scale=alt.Scale(domain=[0, max_y2 + 1])),
        color=alt.Color("type:N")
    ).properties(height=400, title="Ocorrências Recentes (Scraper)")
    st.altair_chart(chart_scraper, use_container_width=True)

with col6:
    tipo_mapa_2 = st.radio("Selecionar tipo de desastre (mapa):", ["Todos", "Flood", "Landslide"], horizontal=True, key="mapa2")
    df_map = df_scraper.copy()
    if tipo_mapa_2 != "Todos":
        df_map = df_map[df_map["type"] == tipo_mapa_2]
    if not df_map.empty:
        st.pydeck_chart(pdk.Deck(
            initial_view_state=pdk.ViewState(latitude=df_map["latitude"].mean(), longitude=df_map["longitude"].mean(), zoom=5.0),
            layers=[pdk.Layer("ScatterplotLayer", data=df_map, get_position='[longitude, latitude]', get_radius=8000, get_color='[0, 0, 200, 160]', pickable=True)],
            map_style="mapbox://styles/mapbox/light-v9"
        ), height=400)
    else:
        st.warning("Sem dados de localização disponíveis.")



# === Parte 3 ===
st.markdown("<h2 style='text-align: center;'>Previsão de Ocorrências para 2026</h2>", unsafe_allow_html=True)



# --- Criar previsões globais por tipo ---
previsoes = []
meses_futuros = pd.date_range(start="2026-01", end="2026-12", freq="MS")

for tipo in df_disasters["type"].unique():
    df_tipo = df_disasters[df_disasters["type"] == tipo]
    X = df_tipo[["year", "month"]]
    y = df_tipo["ocorrencias"]
    modelo = LinearRegression().fit(X, y)
    df_futuro = pd.DataFrame({"year": meses_futuros.year, "month": meses_futuros.month})
    y_pred = modelo.predict(df_futuro[["year", "month"]])
    for i, data in enumerate(meses_futuros):
        previsoes.append({
            "data": data,
            "year": data.year,
            "month": data.month,
            "type": tipo,
            "ocorrencias": max(0, round(y_pred[i]))
        })

df_prev = pd.DataFrame(previsoes)


# --- Criar previsões geográficas por município ---
df_completo = pd.merge(df_disasters_raw, df_loc_disasters, on="id").dropna(subset=["year", "month"])
df_historico_mun = df_completo.groupby(["year", "month", "type", "municipality", "latitude", "longitude"]).size().reset_index(name="ocorrencias")

previsoes_geo = []
for (municipio, tipo), grupo in df_historico_mun.groupby(["municipality", "type"]):
    if len(grupo["year"].unique()) >= 2:
        X = grupo[["year", "month"]]
        y = grupo["ocorrencias"]
        modelo = LinearRegression().fit(X, y)
        df_futuro = pd.DataFrame({"year": meses_futuros.year, "month": meses_futuros.month})
        y_pred = modelo.predict(df_futuro[["year", "month"]])
        for i, data in enumerate(meses_futuros):
            previsoes_geo.append({
                "data": data,
                "year": data.year,
                "month": data.month,
                "type": tipo,
                "municipality": municipio,
                "ocorrencias": max(0, round(y_pred[i])),
                "latitude": grupo["latitude"].iloc[0],
                "longitude": grupo["longitude"].iloc[0]
            })

df_previsao_mapa = pd.DataFrame(previsoes_geo)

# --- Layout das 3 colunas ---
col7, col8, col9 = st.columns(3)

with col7:
    st.markdown("#### Dados de Previsão (2026)")
    st.dataframe(df_prev, use_container_width=True)

with col8:
    tipo_graf3 = st.radio("Selecionar tipo de desastre (gráfico):", ["Todos", "Flood", "Landslide"], horizontal=True, key="graf3")
    df_g3 = df_prev.copy()
    if tipo_graf3 != "Todos":
        df_g3 = df_g3[df_g3["type"] == tipo_graf3]
    chart_prev = alt.Chart(df_g3).mark_line(point=True).encode(
        x=alt.X("data:T", title="Data"),
        y=alt.Y("ocorrencias:Q"),
        color=alt.Color("type:N", legend=alt.Legend(orient="top"))
    ).properties(
        height=400,
        title="Previsão de Ocorrências Futuras (2026)"
    )
    st.altair_chart(chart_prev, use_container_width=True)

with col9:
    tipo_prev_mapa = st.radio("Selecionar tipo de desastre (mapa):", ["Todos", "Flood", "Landslide"], horizontal=True, key="mapa_previsao")
    df_prev_vis = df_previsao_mapa if tipo_prev_mapa == "Todos" else df_previsao_mapa[df_previsao_mapa["type"] == tipo_prev_mapa]
    if not df_prev_vis.empty:
        st.pydeck_chart(pdk.Deck(
            initial_view_state=pdk.ViewState(
                latitude=df_prev_vis["latitude"].mean(),
                longitude=df_prev_vis["longitude"].mean(),
                zoom=5.0
            ),
            layers=[pdk.Layer(
                "HeatmapLayer",
                data=df_prev_vis,
                get_position='[longitude, latitude]',
                get_weight='ocorrencias',
                aggregation="SUM",
                pickable=True
            )],
            map_style="mapbox://styles/mapbox/light-v9"
        ), height=400)
    else:
        st.warning("Sem dados de previsão geográfica disponíveis.")


# Rodapé
st.markdown("---")
st.caption("Projeto de Engenharia Informática<br>Autores: Luis Fernandes, Nuno Figueiredo, Paulo Couto, Rui Carvalho.", unsafe_allow_html=True)

