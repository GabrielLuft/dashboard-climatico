
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
from scipy.interpolate import griddata
import math
import requests

# ------------------- CONFIGURAÇÕES INICIAIS -------------------
st.set_page_config(
    page_title="🌐 AgriClim Dashboard Futurista",
    layout="wide",
    page_icon="🌾",
)

st.markdown(
    "<h1 style='text-align: center; color: #00ffcc;'>🌐 AgriClim: Painel Climático Avançado para a Fruticultura</h1>",
    unsafe_allow_html=True
)

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA/export?format=csv&gid="

ESTACOES = {
    "Bento Gonçalves": {"gid": "1136868112", "lat": -29.1667, "lon": -51.5167},
    "Caxias do Sul": {"gid": "1948457634", "lat": -29.1683, "lon": -51.1794},
    "Garibaldi": {"gid": "651276718", "lat": -29.2597, "lon": -51.5356},
    "Farroupilha": {"gid": "1776247071", "lat": -29.2228, "lon": -51.3417}
}

@st.cache_data
def carregar_dados():
    dados = []
    for estacao, info in ESTACOES.items():
        try:
            url = GOOGLE_SHEET_URL + info["gid"]
            df = pd.read_csv(url)
            df["Estacao"] = estacao
            df["Latitude"] = info["lat"]
            df["Longitude"] = info["lon"]
            df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors='coerce')
            df["Hora"] = pd.to_datetime(df["Hora"], format="%H:%M:%S", errors="coerce").dt.time
            dados.append(df)
        except Exception as e:
            st.warning(f"Erro ao carregar {estacao}: {e}")
    return pd.concat(dados, ignore_index=True)

df = carregar_dados()

# ------------------- FILTROS -------------------
st.sidebar.title("🎛️ Filtros Interativos")
estacoes_selecionadas = st.sidebar.multiselect("Selecione as Estações", list(ESTACOES.keys()))
variaveis = ["Temperatura", "Umidade", "Chuva", "Radiação"]
variaveis_selecionadas = st.sidebar.multiselect("Variáveis", variaveis)
data_min, data_max = df["Data"].min(), df["Data"].max()
data_inicio = st.sidebar.date_input("Data Início", value=None, min_value=data_min, max_value=data_max)
data_fim = st.sidebar.date_input("Data Fim", value=None, min_value=data_min, max_value=data_max)
media_movel = st.sidebar.slider("Média Móvel (em horas)", 1, 72, 24)

df_filtrado = df.copy()
if estacoes_selecionadas:
    df_filtrado = df_filtrado[df_filtrado["Estacao"].isin(estacoes_selecionadas)]
if data_inicio:
    df_filtrado = df_filtrado[df_filtrado["Data"] >= pd.to_datetime(data_inicio)]
if data_fim:
    df_filtrado = df_filtrado[df_filtrado["Data"] <= pd.to_datetime(data_fim)]

# ------------------- VISUALIZAÇÕES -------------------
st.markdown("### 📈 Séries Temporais com Média Móvel")
for var in variaveis_selecionadas:
    fig = px.line(df_filtrado, x="Data", y=var, color="Estacao", title=f"{var} ao longo do tempo")
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

# ------------------- CANDLESTICK -------------------
if "Temperatura" in variaveis_selecionadas:
    st.markdown("### 📊 Candlestick da Temperatura")
    df_candle = df_filtrado.groupby(["Data", "Estacao"])["Temperatura"].agg(["min", "max", "mean"]).reset_index()
    fig = go.Figure()
    for estacao in df_candle["Estacao"].unique():
        df_e = df_candle[df_candle["Estacao"] == estacao]
        fig.add_trace(go.Candlestick(
            x=df_e["Data"],
            open=df_e["mean"], high=df_e["max"],
            low=df_e["min"], close=df_e["mean"],
            name=estacao
        ))
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

# ------------------- INTERPOLAÇÃO -------------------
if len(estacoes_selecionadas) >= 3 and variaveis_selecionadas:
    st.markdown("### 🌐 Interpolação Espacial (Mapa Real com Gradiente)")
    ultima_data = df_filtrado["Data"].max()
    df_ultima = df_filtrado[df_filtrado["Data"] == ultima_data]
    for var in variaveis_selecionadas:
        points = df_ultima[["Latitude", "Longitude"]].values
        values = df_ultima[var].values
        grid_lat, grid_lon = np.mgrid[-29.4:-29.1:100j, -51.6:-51.1:100j]
        grid_z = griddata(points, values, (grid_lat, grid_lon), method='linear')
        fig = go.Figure(data=go.Heatmap(
            z=grid_z, x=grid_lon[0], y=grid_lat[:,0],
            colorscale='Viridis', colorbar_title=var))
        fig.update_layout(title=f"Interpolação - {var}", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("🔺 Para interpolação espacial, selecione ao menos 3 estações e uma variável.")

# ------------------- RADAR CHART -------------------
if estacoes_selecionadas and variaveis_selecionadas:
    st.markdown("### 🛰️ Radar Chart Comparativo")
    df_medias = df_filtrado.groupby("Estacao")[variaveis_selecionadas].mean().reset_index()
    fig = go.Figure()
    for _, row in df_medias.iterrows():
        fig.add_trace(go.Scatterpolar(
            r=row[variaveis_selecionadas].values,
            theta=variaveis_selecionadas,
            fill='toself',
            name=row["Estacao"]
        ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
