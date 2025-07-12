# app.py
# Dashboard Climático Interativo - Streamlit + Google Sheets + Mapbox
# Desenvolvido por Gabriel Luft com suporte técnico do ChatGPT

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import folium
from streamlit_folium import folium_static
from datetime import datetime
from utils import (
    carregar_dados_estacoes,
    localizar_estacao_proxima,
    heatmap_temporal,
    radar_chart_comparativo,
    exportar_excel,
    mapa_interpolado,
    boxplot_temporal,
    espaguete_3d
)

# ========== CONFIGURAÇÕES INICIAIS ========== #
st.set_page_config(
    page_title="Dashboard Climático RS",
    layout="wide",
    page_icon="🌦️"
)

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("# 🌦️ Dashboard Climático do Rio Grande do Sul")
st.markdown("Visualização interativa e futurista dos dados meteorológicos registrados por estações automáticas.")

# ========== CARREGAMENTO DOS DADOS ========== #
with st.spinner("🔄 Carregando dados das estações..."):
    estacoes = carregar_dados_estacoes()

# ========== SIDEBAR: FILTROS ========== #
st.sidebar.title("🔧 Filtros")
st.sidebar.markdown("📍 Geolocalização (simulada para testes)")

lat_user = st.sidebar.number_input("Latitude", value=-29.16)
lon_user = st.sidebar.number_input("Longitude", value=-51.52)

# Coordenadas das estações
estacoes_coords = {
    "Garibaldi": (-29.2597, -51.5352),
    "Bento Gonçalves": (-29.1667, -51.5167),
    "Farroupilha": (-29.2222, -51.3419),
    "Monte Belo": (-29.1500, -51.6000)
}

estacao_proxima = localizar_estacao_proxima(lat_user, lon_user, estacoes_coords)
st.sidebar.success(f"📡 Estação mais próxima: {estacao_proxima}")

estacoes_nomes = list(estacoes.keys())
estacao_sel = st.sidebar.selectbox("Estação", estacoes_nomes, index=estacoes_nomes.index(estacao_proxima))

data_inicio = st.sidebar.date_input("Data inicial", datetime(2024, 1, 1))
data_fim = st.sidebar.date_input("Data final", datetime.today())

# ========== FILTRO DE DADOS ========== #
df = estacoes[estacao_sel]
df["Data"] = pd.to_datetime(df["Data"])
df_filtro = df[(df["Data"] >= pd.to_datetime(data_inicio)) & (df["Data"] <= pd.to_datetime(data_fim))].copy()

# ========== ABA PRINCIPAL ========== #
abas = st.tabs([
    "📈 Candlestick", 
    "🌡️ Heatmap", 
    "📊 Radar Comparativo", 
    "🧊 Boxplot Temporal", 
    "🌍 Mapa Interpolado", 
    "📉 Espaguete 3D", 
    "📤 Exportar Excel"
])

# ========== CANDLESTICK ========== #
with abas[0]:
    st.subheader("📈 Candlestick Climático (Temp Mín / Méd / Máx)")
    fig_candle = go.Figure(data=[
        go.Candlestick(
            x=df_filtro['Data'],
            open=df_filtro['Temp_Med'],
            high=df_filtro['Temp_Max'],
            low=df_filtro['Temp_Min'],
            close=df_filtro['Temp_Med'],
            increasing_line_color='red',
            decreasing_line_color='blue'
        )
    ])
    fig_candle.update_layout(height=400, margin=dict(t=30, b=30))
    st.plotly_chart(fig_candle, use_container_width=True)

# ========== HEATMAP ========== #
with abas[1]:
    st.subheader("🌡️ Heatmap Temporal por Hora e Dia")
    fig_heatmap = heatmap_temporal(df_filtro)
    st.plotly_chart(fig_heatmap, use_container_width=True)

# ========== RADAR CHART ========== #
with abas[2]:
    st.subheader("📊 Comparativo entre Estações (Radar Chart)")
    fig_radar = radar_chart_comparativo(estacoes)
    st.plotly_chart(fig_radar, use_container_width=True)

# ========== BOXPLOT ========== #
with abas[3]:
    st.subheader("🧊 Boxplot da Temperatura por Semana")
    fig_box = boxplot_temporal(df_filtro)
    st.plotly_chart(fig_box, use_container_width=True)

# ========== MAPA INTERPOLADO ========== #
with abas[4]:
    st.subheader("🌍 Interpolação Térmica (Mapbox/Folium)")
    mapa = mapa_interpolado(estacoes_coords, estacoes)
    folium_static(mapa)

# ========== ESPAGUETE 3D ========== #
with abas[5]:
    st.subheader("📉 Espaguete 3D das Temperaturas")
    fig_3d = espaguete_3d(df_filtro)
    st.plotly_chart(fig_3d, use_container_width=True)

# ========== EXPORTAÇÃO PARA EXCEL ========== #
with abas[6]:
    st.subheader("📤 Exportar Dados Filtrados")
    excel_data = exportar_excel(df_filtro)
    st.download_button(
        label="📥 Baixar Excel",
        data=excel_data,
        file_name=f"Dados_{estacao_sel}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ========== RODAPÉ ========== #
st.markdown("---")
st.markdown("Aplicativo desenvolvido com ❤️ por Gabriel Luft • Dados meteorológicos via Google Sheets • Visualizações com Plotly e Folium.")
