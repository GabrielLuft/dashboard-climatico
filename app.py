import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from geopy.distance import geodesic
from sklearn.preprocessing import MinMaxScaler
import logging
import os
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from datetime import datetime

# --- CONFIGURAÇÕES E LOGGING ---

logging.basicConfig(
    filename='app.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

GSHEET_ID = os.getenv("GSHEET_ID", "1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA")

EXPECTED_COLUMNS = ['Data', 'Temperatura_Min', 'Temperatura_Med', 'Temperatura_Max',
                    'Chuva_mm', 'Umidade_Relativa', 'Vento', 'Latitude', 'Longitude']

RADAR_VARS = ['Temperatura_Min', 'Temperatura_Med', 'Temperatura_Max', 'Chuva_mm', 'Umidade_Relativa']

# --- FUNÇÕES ---

@st.cache_data(ttl=3600)  # cache por 1 hora para evitar recarregamento constante
def init_gspread_client(creds_json='credentials.json'):
    try:
        scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_json, scope)
        client = gspread.authorize(creds)
        logging.info("Google Sheets client autorizado com sucesso")
        return client
    except Exception as e:
        logging.error(f"Erro ao autenticar Google Sheets: {e}")
        st.error("Erro na autenticação do Google Sheets. Verifique as credenciais.")
        st.stop()

@st.cache_data(ttl=3600)
def carregar_abas(client, sheet_id):
    try:
        planilha = client.open_by_key(sheet_id)
        abas = planilha.worksheets()
        nomes_abas = [aba.title for aba in abas]
        logging.info(f"Abas encontradas: {nomes_abas}")
        return nomes_abas
    except Exception as e:
        logging.error(f"Erro ao listar abas da planilha: {e}")
        st.error("Erro ao listar abas da planilha Google Sheets.")
        st.stop()

@st.cache_data(ttl=3600)
def carregar_dados(client, sheet_id, abas):
    dados = {}
    planilha = client.open_by_key(sheet_id)
    for aba in abas:
        try:
            ws = planilha.worksheet(aba)
            df = pd.DataFrame(ws.get_all_records())
            # Validar colunas mínimas para evitar erros futuros
            missing_cols = [col for col in EXPECTED_COLUMNS if col not in df.columns]
            if missing_cols:
                logging.warning(f"Aba '{aba}' com colunas faltantes: {missing_cols}")
                continue  # pula essa aba

            # Ajuste Data
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
            df.dropna(subset=['Data'], inplace=True)

            dados[aba] = df
            logging.info(f"Dados carregados da aba {aba}")
        except Exception as e_aba:
            logging.warning(f"Não foi possível carregar aba {aba}: {e_aba}")
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

def plot_heatmap(df, var='Chuva_mm'):
    df['Data_str'] = df['Data'].dt.strftime('%Y-%m-%d')
    df['Hora'] = df['Data'].dt.hour if 'Hora' in df.columns else 12
    heat_data = df.pivot_table(index='Hora', columns='Data_str', values=var, aggfunc='mean').fillna(0)
    fig = px.imshow(heat_data,
                    aspect='auto',
                    labels=dict(x="Data", y="Hora do Dia", color=var),
                    title=f"Heatmap Temporal de {var}")
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

def plot_espaguete_3d(dfs, labels):
    fig = go.Figure()
    for i, df in enumerate(dfs):
        df_sorted = df.sort_values('Data')
        fig.add_trace(go.Scatter3d(
            x=df_sorted['Data'],
            y=[i]*len(df_sorted),
            z=df_sorted['Temperatura_Med'],
            mode='lines',
            name=labels[i],
        ))
    fig.update_layout(
        scene=dict(
            xaxis_title='Data',
            yaxis_title='Estação',
            yaxis=dict(tickvals=list(range(len(labels))), ticktext=labels),
            zaxis_title='Temperatura Média (°C)'
        ),
        title="Espaguete 3D da Temperatura Média"
    )
    return fig

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

def detectar_anomalias(df, var='Temperatura_Med', threshold=3):
    df['z_score'] = (df[var] - df[var].mean()) / df[var].std()
    anomalias = df[np.abs(df['z_score']) > threshold]
    return anomalias

def encontrar_estacao_proxima(lat_user, lon_user, dfs):
    estacoes = []
    for nome, df in dfs.items():
        lat = df['Latitude'].iloc[0]
        lon = df['Longitude'].iloc[0]
        dist = geodesic((lat_user, lon_user), (lat, lon)).km
        estacoes.append((nome, dist))
    estacoes.sort(key=lambda x: x[1])
    return estacoes[0][0] if estacoes else None

# --- INTERFACE ---

def main():
    st.set_page_config(page_title="Dashboard Climático Interativo", layout="wide", page_icon="🌦️")
    st.markdown("""
        <style>
            .main {
                background: linear-gradient(135deg, #1e1e2f, #28313f);
                color: #d0d0d0;
            }
            .title {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-weight: 700;
                font-size: 3rem;
                color: #00bcd4;
                text-align: center;
                margin-bottom: 1rem;
            }
        </style>""", unsafe_allow_html=True)
    st.markdown('<h1 class="title">Dashboard Climático Interativo</h1>', unsafe_allow_html=True)

    client = init_gspread_client()
    with st.spinner("Carregando abas..."):
        abas = carregar_abas(client, GSHEET_ID)
    with st.spinner("Carregando dados..."):
        dfs = carregar_dados(client, GSHEET_ID, abas)

    if not dfs:
        st.error("Nenhum dado carregado. Verifique a planilha e colunas.")
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

    st.plotly_chart(plot_heatmap(df_estacao, 'Chuva_mm'), use_container_width=True)
    st.plotly_chart(plot_heatmap(df_estacao, 'Umidade_Relativa'), use_container_width=True)

    st.plotly_chart(plot_candlestick(df_estacao), use_container_width=True)

    st.subheader("Comparação entre Estações (Radar Chart)")
    st.plotly_chart(plot_radar_chart(list(dfs.values()), list(dfs.keys())), use_container_width=True)

    st.subheader("Espaguete 3D - Temperatura Média")
    st.plotly_chart(plot_espaguete_3d(list(dfs.values()), list(dfs.keys())), use_container_width=True)

    st.subheader("Mapa térmico interpolado")
    st.plotly_chart(plot_map_thermal(dfs), use_container_width=True)

    st.subheader("Análise de Anomalias")
    threshold = st.slider("Threshold Z-score para outliers", 1.0, 5.0, 3.0, 0.1)
    anomalias = detectar_anomalias(df_estacao, threshold=threshold)
    st.write(f"Quantidade de dados fora do esperado (|z| > {threshold}): {len(anomalias)}")
    st.dataframe(anomalias[['Data', 'Temperatura_Med', 'z_score']])

if __name__ == "__main__":
    main()
