# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from scipy.interpolate import griddata
import pydeck as pdk
import requests
import io

st.set_page_config(
    page_title="🌐 AgriClim – Painel Climático Avançado",
    layout="wide",
    page_icon="🌍"
)

# -----------------------------
# CONFIGURAÇÕES INICIAIS
# -----------------------------
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
    }
    .css-18e3th9 {
        padding: 1rem;
        background: #0f2027;  /* fallback for old browsers */
        background: linear-gradient(to right, #2c5364, #203a43, #0f2027);
        color: white;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #F4F4F4;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌐 AgriClim – Painel Climático para Viticultura Avançada")

# -----------------------------
# CONFIG: DADOS
# -----------------------------
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxNAGwHYvJqCBfWf-x5TWCGdNQ_wkZkA5jIYTw7kYfAIsEP8brvnEtAjFJjGJXkZMJ7kXNbdYItkTH/pub?output=xlsx"

@st.cache_data
def carregar_dados():
    response = requests.get(GOOGLE_SHEET_URL)
    if response.status_code != 200:
        st.error("Erro ao carregar a planilha do Google Sheets")
        return {}
    xls = pd.ExcelFile(io.BytesIO(response.content))
    dados = {}
    for nome in xls.sheet_names:
        df = xls.parse(nome)
        if {'Data', 'Hora', 'Umidade', 'Temperatura', 'Chuva', 'Radiação'}.issubset(df.columns):
            df['Data_Hora'] = pd.to_datetime(df['Data'].astype(str) + ' ' + df['Hora'].astype(str), errors='coerce')
            df = df.dropna(subset=['Data_Hora'])
            df['Estacao'] = nome
            dados[nome] = df
    return dados

dados_por_estacao = carregar_dados()

# -----------------------------
# SELEÇÃO DE PARÂMETROS
# -----------------------------
estacoes = list(dados_por_estacao.keys())
estacoes_selecionadas = st.sidebar.multiselect("🌐 Estações meteorológicas:", estacoes, default=[])
variaveis_selecionadas = st.sidebar.multiselect("📊 Variáveis climáticas:", ['Temperatura', 'Umidade', 'Chuva', 'Radiação'], default=[])

st.sidebar.markdown("---")

data_min = min(df['Data_Hora'].min() for df in dados_por_estacao.values())
data_max = max(df['Data_Hora'].max() for df in dados_por_estacao.values())
data_inicio = st.sidebar.date_input("🕒 Início:", data_min.date(), min_value=data_min.date(), max_value=data_max.date())
data_fim = st.sidebar.date_input("🕒 Fim:", data_max.date(), min_value=data_min.date(), max_value=data_max.date())

media_movel = st.sidebar.slider("📈 Média móvel (horas):", 1, 48, 3)

# -----------------------------
# DADOS FILTRADOS E GRÁFICOS
# -----------------------------
@st.cache_data
def filtrar_dados():
    df_geral = pd.concat(dados_por_estacao[est] for est in estacoes_selecionadas)
    df_geral = df_geral[(df_geral['Data_Hora'] >= pd.to_datetime(data_inicio)) &
                        (df_geral['Data_Hora'] <= pd.to_datetime(data_fim))]
    df_geral = df_geral.sort_values('Data_Hora')
    df_geral.set_index('Data_Hora', inplace=True)
    for var in variaveis_selecionadas:
        df_geral[f"{var}_MM"] = df_geral.groupby('Estacao')[var].transform(lambda x: x.rolling(media_movel).mean())
    df_geral.reset_index(inplace=True)
    return df_geral

if estacoes_selecionadas and variaveis_selecionadas:
    df = filtrar_dados()

    st.subheader("🌇 Séries Temporais com Média Móvel")
    for var in variaveis_selecionadas:
        fig = px.line(df, x='Data_Hora', y=f"{var}_MM", color='Estacao', title=f"{var} (média móvel)")
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("🌤️ Interpolação Espacial sobre Mapa")
    coordenadas = {
        "Bento Gonçalves": (-29.1667, -51.5167),
        "Caxias do Sul": (-29.1681, -51.1794),
        "Garibaldi": (-29.2583, -51.5333),
        "Farroupilha": (-29.2222, -51.3417),
    }
    pontos = []
    for est in estacoes_selecionadas:
        if est in coordenadas:
            lat, lon = coordenadas[est]
            df_est = df[df['Estacao'] == est]
            valor = df_est[variaveis_selecionadas[0]].mean()
            pontos.append((lat, lon, valor))

    if len(pontos) >= 3:
        lats, lons, values = zip(*pontos)
        grid_lat, grid_lon = np.meshgrid(
            np.linspace(min(lats), max(lats), 50),
            np.linspace(min(lons), max(lons), 50)
        )
        grid_z = griddata((lats, lons), values, (grid_lat, grid_lon), method='cubic')
        fig_map = go.Figure(go.Contour(
            z=grid_z,
            x=grid_lon[0],
            y=grid_lat[:,0],
            colorscale='Viridis',
            contours_coloring='heatmap',
            colorbar_title=variaveis_selecionadas[0]
        ))
        fig_map.update_layout(
            title="Mapa Interpolado",
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            height=500,
            template="plotly_dark"
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("Para o gráfico de mapa interpolado é necessário selecionar no mínimo 3 estações.")

    st.subheader("🌧️ Boxplot Personalizado")
    intervalo = st.selectbox("Intervalo:", ['Dia', 'Semana', 'Mês'])
    df['Intervalo'] = df['Data_Hora'].dt.to_period(intervalo[0]).astype(str)

    for var in variaveis_selecionadas:
        fig_box = px.box(df, x='Intervalo', y=var, color='Estacao', title=f"Boxplot de {var} por {intervalo.lower()}")
        fig_box.update_layout(template="plotly_dark")
        st.plotly_chart(fig_box, use_container_width=True)

else:
    st.warning("Por favor, selecione ao menos uma estação e uma variável para iniciar a visualização.")
