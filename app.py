import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import time, date
import numpy as np

st.set_page_config(page_title="Dashboard Climático Multiestação", layout="wide", page_icon="🌦️")

# Sua planilha Google Sheet e seus gids de abas:
SHEET_ID = "1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA"
GID_MAP = {
    "Bento Gonçalves": "1136868112",
    "Caxias do Sul": "1234567890",  # Substitua pelos gid reais
    "Porto Alegre": "2345678901",
    "Pelotas": "3456789012",
    "Santa Maria": "4567890123"
}

# Coordenadas das estações (latitude, longitude)
COORDS = {
    "Bento Gonçalves": (-29.1667, -51.5194),
    "Caxias do Sul": (-29.1678, -51.1794),
    "Porto Alegre": (-30.0346, -51.2177),
    "Pelotas": (-31.7656, -52.3376),
    "Santa Maria": (-29.6846, -53.8060)
}

@st.cache_data(ttl=600)
def load_all_stations(sheet_id, gid_map):
    dfs = []
    for estacao, gid in gid_map.items():
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        try:
            df = pd.read_csv(url)
            df['Estacao'] = estacao
            # Ajuste datas e horas
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            df['Hora'] = pd.to_datetime(df['Hora'], format='%H:%M', errors='coerce').dt.time
            df['DataHora'] = pd.to_datetime(df['Data'].astype(str) + ' ' + df['Hora'].astype(str), errors='coerce')
            dfs.append(df.dropna(subset=['DataHora']))
        except Exception as e:
            st.warning(f"Erro ao carregar {estacao}: {e}")
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()  # vazio

df = load_all_stations(SHEET_ID, GID_MAP)

if df.empty:
    st.error("Nenhum dado carregado. Verifique os GIDs das abas e a planilha.")
    st.stop()

# Sidebar filtros
st.sidebar.header("Filtros")

estacoes_selecionadas = st.sidebar.multiselect("Selecione Estação(s)", options=list(COORDS.keys()), default=list(COORDS.keys()))
variaveis_disponiveis = ['Temperatura', 'Umidade', 'Chuva', 'Radiação']
variaveis_selecionadas = st.sidebar.multiselect("Variáveis para análise", options=variaveis_disponiveis, default=['Temperatura', 'Umidade'])

data_min = df['Data'].min().date()
data_max = df['Data'].max().date()

data_inicio = st.sidebar.date_input("Data Início", data_min, min_value=data_min, max_value=data_max)
data_fim = st.sidebar.date_input("Data Fim", data_max, min_value=data_min, max_value=data_max)

hora_inicio = st.sidebar.slider("Hora Início", 0, 23, 0, 1, format="%02d:00")
hora_fim = st.sidebar.slider("Hora Fim", 0, 23, 23, 1, format="%02d:00")

if hora_fim < hora_inicio:
    st.sidebar.error("Hora Fim deve ser maior ou igual à Hora Início")
    st.stop()

hora_inicio_time = time(hora_inicio, 0)
hora_fim_time = time(hora_fim, 59)

# Filtrar dados
df_filtrado = df[
    (df['Estacao'].isin(estacoes_selecionadas)) &
    (df['Data'] >= pd.to_datetime(data_inicio)) &
    (df['Data'] <= pd.to_datetime(data_fim)) &
    (df['Hora'] >= hora_inicio_time) &
    (df['Hora'] <= hora_fim_time)
]

if df_filtrado.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

st.title("🌦️ Dashboard Climático Multiestação")

# Indicadores rápidos
with st.container():
    cols = st.columns(len(variaveis_selecionadas))
    for col, var in zip(cols, variaveis_selecionadas):
        val_min = df_filtrado[var].min()
        val_max = df_filtrado[var].max()
        val_mean = df_filtrado[var].mean()
        col.metric(label=f"{var} (mín/média/máx)", value=f"{val_mean:.2f}", delta=f"{val_max - val_min:.2f}")

# Gráfico 2D sobreposto
st.subheader("Gráfico 2D das variáveis por estação")
fig = px.line(
    df_filtrado,
    x='DataHora',
    y=variaveis_selecionadas,
    color='Estacao',
    line_group='Estacao',
    labels={"DataHora": "Data e Hora"},
    title="Visualização Temporal das Variáveis Climáticas"
)
st.plotly_chart(fig, use_container_width=True)

# Mapa interativo
st.subheader("Mapa Regional das Estações")

# Calcular média dos parâmetros selecionados por estação
map_data = df_filtrado.groupby('Estacao')[variaveis_selecionadas].mean().reset_index()
map_data['lat'] = map_data['Estacao'].map(lambda x: COORDS.get(x, (None, None))[0])
map_data['lon'] = map_data['Estacao'].map(lambda x: COORDS.get(x, (None, None))[1])

parametro_mapa = st.selectbox("Parâmetro para visualização no mapa", options=variaveis_selecionadas)

fig_map = px.scatter_mapbox(
    map_data,
    lat='lat',
    lon='lon',
    size=parametro_mapa,
    color=parametro_mapa,
    hover_name='Estacao',
    color_continuous_scale=px.colors.sequential.Viridis,
    size_max=35,
    zoom=6,
    mapbox_style="carto-positron",
    title=f"Média Regional de {parametro_mapa} nas Estações Selecionadas"
)
st.plotly_chart(fig_map, use_container_width=True)

# Exibir dados filtrados
with st.expander("Dados filtrados"):
    st.dataframe(df_filtrado)

# Exportar CSV
if st.sidebar.button("Exportar dados filtrados CSV"):
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(label="Download CSV", data=csv, file_name='dados_filtrados.csv', mime='text/csv')
