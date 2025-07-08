import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from scipy.interpolate import griddata
import numpy as np

st.set_page_config(layout="wide", page_title="Dashboard Climático Vitícola", page_icon="🌱")

st.markdown("<h1 style='text-align: center; color: #6DD5FA;'>🌿 DASHBOARD CLIMÁTICO PARA VITICULTURA 🌿</h1>", unsafe_allow_html=True)

@st.cache_data
def carregar_dados():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR9AdILQ93f2IDMadcvHS5SK29o3fanNPDUrMA-QkV55XyrBmr8TdoFtu6h58FtSRrLFVupUmO5DrrG/pubhtml"
    xls = pd.ExcelFile(url)
    dados = {}
    for nome in xls.sheet_names:
        df = xls.parse(nome)
        if 'Data' in df.columns and 'Hora' in df.columns:
            df['Data_Hora'] = pd.to_datetime(df['Data'].astype(str) + ' ' + df['Hora'].astype(str), errors='coerce')
            df['Estação'] = nome
            df = df.dropna(subset=['Data_Hora'])
            dados[nome] = df
    return pd.concat(dados.values(), ignore_index=True)

df = carregar_dados()

# Filtros
with st.sidebar:
    st.markdown("### ⏱️ Intervalo de Visualização")
    data_min = df['Data_Hora'].min().date()
    data_max = df['Data_Hora'].max().date()
    data_inicio = st.date_input("Data Início", data_min, min_value=data_min, max_value=data_max)
    data_fim = st.date_input("Data Fim", data_max, min_value=data_min, max_value=data_max)
    janela_media = st.slider("🧮 Janela da Média Móvel (dias)", 1, 30, 7)

    st.markdown("### 🛰️ Estações")
    estacoes = st.multiselect("Selecione as Estações", df['Estação'].unique(), default=[])

    st.markdown("### 📈 Variáveis")
    variaveis = st.multiselect("Selecione as Variáveis", ['Temperatura', 'Umidade', 'Chuva', 'Radiação'], default=[])

# Filtro principal
df_filtrado = df[
    (df['Data_Hora'].dt.date >= data_inicio) &
    (df['Data_Hora'].dt.date <= data_fim)
]
if estacoes:
    df_filtrado = df_filtrado[df_filtrado['Estação'].isin(estacoes)]
if variaveis:
    st.markdown("## 📊 Análise Temporal das Variáveis Selecionadas")
    for var in variaveis:
        fig = px.line(df_filtrado, x='Data_Hora', y=var, color='Estação', title=f'{var} ao Longo do Tempo')
        fig.update_traces(mode='lines+markers')
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("## 📦 Boxplot por Estação")
    for var in variaveis:
        fig_box = px.box(df_filtrado, x='Estação', y=var, points="all", title=f'Distribuição de {var}')
        st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("## 🗺️ Interpolação Espacial das Estações (Temperatura)")
    coordenadas = {
        'Bento Gonçalves': (-29.165, -51.518),
        'Caxias do Sul': (-29.168, -51.179),
        'Garibaldi': (-29.256, -51.535),
        'Farroupilha': (-29.223, -51.341)
    }

    pontos = []
    valores = []
    for est in estacoes:
        if est in coordenadas:
            lat, lon = coordenadas[est]
            df_est = df_filtrado[df_filtrado['Estação'] == est]
            if not df_est.empty:
                media = df_est['Temperatura'].mean()
                pontos.append((lat, lon))
                valores.append(media)

    if len(pontos) >= 3:
        latitudes, longitudes = zip(*pontos)
        grid_lat, grid_lon = np.mgrid[min(latitudes):max(latitudes):100j, min(longitudes):max(longitudes):100j]
        grid_temp = griddata(pontos, valores, (grid_lat, grid_lon), method='cubic')

        fig_mapa = go.Figure(data=go.Contour(
            z=grid_temp,
            x=grid_lon[0], y=grid_lat[:,0],
            colorscale='Viridis',
            contours_coloring='heatmap'
        ))
        fig_mapa.update_layout(title='Mapa de Calor Interpolado - Temperatura')
        st.plotly_chart(fig_mapa, use_container_width=True)
    else:
        st.warning("Selecione pelo menos 3 estações para gerar a interpolação espacial.")

else:
    st.info("👈 Selecione estações e variáveis para visualizar os dados.")