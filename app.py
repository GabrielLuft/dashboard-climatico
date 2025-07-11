import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import urllib.request
from datetime import datetime
import numpy as np

# CONFIGURAÇÕES DO DASHBOARD
st.set_page_config(page_title="📊 AgroClima Futurista", layout="wide", page_icon="🌡️")

# === CSS Futurista ===
st.markdown("""
<style>
    html, body, [class*="css"]  {
        background-color: #0b0f1a;
        color: #c7f0ff;
        font-family: 'Segoe UI', sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #0b0f1a, #101c30);
    }
    h1, h2, h3, h4 {
        color: #29abe2;
    }
    .css-1d391kg { background-color: #0f192e; border-radius: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# === LINK DA PLANILHA GOOGLE ===
URL_GOOGLE_SHEET = "https://docs.google.com/spreadsheets/d/1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA/export?format=csv&gid=1136868112"

@st.cache_data
def carregar_dados():
    url = URL_GOOGLE_SHEET
    df = pd.read_csv(url)
    df['Data'] = pd.to_datetime(df['Data'])
    return df

# Carrega os dados
try:
    df = carregar_dados()
except Exception as e:
    st.error("Erro ao carregar os dados da planilha.")
    st.stop()

st.title("🌐 Painel Climático de Alta Precisão para Fruticultura")

# === INTERFACE INTERATIVA ===
col1, col2, col3, col4 = st.columns(4)

with col1:
    estacoes = df['Estação'].unique().tolist()
    estacao_selecionada = st.selectbox("📍 Selecione a estação", estacoes)

with col2:
    variavel = st.selectbox("📈 Variável", ['Temperatura Mínima', 'Temperatura Média', 'Temperatura Máxima', 'Umidade', 'Precipitação'])

with col3:
    media_movel = st.slider("📊 Janela de Média Móvel (dias)", 1, 30, 7)

with col4:
    intervalo_anomalia = st.slider("🚨 Desvio da média (anomalias)", 0.5, 5.0, 2.0, step=0.1)

# === FILTRO ===
df_estacao = df[df['Estação'] == estacao_selecionada].sort_values("Data")
df_estacao['Média Móvel'] = df_estacao[variavel].rolling(window=media_movel).mean()

media_global = df_estacao[variavel].mean()
desvio_global = df_estacao[variavel].std()

limite_sup = media_global + intervalo_anomalia * desvio_global
limite_inf = media_global - intervalo_anomalia * desvio_global

df_estacao['Anomalia'] = (df_estacao[variavel] > limite_sup) | (df_estacao[variavel] < limite_inf)

# === GRÁFICO TEMPORAL ===
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_estacao['Data'], y=df_estacao[variavel], mode='lines', name='Valor', line=dict(color='cyan')))
fig.add_trace(go.Scatter(x=df_estacao['Data'], y=df_estacao['Média Móvel'], mode='lines', name='Média Móvel', line=dict(color='magenta', dash='dash')))
fig.add_trace(go.Scatter(x=df_estacao[df_estacao['Anomalia']]['Data'],
                         y=df_estacao[df_estacao['Anomalia']][variavel],
                         mode='markers',
                         name='Anomalias',
                         marker=dict(size=10, color='red')))

fig.update_layout(
    title=f"Série Temporal de {variavel} em {estacao_selecionada}",
    xaxis_title='Data',
    yaxis_title=variavel,
    plot_bgcolor='#0b0f1a',
    paper_bgcolor='#0b0f1a',
    font=dict(color='white'),
    hovermode='x unified'
)

st.plotly_chart(fig, use_container_width=True)

# === TABELA DE ANOMALIAS ===
st.subheader("📋 Detecção de Anomalias")
df_anomalias = df_estacao[df_estacao['Anomalia']][['Data', variavel]]
df_anomalias = df_anomalias.rename(columns={variavel: "Valor fora do padrão"})

st.dataframe(df_anomalias, use_container_width=True)

# === RODAPÉ ===
st.markdown("""<br><hr><center style="color:#777">🛰️ Sistema AgroClima Avançado para Fruticultura • Desenvolvido com ♥️</center>""", unsafe_allow_html=True)
