import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.interpolate import griddata
from datetime import datetime

st.set_page_config(page_title="Dashboard Climático Profissional", layout="wide")

st.title("🌦️ Dashboard Climático Profissional - Serra Gaúcha")
st.markdown("""
Painel interativo para análise e visualização dinâmica dos dados meteorológicos das estações da Serra Gaúcha.
Selecione as estações, variáveis e período para gerar gráficos técnicos, análises estatísticas e mapa interpolado.
""")

# Constantes para tradução e descrição das variáveis
VARS_DESCRICAO = {
    'Umidade': 'Umidade Relativa (%)',
    'Temperatura': 'Temperatura (°C)',
    'Chuva': 'Precipitação (mm)',
    'Radiação': 'Radiação Solar (W/m²)'
}

# Função para ler dados das abas e acrescentar coordenadas com base no nome da estação (aba)
def carregar_dados(sheet_url):
    xls = pd.ExcelFile(sheet_url)
    lista_dfs = []
    coord_estacoes = {
        'Bento Gonçalves': (-29.1698, -51.5237),
        'Caxias do Sul': (-29.1678, -51.1794),
        'Garibaldi': (-29.2339, -51.4997),
        'Farroupilha': (-29.2015, -51.3354)
    }
    for aba in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=aba)
            df['Estacao'] = aba
            lat, lon = coord_estacoes.get(aba, (np.nan, np.nan))
            df['lat'] = lat
            df['lon'] = lon
            lista_dfs.append(df)
        except Exception as e:
            st.warning(f"Erro ao carregar aba {aba}: {e}")
    if lista_dfs:
        return pd.concat(lista_dfs, ignore_index=True)
    else:
        return pd.DataFrame()

# URL da planilha pública do Google Sheets exportada para Excel (coloque a sua aqui)
GOOGLE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA/export?format=xlsx'

@st.cache_data(ttl=3600)
def carregar_planilha():
    return carregar_dados(GOOGLE_SHEET_URL)

df = carregar_planilha()

# Convertendo datas
df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
df = df.dropna(subset=['Data'])  # Remove linhas sem data válida

# Sidebar: seleção de estações e variáveis - iniciando vazio
estacoes_disponiveis = df['Estacao'].unique().tolist()
variaveis_disponiveis = ['Umidade', 'Temperatura', 'Chuva', 'Radiação']

st.sidebar.header("Configurações do Dashboard")
selected_estacoes = st.sidebar.multiselect("Selecione as Estações", options=estacoes_disponiveis, default=[])
selected_variaveis = st.sidebar.multiselect("Selecione as Variáveis", options=variaveis_disponiveis, default=[])

data_min = df['Data'].min()
data_max = df['Data'].max()
data_inicio = st.sidebar.date_input("Data Início", value=data_min, min_value=data_min, max_value=data_max)
data_fim = st.sidebar.date_input("Data Fim", value=data_max, min_value=data_min, max_value=data_max)

# Filtrando dados conforme seleções
if not selected_estacoes or not selected_variaveis:
    st.warning("Por favor, selecione pelo menos uma estação e uma variável para continuar.")
    st.stop()

df_filtrado = df[
    (df['Estacao'].isin(selected_estacoes)) &
    (df['Data'] >= pd.to_datetime(data_inicio)) &
    (df['Data'] <= pd.to_datetime(data_fim))
].copy()

if df_filtrado.empty:
    st.error("Nenhum dado disponível para as seleções feitas.")
    st.stop()

# ---- Gráfico de Séries Temporais ----
st.header("📈 Séries Temporais")
for var in selected_variaveis:
    fig = px.line(
        df_filtrado,
        x='Data',
        y=var,
        color='Estacao',
        title=f"Série Temporal de {VARS_DESCRICAO.get(var, var)}",
        labels={'Data': 'Data', var: VARS_DESCRICAO.get(var, var)},
        template='plotly_white'
    )
    fig.update_layout(legend_title_text="Estação", font=dict(size=14))
    st.plotly_chart(fig, use_container_width=True)

# ---- Boxplot Mensal com melhor visual ----
st.header("📦 Distribuição Mensal")
df_filtrado['Mes'] = df_filtrado['Data'].dt.to_period('M').astype(str)
for var in selected_variaveis:
    fig_box = px.box(
        df_filtrado,
        x='Mes',
        y=var,
        color='Estacao',
        points='outliers',
        labels={"Mes": "Mês", var: VARS_DESCRICAO.get(var, var)},
        title=f"Distribuição Mensal de {VARS_DESCRICAO.get(var, var)}",
        template='plotly_white'
    )
    fig_box.update_layout(legend_title_text="Estação", font=dict(size=14))
    st.plotly_chart(fig_box, use_container_width=True)

# ---- Mapa de Interpolação (Heatmap) ----
st.header("🌍 Mapa de Interpolação por Estação")

param_mapa = st.selectbox("Escolha o parâmetro para o mapa", options=selected_variaveis)

# Média por estação para o parâmetro escolhido
df_media = df_filtrado.groupby(['Estacao', 'lat', 'lon'])[param_mapa].mean().reset_index()

# Gerar grid para interpolação
num_grid = 100
lat_min, lat_max = df_media['lat'].min(), df_media['lat'].max()
lon_min, lon_max = df_media['lon'].min(), df_media['lon'].max()
grid_lat, grid_lon = np.mgrid[lat_min:lat_max:complex(num_grid), lon_min:lon_max:complex(num_grid)]

points = df_media[['lat', 'lon']].values
values = df_media[param_mapa].values

try:
    grid_z = griddata(points, values, (grid_lat, grid_lon), method='cubic')
except Exception:
    grid_z = griddata(points, values, (grid_lat, grid_lon), method='linear')

fig_map = go.Figure(go.Contour(
    z=grid_z,
    x=np.linspace(lon_min, lon_max, num_grid),
    y=np.linspace(lat_min, lat_max, num_grid),
    colorscale='Viridis',
    colorbar=dict(title=VARS_DESCRICAO.get(param_mapa, param_mapa)),
    contours=dict(showlabels=True),
    line_smoothing=0.85
))

fig_map.add_trace(go.Scattergeo(
    lon=df_media['lon'],
    lat=df_media['lat'],
    mode='markers+text',
    marker=dict(size=14, color='crimson', symbol='circle'),
    text=df_media['Estacao'] + "<br>" + df_media[param_mapa].round(2).astype(str),
    textposition="top center",
    name="Estações"
))

fig_map.update_geos(
    visible=False,
    resolution=50,
    showcountries=False,
    showsubunits=False,
    fitbounds="locations"
)

fig_map.update_layout(
    height=550,
    margin=dict(l=0, r=0, t=40, b=0),
    title=f"Mapa de Interpolação do parâmetro {VARS_DESCRICAO.get(param_mapa, param_mapa)}",
    font=dict(size=16)
)

st.plotly_chart(fig_map, use_container_width=True)

# ---- Resumo Estatístico ----
st.header("📋 Resumo Estatístico das Variáveis")
df_resumo = df_filtrado.groupby('Estacao')[selected_variaveis].agg(['mean', 'median', 'std', 'min', 'max'])
df_resumo.columns = ['_'.join(col).strip() for col in df_resumo.columns.values]  # Flatten multiindex
st.dataframe(df_resumo.style.format("{:.2f}"), height=300)

# ---- Rodapé discreto ----
st.markdown("""
---
Dashboard criado por Gabriel Augusto Luft - {0}
""".format(datetime.now().strftime("%d/%m/%Y")), unsafe_allow_html=True)
