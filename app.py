import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import time

st.set_page_config(page_title="🌦️ Dashboard Climático Multiestação", layout="wide")

# -------------------------------
# 📡 CONFIGURAÇÃO DA PLANILHA
# -------------------------------
SHEET_ID = "1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA"

GID_MAP = {
    "Bento Gonçalves": "1136868112",
    "Caxias do Sul": "1948457634",
    "Garibaldi": "651276718",
    "Farroupilha": "1776247071"
}

COORDS = {
    "Bento Gonçalves": (-29.1667, -51.5167),
    "Caxias do Sul": (-29.1668, -51.1794),
    "Garibaldi": (-29.2597, -51.5336),
    "Farroupilha": (-29.2222, -51.3475)
}

# -------------------------------
# 📥 FUNÇÃO DE CARGA DOS DADOS
# -------------------------------
@st.cache_data(ttl=600)
def load_all_stations(sheet_id, gid_map):
    dfs = []
    for estacao, gid in gid_map.items():
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        try:
            df = pd.read_csv(url)
            df['Estacao'] = estacao
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            df['Hora'] = pd.to_datetime(df['Hora'], format='%H:%M', errors='coerce').dt.time
            df['DataHora'] = pd.to_datetime(df['Data'].astype(str) + ' ' + df['Hora'].astype(str), errors='coerce')
            dfs.append(df.dropna(subset=['DataHora']))
        except Exception as e:
            st.warning(f"Erro ao carregar {estacao}: {e}")
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()

with st.spinner("🔄 Carregando dados das estações..."):
    df = load_all_stations(SHEET_ID, GID_MAP)

if df.empty:
    st.error("Nenhum dado encontrado. Verifique os GIDs ou o formato da planilha.")
    st.stop()

# -------------------------------
# 🎛️ SIDEBAR - FILTROS
# -------------------------------
st.sidebar.header("🎚️ Filtros")

estacoes = st.sidebar.multiselect("Selecionar Estações", list(GID_MAP.keys()), default=list(GID_MAP.keys()))
variaveis = ['Temperatura', 'Umidade', 'Chuva', 'Radiação']
vars_selecionadas = st.sidebar.multiselect("Variáveis", variaveis, default=['Temperatura', 'Umidade'])

data_min = df['Data'].min().date()
data_max = df['Data'].max().date()
data_inicio = st.sidebar.date_input("Data Início", data_min, min_value=data_min, max_value=data_max)
data_fim = st.sidebar.date_input("Data Fim", data_max, min_value=data_min, max_value=data_max)

hora_inicio = st.sidebar.slider("Hora Início", 0, 23, 0)
hora_fim = st.sidebar.slider("Hora Fim", 0, 23, 23)

hora_inicio_time = time(hora_inicio, 0)
hora_fim_time = time(hora_fim, 59)

df_filtrado = df[
    (df['Estacao'].isin(estacoes)) &
    (df['Data'] >= pd.to_datetime(data_inicio)) &
    (df['Data'] <= pd.to_datetime(data_fim)) &
    (df['Hora'] >= hora_inicio_time) &
    (df['Hora'] <= hora_fim_time)
]

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado com os filtros selecionados.")
    st.stop()

# -------------------------------
# 🧠 TÍTULO E MÉTRICAS
# -------------------------------
st.title("🌤️ Dashboard Climático da Serra Gaúcha")
st.caption("Atualizado automaticamente com dados da planilha do Google.")

with st.container():
    cols = st.columns(len(vars_selecionadas))
    for col, var in zip(cols, vars_selecionadas):
        media = df_filtrado[var].mean()
        minimo = df_filtrado[var].min()
        maximo = df_filtrado[var].max()
        col.metric(f"{var}", f"{media:.2f}", f"Min: {minimo:.1f} | Max: {maximo:.1f}")

# -------------------------------
# 📈 GRÁFICO TEMPORAL
# -------------------------------
st.subheader("📊 Evolução Temporal das Variáveis")
fig = px.line(
    df_filtrado,
    x="DataHora",
    y=vars_selecionadas,
    color="Estacao",
    template="plotly_dark",
    markers=True,
    title="Séries Temporais"
)
fig.update_layout(
    xaxis_title="Data e Hora",
    yaxis_title="Valor",
    legend_title="Estação",
    hovermode="x unified",
    margin=dict(l=40, r=20, t=60, b=40)
)
st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# 🗺️ MAPA REGIONAL
# -------------------------------
st.subheader("🗺️ Mapa Regional das Estações")

df_mapa = df_filtrado.groupby('Estacao')[vars_selecionadas].mean().reset_index()
df_mapa['lat'] = df_mapa['Estacao'].map(lambda x: COORDS[x][0])
df_mapa['lon'] = df_mapa['Estacao'].map(lambda x: COORDS[x][1])

param_mapa = st.selectbox("📌 Escolha a variável para o mapa:", options=vars_selecionadas)

fig_mapa = px.scatter_mapbox(
    df_mapa,
    lat="lat",
    lon="lon",
    size=param_mapa,
    color=param_mapa,
    hover_name="Estacao",
    zoom=8,
    size_max=35,
    mapbox_style="open-street-map",
    color_continuous_scale=px.colors.sequential.Plasma,
    title=f"Média de {param_mapa} por Estação"
)
st.plotly_chart(fig_mapa, use_container_width=True)

# -------------------------------
# 📤 DADOS E EXPORTAÇÃO
# -------------------------------
with st.expander("📋 Visualizar Dados"):
    st.dataframe(df_filtrado)

st.sidebar.markdown("---")
st.sidebar.download_button(
    label="⬇️ Baixar CSV",
    data=df_filtrado.to_csv(index=False).encode('utf-8'),
    file_name='dados_climaticos_filtrados.csv',
    mime='text/csv'
)
