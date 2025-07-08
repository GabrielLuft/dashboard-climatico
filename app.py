
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import griddata
from datetime import datetime

# ------------------------- CONFIGURAÇÕES GERAIS -------------------------
st.set_page_config(layout="wide", page_title="Painel Climático para Viticultura")
st.title("🍇 Painel Climático Interativo para a Viticultura da Serra Gaúcha")
st.markdown("""
Monitore em tempo real os dados climáticos de diferentes regiões vitícolas. 
Gráficos técnicos, visualizações 3D e mapas interativos para suporte na tomada de decisão.
""")

# ------------------------- FUNÇÃO PARA CARREGAR PLANILHA -------------------------
@st.cache_data(ttl=3600)
def carregar_dados():
    URL = "https://docs.google.com/spreadsheets/d/1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA/export?format=xlsx"
    xls = pd.ExcelFile(URL)

    coordenadas = {
        "Bento Gonçalves": (-29.1667, -51.5167),
        "Caxias do Sul": (-29.1684, -51.1794),
        "Garibaldi": (-29.2565, -51.5352),
        "Farroupilha": (-29.2225, -51.3419),
    }

    dados = []
    for aba in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=aba)
            if {'Data', 'Hora', 'Umidade', 'Temperatura', 'Chuva', 'Radiação'}.issubset(df.columns):
                df['Estacao'] = aba
                df['Datetime'] = pd.to_datetime(df['Data'].astype(str) + ' ' + df['Hora'].astype(str), errors='coerce')
                df[['Latitude', 'Longitude']] = coordenadas.get(aba, (np.nan, np.nan))
                dados.append(df)
        except:
            continue

    if not dados:
        return pd.DataFrame()
    return pd.concat(dados, ignore_index=True)

# ------------------------- DADOS -------------------------
df = carregar_dados()
variaveis = ['Temperatura', 'Umidade', 'Chuva', 'Radiação']

# ------------------------- SIDEBAR -------------------------
st.sidebar.header("🎛️ Filtros")

estacoes = st.sidebar.multiselect("Estações", sorted(df['Estacao'].unique()), default=[])
variaveis_selecionadas = st.sidebar.multiselect("Variáveis Climáticas", variaveis, default=[])
data_min, data_max = df['Datetime'].min(), df['Datetime'].max()
data_inicio = st.sidebar.date_input("Data Início", data_min.date())
data_fim = st.sidebar.date_input("Data Fim", data_max.date())
media_movel = st.sidebar.checkbox("Aplicar média móvel de 3 horas")

# ------------------------- FILTRAGEM -------------------------
df_filtrado = df[
    (df['Estacao'].isin(estacoes)) &
    (df['Datetime'] >= pd.to_datetime(data_inicio)) &
    (df['Datetime'] <= pd.to_datetime(data_fim))
]

# ------------------------- GRÁFICOS DE SÉRIE TEMPORAL -------------------------
if estacoes and variaveis_selecionadas:
    st.subheader("📈 Dinâmica Temporal das Variáveis")
    for var in variaveis_selecionadas:
        fig = px.line(df_filtrado, x='Datetime', y=var, color='Estacao',
                      markers=True, title=f"{var} ao longo do tempo",
                      template='plotly_white')
        if media_movel:
            for est in df_filtrado['Estacao'].unique():
                dados_est = df_filtrado[df_filtrado['Estacao'] == est].sort_values('Datetime')
                dados_est[var + '_mm'] = dados_est[var].rolling(3).mean()
                fig.add_scatter(x=dados_est['Datetime'], y=dados_est[var + '_mm'],
                                mode='lines', name=f"{est} - MM", line=dict(dash='dot'))
        st.plotly_chart(fig, use_container_width=True)

# ------------------------- BOXPLOT -------------------------
    st.subheader("📊 Distribuição por Estação (Boxplot)")
    for var in variaveis_selecionadas:
        fig_box = px.box(df_filtrado, x='Estacao', y=var, color='Estacao', title=f"Distribuição de {var}", template='ggplot2')
        st.plotly_chart(fig_box, use_container_width=True)

# ------------------------- GRÁFICO 3D -------------------------
    st.subheader("🌐 Gráficos Tridimensionais por Variável")
    for var in variaveis_selecionadas:
        fig3d = px.scatter_3d(df_filtrado, x='Datetime', y='Estacao', z=var, color='Estacao',
                              title=f"{var} no Espaço-Tempo", template='plotly_dark')
        st.plotly_chart(fig3d, use_container_width=True)

# ------------------------- INTERPOLAÇÃO DE CALOR -------------------------
    st.subheader("🗺️ Mapa de Interpolação Climática (Superfície 3D)")
    if len(estacoes) >= 3:
        for var in variaveis_selecionadas:
            ultimos_valores = df_filtrado.sort_values('Datetime').groupby('Estacao').tail(1)
            pontos = ultimos_valores[['Latitude', 'Longitude']].dropna().values
            valores = ultimos_valores[var].values
            grid_lat, grid_lon = np.mgrid[
                pontos[:, 0].min():pontos[:, 0].max():100j,
                pontos[:, 1].min():pontos[:, 1].max():100j
            ]
            grid_z = griddata(pontos, valores, (grid_lat, grid_lon), method='linear')

            fig_map = go.Figure(data=[
                go.Surface(z=grid_z, x=grid_lat, y=grid_lon, colorscale='Inferno', opacity=0.85)
            ])
            fig_map.update_layout(
                title=f"Distribuição espacial de {var}",
                scene=dict(xaxis_title='Latitude', yaxis_title='Longitude', zaxis_title=var),
                template='plotly_dark'
            )
            st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.warning("⚠️ Selecione pelo menos 3 estações para gerar a interpolação espacial.")
else:
    st.info("Selecione ao menos uma estação e uma variável para visualizar os gráficos.")
