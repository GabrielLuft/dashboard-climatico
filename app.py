import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
from geopy.distance import geodesic

# --- CONFIGURAÇÕES ---

CSV_LINKS = {
    "Estacao1": "https://docs.google.com/spreadsheets/d/e/2PACX-1vR9AdILQ93f2IDMadcvHS5SK29o3fanNPDUrMA-QkV55XyrBmr8TdoFtu6h58FtSRrLFVupUmO5DrrG/pub?output=csv&gid=0",
    # Adicione outros links CSV aqui...
}

EXPECTED_COLUMNS = ['Data', 'Temperatura_Min', 'Temperatura_Med', 'Temperatura_Max',
                    'Chuva_mm', 'Umidade_Relativa', 'Vento', 'Latitude', 'Longitude']

RADAR_VARS = ['Temperatura_Min', 'Temperatura_Med', 'Temperatura_Max', 'Chuva_mm', 'Umidade_Relativa']

# --- FUNÇÕES ---

@st.cache_data(ttl=3600)
def carregar_dados(csv_links):
    dados = {}
    for nome, url in csv_links.items():
        try:
            df = pd.read_csv(url)
            if 'Data' in df.columns:
                df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
                df.dropna(subset=['Data'], inplace=True)
            else:
                st.warning(f"Coluna 'Data' não encontrada na estação {nome}")
                continue

            missing_cols = [col for col in EXPECTED_COLUMNS if col not in df.columns]
            if missing_cols:
                st.warning(f"Colunas faltantes na estação {nome}: {missing_cols}")
                continue

            dados[nome] = df
        except Exception as e:
            st.error(f"Erro ao carregar dados da estação {nome}: {e}")
    return dados

def plot_media_movel(df, dias=7):
    df_sorted = df.sort_values('Data')
    df_sorted['Temp_Med_Media_Movel'] = df_sorted['Temperatura_Med'].rolling(window=dias).mean()
    fig = px.line(df_sorted, x='Data', y=['Temperatura_Med', 'Temp_Med_Media_Movel'],
                  title=f"Temperatura Média e Média Móvel {dias} dias",
                  labels={'value': 'Temperatura (°C)', 'variable': 'Legenda'})
    return fig

def plot_boxplot(df, intervalo='Dia'):
    df = df.copy()
    if intervalo == 'Dia':
        df['Periodo'] = df['Data'].dt.date
    elif intervalo == 'Semana':
        df['Periodo'] = df['Data'].dt.to_period('W').apply(lambda r: r.start_time)
    else:
        df['Periodo'] = df['Data'].dt.to_period('M').apply(lambda r: r.start_time)
    fig = px.box(df, x='Periodo', y='Temperatura_Med', points='all',
                 title=f"Boxplot Temperatura Média por {intervalo}")
    return fig

def plot_candlestick(df):
    df_sorted = df.sort_values('Data')
    fig = go.Figure(data=[go.Candlestick(
        x=df_sorted['Data'],
        open=df_sorted['Temperatura_Min'],
        high=df_sorted['Temperatura_Max'],
        low=df_sorted['Temperatura_Min'],
        close=df_sorted['Temperatura_Med'],
        increasing_line_color='green',
        decreasing_line_color='red'
    )])
    fig.update_layout(title="Candlestick Climático",
                      xaxis_title="Data",
                      yaxis_title="Temperatura (°C)")
    return fig

def plot_radar_chart(dfs, labels):
    scaler = MinMaxScaler()
    radar_data = []
    for df in dfs:
        mean_vals = df[RADAR_VARS].mean().values.reshape(1, -1)
        scaled = scaler.fit_transform(mean_vals)[0]
        radar_data.append(scaled)
    categories = RADAR_VARS
    fig = go.Figure()
    for i, data in enumerate(radar_data):
        fig.add_trace(go.Scatterpolar(
            r=data,
            theta=categories,
            fill='toself',
            name=labels[i]
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,1])),
        showlegend=True,
        title="Radar Chart: Comparação entre Estações"
    )
    return fig

def detectar_anomalias(df, var='Temperatura_Med', threshold=3):
    df = df.copy()
    df['z_score'] = (df[var] - df[var].mean()) / df[var].std()
    anomalias = df[np.abs(df['z_score']) > threshold]
    return anomalias

def encontrar_estacao_proxima(lat_user, lon_user, dfs):
    estacoes = []
    for nome, df in dfs.items():
        # Pega latitude e longitude da última data
        df_sorted = df.sort_values('Data')
        lat = df_sorted['Latitude'].iloc[-1]
        lon = df_sorted['Longitude'].iloc[-1]
        dist = geodesic((lat_user, lon_user), (lat, lon)).km
        estacoes.append((nome, dist))
    estacoes.sort(key=lambda x: x[1])
    return estacoes[0][0] if estacoes else None

def plot_map_thermal(dfs):
    df_map = pd.DataFrame()
    for nome, df in dfs.items():
        last = df.sort_values('Data').iloc[-1]
        df_map = pd.concat([df_map, pd.DataFrame({
            'Estacao': [nome],
            'Lat': [last['Latitude']],
            'Lon': [last['Longitude']],
            'Temp_Med': [last['Temperatura_Med']]
        })])
    fig = px.scatter_mapbox(df_map, lat='Lat', lon='Lon', color='Temp_Med',
                            size='Temp_Med', color_continuous_scale='thermal',
                            size_max=15, zoom=5,
                            mapbox_style='carto-darkmatter',
                            hover_name='Estacao',
                            title="Mapa térmico interpolado de Temperatura Média")
    return fig

# --- INTERFACE ---

def main():
    st.set_page_config(page_title="Dashboard Climático Interativo", layout="wide", page_icon="🌦️")

    # Estilo CSS para fundo escuro e fontes modernas
    st.markdown(
        """
        <style>
        .main {
            background: linear-gradient(135deg, #1e1e2f, #28313f);
            color: #d0d0d0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .css-1d391kg {
            background-color: transparent;
        }
        .css-ffhzg2 {
            color: #00bcd4 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("Dashboard Climático Interativo - Versão com Geolocalização e Mapa")

    dfs = carregar_dados(CSV_LINKS)

    if not dfs:
        st.error("Nenhum dado válido carregado. Verifique os links CSV.")
        st.stop()

    st.sidebar.header("Configurações")

    detectar_auto = st.sidebar.checkbox("Detectar estação mais próxima automaticamente", value=True)

    lat_user = st.sidebar.number_input("Latitude sua localização", value=-29.169, format="%.6f")
    lon_user = st.sidebar.number_input("Longitude sua localização", value=-51.528, format="%.6f")

    if detectar_auto:
        estacao_selecionada = encontrar_estacao_proxima(lat_user, lon_user, dfs)
        st.sidebar.success(f"Estação detectada: {estacao_selecionada}")
    else:
        estacao_selecionada = st.sidebar.selectbox("Escolha a estação", list(dfs.keys()))

    df_estacao = dfs.get(estacao_selecionada)

    if df_estacao is None or df_estacao.empty:
        st.error("Dados da estação selecionada não encontrados ou vazios.")
        st.stop()

    st.subheader(f"Dados da estação: {estacao_selecionada}")
    st.dataframe(df_estacao.head())

    st.plotly_chart(plot_media_movel(df_estacao), use_container_width=True)

    intervalo = st.selectbox("Intervalo para boxplot", ['Dia', 'Semana', 'Mês'])
    st.plotly_chart(plot_boxplot(df_estacao, intervalo), use_container_width=True)

    st.plotly_chart(plot_candlestick(df_estacao), use_container_width=True)

    st.subheader("Comparação entre Estações (Radar Chart)")
    st.plotly_chart(plot_radar_chart(list(dfs.values()), list(dfs.keys())), use_container_width=True)

    st.subheader("Mapa térmico interpolado")
    st.plotly_chart(plot_map_thermal(dfs), use_container_width=True)

    st.subheader("Análise de Anomalias")
    threshold = st.slider("Threshold Z-score para outliers", 1.0, 5.0, 3.0, 0.1)
    anomalias = detectar_anomalias(df_estacao, threshold=threshold)
    st.write(f"Quantidade de dados fora do esperado (|z| > {threshold}): {len(anomalias)}")
    st.dataframe(anomalias[['Data', 'Temperatura_Med', 'z_score']])

if __name__ == "__main__":
    main()
