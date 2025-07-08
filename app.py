import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from scipy.interpolate import griddata
import pydeck as pdk

# === Configuração inicial ===
st.set_page_config(layout="wide", page_title="🌎 AgroDashboard | Clima Inteligente")

st.markdown(
    """
    <style>
        body {
            background-color: #0d1117;
            color: #c9d1d9;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3 {
            color: #58a6ff;
        }
        .css-1d391kg {
            background-color: #161b22;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# === Função para carregar dados das abas (estações) ===
@st.cache_data
def carregar_estacoes():
    estacoes = {
        "Bento Gonçalves": "https://docs.google.com/spreadsheets/d/1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA/export?format=csv&gid=1136868112",
        "Caxias do Sul": "https://docs.google.com/spreadsheets/d/1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA/export?format=csv&gid=1948457634",
        "Garibaldi": "https://docs.google.com/spreadsheets/d/1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA/export?format=csv&gid=651276718",
        "Farroupilha": "https://docs.google.com/spreadsheets/d/1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA/export?format=csv&gid=1776247071"
    }

    coordenadas = {
        "Bento Gonçalves": (-29.1667, -51.5167),
        "Caxias do Sul": (-29.1629, -51.1794),
        "Garibaldi": (-29.2597, -51.5350),
        "Farroupilha": (-29.2225, -51.3411)
    }

    dados = []
    for cidade, url in estacoes.items():
        try:
            df = pd.read_csv(url)
            df["Estacao"] = cidade
            df["Lat"] = coordenadas[cidade][0]
            df["Lon"] = coordenadas[cidade][1]
            df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
            df["Hora"] = pd.to_datetime(df["Hora"], format="%H:%M:%S", errors="coerce").dt.time
            dados.append(df)
        except Exception as e:
            st.warning(f"Erro ao carregar {cidade}: {e}")
    return pd.concat(dados, ignore_index=True)

# === Carregar os dados ===
df = carregar_estacoes()

# === Sidebar ===
with st.sidebar:
    st.image("https://img.icons8.com/external-flaticons-flat-flat-icons/512/external-climate-sustainability-flaticons-flat-flat-icons.png", width=150)
    st.title("Painel Agroclimático 🌾")
    estacoes_sel = st.multiselect("Selecione as Estações", options=sorted(df["Estacao"].unique()))
    variaveis_sel = st.multiselect("Variáveis", ["Temperatura", "Umidade", "Chuva", "Radiação"])
    data_ini = st.date_input("Data Início", df["Data"].min().date())
    data_fim = st.date_input("Data Fim", df["Data"].max().date())
    media_movel = st.slider("Média Móvel (horas)", 1, 48, 6)

# === Filtrar os dados ===
df_filtrado = df[
    (df["Estacao"].isin(estacoes_sel)) &
    (df["Data"] >= pd.to_datetime(data_ini)) &
    (df["Data"] <= pd.to_datetime(data_fim))
].copy()

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para o filtro selecionado.")
    st.stop()

# === Gráficos Temporais ===
st.markdown("## 📈 Séries Temporais com Média Móvel")

for var in variaveis_sel:
    fig = px.line()
    for est in estacoes_sel:
        df_est = df_filtrado[df_filtrado["Estacao"] == est]
        df_est["MediaMovel"] = df_est[var].rolling(media_movel).mean()
        fig.add_scatter(x=df_est["Data"], y=df_est["MediaMovel"], mode="lines", name=f"{est} - {var}")
    fig.update_layout(
        template="plotly_dark", 
        height=400,
        title=f"{var} | Média Móvel: {media_movel}h"
    )
    st.plotly_chart(fig, use_container_width=True)

# === Boxplot Personalizado ===
st.markdown("## 📊 Distribuição Estatística (Boxplot)")
intervalo = st.radio("Intervalo", ["Dia", "Semana", "Mês"], horizontal=True)

df_filtrado["Intervalo"] = df_filtrado["Data"].dt.to_period({
    "Dia": "D", "Semana": "W", "Mês": "M"
}[intervalo]).dt.start_time

for var in variaveis_sel:
    fig_box = px.box(df_filtrado, x="Estacao", y=var, color="Estacao", points="all", template="plotly_dark")
    fig_box.update_layout(title=f"{var} - Boxplot por {intervalo}")
    st.plotly_chart(fig_box, use_container_width=True)

# === Interpolação Espacial ===
if len(estacoes_sel) >= 3:
    st.markdown("## 🌐 Mapa de Calor Interpolado")

    for var in variaveis_sel:
        pontos = df_filtrado.dropna(subset=[var])[["Lat", "Lon", var]]
        grid_lat, grid_lon = np.mgrid[
            pontos["Lat"].min():pontos["Lat"].max():100j,
            pontos["Lon"].min():pontos["Lon"].max():100j
        ]
        grid_valores = griddata(
            pontos[["Lat", "Lon"]].values, 
            pontos[var].values, 
            (grid_lat, grid_lon), 
            method="linear"
        )

        fig_map = go.Figure(go.Contour(
            z=grid_valores,
            x=grid_lon[0], 
            y=grid_lat[:,0],
            colorscale="Viridis",
            contours_coloring="heatmap",
            colorbar_title=var
        ))
        fig_map.update_layout(
            title=f"Mapa Interpolado: {var}",
            height=500,
            template="plotly_dark"
        )
        st.plotly_chart(fig_map, use_container_width=True)
else:
    st.info("⚠️ Pelo menos 3 estações devem ser selecionadas para gerar o mapa interpolado.")

# === Gráfico 3D ===
st.markdown("## 🌐 Visualização 3D Avançada")
for var in variaveis_sel:
    fig3d = px.scatter_3d(df_filtrado, x="Data", y="Estacao", z=var, color="Estacao", template="plotly_dark")
    fig3d.update_layout(title=f"{var} - Visualização 3D", height=500)
    st.plotly_chart(fig3d, use_container_width=True)

# === Rodapé ===
st.markdown("---")
st.markdown("🛰️ Desenvolvido por Gabriel Luft | Projeto de monitoramento climático para agricultura de precisão.")
