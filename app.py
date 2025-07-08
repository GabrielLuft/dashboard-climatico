import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np
from datetime import time
from scipy.interpolate import griddata

# Configurações iniciais do app
st.set_page_config(
    page_title="🌦️ Dashboard Climático Avançado | Serra Gaúcha & RS",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🌤️"
)

# --------- Constantes e Configurações ---------
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

VARS_DESCRICAO = {
    "Temperatura": "Temperatura do ar (°C)",
    "Umidade": "Umidade relativa do ar (%)",
    "Chuva": "Precipitação acumulada (mm)",
    "Radiação": "Radiação solar (W/m²)"
}

# --------- Função para carregar dados ---------
@st.cache_data(ttl=600)
def carregar_dados(sheet_id, gid_map):
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
            st.warning(f"⚠️ Erro ao carregar dados da estação {estacao}: {e}")
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()

# --------- Carregar dados ---------
with st.spinner("🔄 Carregando dados das estações..."):
    df = carregar_dados(SHEET_ID, GID_MAP)

if df.empty:
    st.error("❌ Nenhum dado disponível. Verifique os GIDs e o acesso à planilha.")
    st.stop()

# --------- Sidebar: Filtros ---------
st.sidebar.title("⚙️ Configurações do Dashboard")

# Seleção de estações
estacoes_selecionadas = st.sidebar.multiselect(
    "📍 Selecione as Estações:",
    options=list(GID_MAP.keys()),
    default=list(GID_MAP.keys())
)

# Variáveis
variaveis_disponiveis = list(VARS_DESCRICAO.keys())
variaveis_selecionadas = st.sidebar.multiselect(
    "📊 Variáveis para análise:",
    options=variaveis_disponiveis,
    default=["Temperatura", "Umidade"]
)

# Período
data_min = df['Data'].min().date()
data_max = df['Data'].max().date()

data_inicio = st.sidebar.date_input("Data Início", data_min, min_value=data_min, max_value=data_max)
data_fim = st.sidebar.date_input("Data Fim", data_max, min_value=data_min, max_value=data_max)

# Horário
hora_inicio = st.sidebar.slider("Hora Início", 0, 23, 0)
hora_fim = st.sidebar.slider("Hora Fim", 0, 23, 23)

# Filtro aplicado
df_filtrado = df[
    (df['Estacao'].isin(estacoes_selecionadas)) &
    (df['Data'] >= pd.to_datetime(data_inicio)) &
    (df['Data'] <= pd.to_datetime(data_fim)) &
    (df['Hora'] >= time(hora_inicio, 0)) &
    (df['Hora'] <= time(hora_fim, 59))
]

if df_filtrado.empty:
    st.warning("🔍 Nenhum dado encontrado com os filtros selecionados.")
    st.stop()

# --------- Layout Principal ---------
st.title("🌤️ Dashboard Climático Avançado - Serra Gaúcha & Região")
st.markdown(
    """
    ### Visualização interativa de dados meteorológicos com análise espacial e temporal.
    Desenvolvido para engenheiros, pesquisadores e profissionais do agro.
    """
)

# Métricas principais - layout com cores e ícones
with st.container():
    col1, col2, col3, col4 = st.columns(len(variaveis_selecionadas))
    for col, var in zip([col1, col2, col3, col4], variaveis_selecionadas):
        media = df_filtrado[var].mean()
        minimo = df_filtrado[var].min()
        maximo = df_filtrado[var].max()
        col.metric(
            label=f"📈 {var}",
            value=f"{media:.2f}",
            delta=f"Min: {minimo:.1f} | Max: {maximo:.1f}"
        )

# --------- Série Temporal com múltiplas variáveis ---------
st.subheader("📅 Evolução Temporal das Variáveis Selecionadas")

fig_line = px.line(
    df_filtrado,
    x='DataHora',
    y=variaveis_selecionadas,
    color='Estacao',
    template="plotly_dark",
    markers=True,
    title="Séries Temporais das Variáveis por Estação"
)
fig_line.update_layout(
    hovermode="x unified",
    legend_title_text="Estação",
    xaxis_title="Data e Hora",
    yaxis_title="Valor",
    margin=dict(t=50, b=40, l=40, r=20)
)
st.plotly_chart(fig_line, use_container_width=True)

# --------- Mapa Interpolado (Heatmap) ---------
st.subheader("🌡️ Mapa Regional com Interpolação de Calor")

# Preparar dados para interpolação média no período
df_media = df_filtrado.groupby('Estacao')[variaveis_selecionadas].mean().reset_index()
df_media['lat'] = df_media['Estacao'].map(lambda x: COORDS[x][0])
df_media['lon'] = df_media['Estacao'].map(lambda x: COORDS[x][1])

param_mapa = st.selectbox("Escolha o parâmetro para o mapa:", variaveis_selecionadas)

# Geração de grade para interpolação
num_grid = 100  # mais denso para melhor suavização
lat_min, lat_max = df_media['lat'].min(), df_media['lat'].max()
lon_min, lon_max = df_media['lon'].min(), df_media['lon'].max()

grid_lat, grid_lon = np.mgrid[lat_min:lat_max:complex(num_grid), lon_min:lon_max:complex(num_grid)]

# Interpolação com griddata
points = np.array([(lat, lon) for lat, lon in zip(df_media['lat'], df_media['lon'])])
values = df_media[param_mapa].values

grid_z = griddata(points, values, (grid_lat, grid_lon), method='cubic')

# Criar figura heatmap com plotly
fig_heatmap = px.imshow(
    grid_z.T,
    origin='lower',
    labels={'x': 'Latitude', 'y': 'Longitude', 'color': param_mapa},
    x=np.linspace(lat_min, lat_max, num_grid),
    y=np.linspace(lon_min, lon_max, num_grid),
    color_continuous_scale='thermal',
    aspect='auto',
    title=f"Mapa de Calor Interpolado - {param_mapa}"
)

# Sobrepor pontos das estações
fig_heatmap.add_scatter(
    x=df_media['lat'],
    y=df_media['lon'],
    mode='markers+text',
    marker=dict(size=12, color='black', symbol='x'),
    text=df_media['Estacao'],
    textposition='top center',
    name='Estações'
)

fig_heatmap.update_layout(
    xaxis_title="Latitude",
    yaxis_title="Longitude",
    coloraxis_colorbar=dict(title=VARS_DESCRICAO[param_mapa])
)

st.plotly_chart(fig_heatmap, use_container_width=True)

# --------- Visualização dos Dados ---------
with st.expander("📋 Visualizar tabela de dados filtrados"):
    st.dataframe(df_filtrado)

# --------- Download dos dados ---------
st.sidebar.markdown("---")
st.sidebar.download_button(
    label="⬇️ Baixar dados filtrados (CSV)",
    data=df_filtrado.to_csv(index=False).encode('utf-8'),
    file_name="dados_climaticos_filtrados.csv",
    mime="text/csv"
)

# --------- Rodapé ---------
st.markdown(
    """
    ---
    <small style="color:gray;">
    Dashboard desenvolvido por Gabriel Augusto Luft - Dados atualizados automaticamente da planilha Google Sheets
    </small>
    """,
    unsafe_allow_html=True
)
