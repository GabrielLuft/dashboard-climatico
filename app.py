
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from scipy.interpolate import griddata
import urllib.request

st.set_page_config(page_title="🌐 AgriClim: Painel Climático Avançado", layout="wide")

st.markdown("""
    <style>
    h1, h2, h3, h4, h5, h6 {
        color: #00FFAA;
        font-family: 'Segoe UI', sans-serif;
    }
    .stApp {
        background: linear-gradient(145deg, #0a0f1c, #1c2230);
        color: #ffffff;
    }
    .block-container {
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🌐 AgriClim: Painel Climático para a Fruticultura de Precisão")

@st.cache_data
def carregar_dados():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTq6tpKNUY9gh5NENY9E1Iq_QHOtrKocgvUJ7snqV7fGwbSRQ1z6Ke7a5AgGiJH3Xk3Yq4_j4R6sbi_/pub?output=xlsx"
    xls = pd.ExcelFile(url)
    df_total = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        if 'Data' in df.columns:
            df['Estação'] = sheet
            df_total.append(df)
    return pd.concat(df_total, ignore_index=True)

df = carregar_dados()
df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
df = df.dropna(subset=['Data'])

st.sidebar.header("🎛️ Filtros")
estacoes = sorted(df['Estação'].unique())
variaveis = [col for col in df.columns if col not in ['Data', 'Estação']]

estacoes_sel = st.sidebar.multiselect("Selecionar Estações", estacoes)
variaveis_sel = st.sidebar.multiselect("Selecionar Variáveis", variaveis)
data_inicio = st.sidebar.date_input("Data Início", df['Data'].min().date())
data_fim = st.sidebar.date_input("Data Fim", df['Data'].max().date())
media_movel = st.sidebar.slider("Média Móvel (dias)", 1, 30, 7)

if estacoes_sel and variaveis_sel:
    df_filtrado = df[(df['Estação'].isin(estacoes_sel)) & 
                     (df['Data'].between(pd.to_datetime(data_inicio), pd.to_datetime(data_fim)))]

    st.subheader("📈 Séries Temporais com Média Móvel")
    for var in variaveis_sel:
        fig = px.line(df_filtrado, x='Data', y=df_filtrado[var].rolling(media_movel).mean(),
                      color='Estação', labels={"value": var}, title=f"Média Móvel de {var}")
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📊 Box Plot - Distribuição por Estação")
    for var in variaveis_sel:
        fig_box = px.box(df_filtrado, x="Estação", y=var, points="all", color="Estação", title=f"Distribuição de {var}")
        fig_box.update_layout(template="plotly_dark")
        st.plotly_chart(fig_box, use_container_width=True)

    if len(estacoes_sel) >= 3:
        st.subheader("🌡️ Interpolação de Calor (Mapa)")
        coords = {
            "Bento Gonçalves": (-29.1667, -51.5167),
            "Caxias do Sul": (-29.1667, -51.1833),
            "Garibaldi": (-29.2597, -51.5333),
            "Farroupilha": (-29.2225, -51.3478)
        }
        pontos = []
        for est in estacoes_sel:
            if est in coords:
                lat, lon = coords[est]
                media = df_filtrado[df_filtrado["Estação"] == est][variaveis_sel[0]].mean()
                pontos.append((lat, lon, media))
        if len(pontos) >= 3:
            lats, lons, values = zip(*pontos)
            grid_lat, grid_lon = np.mgrid[min(lats):max(lats):100j, min(lons):max(lons):100j]
            grid_val = griddata((lats, lons), values, (grid_lat, grid_lon), method="cubic")

            fig_map = go.Figure(data=go.Heatmap(z=grid_val, x=grid_lon[0], y=grid_lat[:,0], colorscale="Viridis"))
            fig_map.update_layout(title=f"Interpolação de {variaveis_sel[0]} nas Estações", template="plotly_dark")
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("🔔 Selecione pelo menos 3 estações com coordenadas para interpolar no mapa.")
else:
    st.warning("Por favor, selecione ao menos uma estação e uma variável.")
