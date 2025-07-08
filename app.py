import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import time
from scipy.interpolate import griddata
from sklearn.linear_model import LinearRegression

# --- Configurações da página ---
st.set_page_config(
    page_title="🌦️ Dashboard Climático Completo | Serra Gaúcha",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🌤️"
)

# --- Constantes e funções ---
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
    "Farroupilha": (-29.2222, -51.3475),
}

VARS_DESCRICAO = {
    "Temperatura": "Temperatura (°C)",
    "Umidade": "Umidade Relativa (%)",
    "Chuva": "Chuva (mm)",
    "Radiação": "Radiação (W/m²)"
}

@st.cache_data(ttl=600)
def carregar_dados(sheet_id, gid_map):
    dfs = []
    for estacao, gid in gid_map.items():
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        try:
            df = pd.read_csv(url)
            df.columns = df.columns.str.strip()
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

# --- Carregamento ---
df = carregar_dados(SHEET_ID, GID_MAP)

if df.empty:
    st.error("❌ Nenhum dado disponível.")
    st.stop()

# --- Sidebar ---
st.sidebar.title("⚙️ Configurações")

variaveis_disponiveis = [col for col in ["Temperatura", "Umidade", "Chuva", "Radiação"] if col in df.columns]
variaveis_selecionadas = st.sidebar.multiselect("Selecione variáveis:", variaveis_disponiveis, default=variaveis_disponiveis[:2])
estacoes_selecionadas = st.sidebar.multiselect("Selecione estações:", list(GID_MAP.keys()), default=list(GID_MAP.keys()))
data_min = df['Data'].min().date()
data_max = df['Data'].max().date()
data_inicio = st.sidebar.date_input("Data início:", data_min, min_value=data_min, max_value=data_max)
data_fim = st.sidebar.date_input("Data fim:", data_max, min_value=data_min, max_value=data_max)
hora_inicio = st.sidebar.slider("Hora início:", 0, 23, 0)
hora_fim = st.sidebar.slider("Hora fim:", 0, 23, 23)
usar_media_movel = st.sidebar.checkbox("Média móvel", value=False)
window_size = 3
if usar_media_movel:
    window_size = st.sidebar.slider("Janela média móvel:", 2, 10, 3)

df_filtrado = df[
    (df['Estacao'].isin(estacoes_selecionadas)) &
    (df['Data'] >= pd.to_datetime(data_inicio)) &
    (df['Data'] <= pd.to_datetime(data_fim)) &
    (df['Hora'] >= time(hora_inicio)) &
    (df['Hora'] <= time(hora_fim))
]

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado com filtros.")
    st.stop()

# Aplica média móvel se selecionado
if usar_media_movel:
    for var in variaveis_selecionadas:
        df_filtrado[var] = df_filtrado.groupby('Estacao')[var].transform(lambda x: x.rolling(window=window_size, min_periods=1).mean())

st.title("🌦️ Dashboard Climático Avançado - Serra Gaúcha")

# -- 1. Séries temporais
st.header("📈 Séries Temporais")
fig1 = px.line(df_filtrado, x='DataHora', y=variaveis_selecionadas, color='Estacao', line_dash='Estacao', markers=True,
               labels={"DataHora":"Data e Hora"}, title="Séries Temporais")
fig1.update_layout(template="plotly_white", legend_title_text="Estações")
st.plotly_chart(fig1, use_container_width=True)

# -- 2. Gráfico de área empilhada
st.header("📊 Área Empilhada (composição)")
df_agg = df_filtrado.groupby(['DataHora', 'Estacao'])[variaveis_selecionadas].sum().reset_index()
fig2 = px.area(df_agg, x='DataHora', y=variaveis_selecionadas, color='Estacao', line_group='Estacao',
               labels={"DataHora":"Data e Hora"}, title="Área Empilhada por Estação")
fig2.update_layout(template="plotly_white", legend_title_text="Estações")
st.plotly_chart(fig2, use_container_width=True)

# -- 3. Boxplots mensais
st.header("📦 Boxplot Mensal")
df_filtrado['Mes'] = df_filtrado['Data'].dt.to_period('M')
for var in variaveis_selecionadas:
    fig_box = px.box(df_filtrado, x='Mes', y=var, color='Estacao', points="outliers",
                     labels={"Mes": "Mês", var: VARS_DESCRICAO.get(var, var)},
                     title=f"Distribuição Mensal de {var}")
    fig_box.update_layout(template="plotly_white", legend_title_text="Estações")
    st.plotly_chart(fig_box, use_container_width=True)

# -- 4. Heatmap Diário x Hora
st.header("🌡️ Heatmap Diário x Hora")
for var in variaveis_selecionadas:
    df_heat = df_filtrado.copy()
    df_heat['Dia'] = df_heat['Data'].dt.day
    df_heat['HoraInt'] = df_heat['Hora'].apply(lambda t: t.hour)
    df_pivot = df_heat.pivot_table(index='Dia', columns='HoraInt', values=var, aggfunc='mean')
    fig_heat = px.imshow(df_pivot,
                        labels=dict(x="Hora do dia", y="Dia do mês", color=VARS_DESCRICAO.get(var, var)),
                        title=f"Heatmap de {var} (Dia x Hora)",
                        aspect="auto", color_continuous_scale='Viridis')
    st.plotly_chart(fig_heat, use_container_width=True)

# -- 5. Scatter Plot Matrix (pairplot) & Correlograma
st.header("🔎 Correlações e Scatter Matrix")
if len(variaveis_selecionadas) > 1:
    df_corr = df_filtrado[variaveis_selecionadas].corr()
    fig_corr = px.imshow(df_corr, text_auto=True, color_continuous_scale='RdBu_r', zmin=-1, zmax=1,
                         title="Correlograma das Variáveis")
    st.plotly_chart(fig_corr, use_container_width=True)

    fig_pair = px.scatter_matrix(df_filtrado, dimensions=variaveis_selecionadas, color='Estacao',
                                 title="Scatter Plot Matrix")
    fig_pair.update_layout(template="plotly_white")
    st.plotly_chart(fig_pair, use_container_width=True)

# -- 6. Gráfico de Tendência (Regressão Linear)
st.header("📉 Análise de Tendência")
for var in variaveis_selecionadas:
    st.subheader(f"Tendência de {var}")
    trend_data = []
    for est in estacoes_selecionadas:
        df_est = df_filtrado[df_filtrado['Estacao'] == est].sort_values('DataHora')
        if df_est.empty:
            continue
        # Convertendo datetime para ordinal para regressão
        x = df_est['DataHora'].map(pd.Timestamp.toordinal).values.reshape(-1,1)
        y = df_est[var].values
        model = LinearRegression()
        model.fit(x, y)
        trend_line = model.predict(x)
        trend_data.append((est, df_est['DataHora'], y, trend_line))

    fig_trend = go.Figure()
    for est, dates, y, trend_line in trend_data:
        fig_trend.add_trace(go.Scatter(x=dates, y=y, mode='markers', name=f"{est} - Dados"))
        fig_trend.add_trace(go.Scatter(x=dates, y=trend_line, mode='lines', name=f"{est} - Tendência"))
    fig_trend.update_layout(template="plotly_white", height=400,
                            yaxis_title=VARS_DESCRICAO.get(var, var),
                            xaxis_title="Data")
    st.plotly_chart(fig_trend, use_container_width=True)

# -- 7. Análise de Anomalias (Desvio da média)
st.header("⚠️ Análise de Anomalias")
for var in variaveis_selecionadas:
    st.subheader(f"Anomalias de {var}")
    media_geral = df_filtrado[var].mean()
    df_filtrado[f"Anomalia_{var}"] = df_filtrado[var] - media_geral
    fig_anom = px.line(df_filtrado, x='DataHora', y=f"Anomalia_{var}", color='Estacao',
                      labels={"DataHora": "Data e Hora", f"Anomalia_{var}": f"Anomalia de {var}"},
                      title=f"Anomalias de {var} (diferença da média)")
    st.plotly_chart(fig_anom, use_container_width=True)

# -- 8. Mapa de calor interpolado e bolhas
st.header("🌍 Mapa Regional - Interpolação de Calor")

df_media = df_filtrado.groupby('Estacao')[variaveis_selecionadas].mean().reset_index()
df_media['lat'] = df_media['Estacao'].map(lambda x: COORDS.get(x, (None, None))[0])
df_media['lon'] = df_media['Estacao'].map(lambda x: COORDS.get(x, (None, None))[1])

param_mapa = st.selectbox("Parâmetro para mapa:", variaveis_selecionadas)

num_grid = 150
lat_min, lat_max = df_media['lat'].min(), df_media['lat'].max()
lon_min, lon_max = df_media['lon'].min(), df_media['lon'].max()

grid_lat, grid_lon = np.mgrid[lat_min:lat_max:complex(num_grid), lon_min:lon_max:complex(num_grid)]
points = np.array(list(zip(df_media['lat'], df_media['lon'])))
values = df_media[param_mapa].values

mask_valid = ~np.isnan(values)
points_valid = points[mask_valid]
values_valid = values[mask_valid]

try:
    metodo_interp = 'cubic' if len(points_valid) >= 4 else 'nearest'
    grid_z = griddata(points_valid, values_valid, (grid_lat, grid_lon), method=metodo_interp)
except:
    grid_z = griddata(points_valid, values_valid, (grid_lat, grid_lon), method='nearest')

fig_map = go.Figure(data=
    go.Contour(
        z=grid_z,
        x=np.linspace(lon_min, lon_max, num_grid),
        y=np.linspace(lat_min, lat_max, num_grid),
        colorscale='Viridis',
        colorbar=dict(title=VARS_DESCRICAO.get(param_mapa, param_mapa)),
        contours=dict(showlabels=True)
    )
)

fig_map.add_trace(go.Scattergeo(
    lon=df_media['lon'],
    lat=df_media['lat'],
    mode='markers+text',
    marker=dict(size=12, color='red', symbol='circle'),
    text=df_media['Estacao'] + "<br>" + df_media[param_mapa].round(2).astype(str),
    textposition="top center",
    name="Estações"
))

fig_map.update_geos(
    visible=False, resolution=50,
    showcountries=False, showsubunits=False,
    fitbounds="locations"
)

fig_map.update_layout(height=500, margin=dict(l=0,r=0,t=40,b=0), title=f"Mapa de Interpolação de {param_mapa}")
st.plotly_chart(fig_map, use_container_width=True)

# -- 9. Resumo estatístico dinâmico
st.header("📋 Resumo Estatístico das Variáveis")
st.dataframe(df_filtrado.groupby('Estacao')[variaveis_selecionadas].agg(['mean','median','std','min','max']))

