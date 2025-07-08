import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
from scipy.interpolate import griddata
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="🌦️ Painel Climático Fruticultura 4.0")

# ------------------- CONFIGURAÇÃO -------------------

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQy6eF8XUYkb6IM1Rk2uDGKqg3A4eLHzm2Z_H6v9aNBgVDqaXZcf_yb1xYBoFvh3Q/pub?output=xlsx"

COORDENADAS_ESTACOES = {
    "Bento Gonçalves": (-29.165, -51.518),
    "Caxias do Sul": (-29.167, -51.179),
    "Garibaldi": (-29.259, -51.534),
    "Farroupilha": (-29.223, -51.341)
}

# ------------------- FUNÇÕES -------------------

@st.cache_data(ttl=3600)
def carregar_dados():
    xls = pd.ExcelFile(GOOGLE_SHEET_URL)
    estacoes = {}
    for nome in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=nome)
        df = df.rename(columns=str.strip)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        df = df.dropna(subset=['Data'])
        df['Hora'] = pd.to_datetime(df['Hora'], format='%H:%M:%S', errors='coerce').dt.time
        df['Estação'] = nome
        estacoes[nome] = df
    return pd.concat(estacoes.values(), ignore_index=True)

df = carregar_dados()
variaveis_disponiveis = ['Temperatura', 'Umidade', 'Chuva', 'Radiação']

# ------------------- SIDEBAR -------------------

st.sidebar.title("🔎 Filtros")

estacoes_selecionadas = st.sidebar.multiselect("Estações", options=df['Estação'].unique(), default=[])
variaveis_selecionadas = st.sidebar.multiselect("Variáveis", options=variaveis_disponiveis, default=[])
data_inicio = st.sidebar.date_input("Data Início", value=df['Data'].min().date())
data_fim = st.sidebar.date_input("Data Fim", value=df['Data'].max().date())
media_movel = st.sidebar.slider("Média Móvel (horas)", 1, 48, 6)

# ------------------- FILTRO PRINCIPAL -------------------

df_filtrado = df.copy()

if estacoes_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['Estação'].isin(estacoes_selecionadas)]
if variaveis_selecionadas:
    df_filtrado = df_filtrado[[*['Data', 'Hora', 'Estação'], *variaveis_selecionadas]]
df_filtrado = df_filtrado[(df_filtrado['Data'] >= pd.to_datetime(data_inicio)) & (df_filtrado['Data'] <= pd.to_datetime(data_fim))]

# ------------------- HEADER -------------------

st.title("🌱 Painel Climático Inteligente para Fruticultura")
st.markdown("Análise técnica dos parâmetros meteorológicos em tempo real com inteligência visual para tomada de decisão.")

# ------------------- SÉRIE TEMPORAL -------------------

st.subheader("📊 Gráficos de Séries Temporais")
if not estacoes_selecionadas or not variaveis_selecionadas:
    st.warning("Selecione ao menos uma estação e uma variável para visualizar os gráficos.")
else:
    for var in variaveis_selecionadas:
        fig = px.line(df_filtrado, x='Data', y=var, color='Estação',
                      title=f"Série Temporal de {var}", template="plotly_dark")
        df_filtrado[f'{var}_MM'] = df_filtrado.groupby('Estação')[var].transform(lambda x: x.rolling(media_movel).mean())
        fig.add_scatter(x=df_filtrado['Data'], y=df_filtrado[f'{var}_MM'], mode='lines', name='Média Móvel')
        st.plotly_chart(fig, use_container_width=True)

# ------------------- BOXPLOT -------------------

st.subheader("🧪 Distribuição Estatística (Boxplot)")

intervalo_box = st.radio("Intervalo:", ["Dia", "Semana", "Mês"], horizontal=True)

df_box = df_filtrado.copy()
if intervalo_box == "Dia":
    df_box['Intervalo'] = df_box['Data'].dt.date
elif intervalo_box == "Semana":
    df_box['Intervalo'] = df_box['Data'].dt.to_period("W").apply(lambda r: r.start_time)
else:
    df_box['Intervalo'] = df_box['Data'].dt.to_period("M").apply(lambda r: r.start_time)

for var in variaveis_selecionadas:
    fig_box = px.box(df_box, x="Intervalo", y=var, color="Estação",
                     title=f"Boxplot de {var} por {intervalo_box}", template="plotly_dark")
    st.plotly_chart(fig_box, use_container_width=True)

# ------------------- INTERPOLAÇÃO EM MAPA -------------------

st.subheader("🗺️ Mapa com Interpolação Geográfica")

if len(estacoes_selecionadas) >= 3:
    ultima_data = df_filtrado['Data'].max()
    df_ultimas = df_filtrado[df_filtrado['Data'] == ultima_data].groupby('Estação').mean(numeric_only=True).reset_index()

    pontos = []
    for est in df_ultimas['Estação']:
        if est in COORDENADAS_ESTACOES:
            lat, lon = COORDENADAS_ESTACOES[est]
            pontos.append((lat, lon))
    if len(pontos) >= 3:
        lats, lons = zip(*pontos)
        for var in variaveis_selecionadas:
            fig_map = go.Figure(data=go.Scattergeo(
                lon=lons,
                lat=lats,
                text=df_ultimas[var].round(2),
                marker=dict(
                    size=18,
                    color=df_ultimas[var],
                    colorscale='YlOrRd',
                    showscale=True,
                    colorbar_title=var
                )
            ))
            fig_map.update_layout(
                geo_scope='south america',
                title=f"{var} Interpolado nas Estações (Última Data)",
                template='plotly_dark'
            )
            st.plotly_chart(fig_map, use_container_width=True)
else:
    st.info("Selecione ao menos 3 estações para visualizar o mapa interpolado.")

# ------------------- GRÁFICOS 3D -------------------

st.subheader("🔭 Visualização 3D Avançada")
for var in variaveis_selecionadas:
    fig_3d = px.scatter_3d(df_filtrado, x="Data", y="Estação", z=var,
                           color=var, title=f"{var} em 3D", template="plotly_dark")
    st.plotly_chart(fig_3d, use_container_width=True)

# ------------------- RODAPÉ -------------------

st.markdown("---")
st.markdown("📍 Desenvolvido por Gabriel Luft | Aplicação voltada ao monitoramento climático técnico para **Fruticultura de Precisão**.")

