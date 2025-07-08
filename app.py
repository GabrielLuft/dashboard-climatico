
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.express as px

st.set_page_config(page_title="🌐 AgriClim – Dashboard Futurista", layout="wide")

st.markdown("""
# 🌿 AgriClim – Dashboard Climático Futurista para Fruticultura
Visualização de dados meteorológicos com foco em usabilidade, estética e tecnologia para o campo.
""")

# Simulação de dados (substitua pelo carregamento real)
@st.cache_data
def gerar_dados():
    np.random.seed(42)
    datas = pd.date_range("2024-01-01", periods=90, freq="D")
    dados = pd.DataFrame({
        "Data": datas,
        "Temperatura Min": np.random.uniform(10, 18, size=len(datas)),
        "Temperatura Média": np.random.uniform(15, 22, size=len(datas)),
        "Temperatura Max": np.random.uniform(20, 30, size=len(datas)),
        "Chuva": np.random.uniform(0, 30, size=len(datas)),
        "Umidade": np.random.uniform(60, 95, size=len(datas)),
        "Estação": np.random.choice(["Bento Gonçalves", "Caxias do Sul", "Garibaldi"], len(datas))
    })
    return dados

df = gerar_dados()
estacoes = st.multiselect("Selecione as estações:", options=df["Estação"].unique(), default=[])
if estacoes:
    df = df[df["Estação"].isin(estacoes)]

# 📈 Gráfico Candlestick (Temperaturas)
st.subheader("📊 Candlestick Climático – Temperaturas Diárias")
for est in df["Estação"].unique():
    df_est = df[df["Estação"] == est]
    fig = go.Figure(data=[go.Candlestick(
        x=df_est["Data"],
        open=df_est["Temperatura Média"],
        high=df_est["Temperatura Max"],
        low=df_est["Temperatura Min"],
        close=df_est["Temperatura Média"],
        increasing_line_color='firebrick', decreasing_line_color='blue'
    )])
    fig.update_layout(title=f"Temperaturas - {est}", xaxis_title="Data", yaxis_title="°C", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

# 🌧️ Heatmap Temporal de Chuvas por Hora (exemplo com simulação)
st.subheader("🌧️ Heatmap Temporal – Distribuição de Chuva por Horário")
horas = list(range(24))
dias = df["Data"].dt.strftime("%Y-%m-%d").unique()[:10]
heat_data = np.random.rand(len(dias), len(horas)) * 30
fig_heat = px.imshow(
    heat_data, 
    labels=dict(x="Hora do Dia", y="Data", color="Chuva (mm)"),
    x=horas, 
    y=dias,
    color_continuous_scale="Blues"
)
st.plotly_chart(fig_heat, use_container_width=True)

# 🌐 Radar Chart para Umidade/Temperatura/Chuva
st.subheader("📡 Radar Chart – Comparativo Climático por Estação")
variaveis = ["Temperatura Média", "Umidade", "Chuva"]
fig_radar = go.Figure()
for est in df["Estação"].unique():
    media = df[df["Estação"] == est][variaveis].mean()
    fig_radar.add_trace(go.Scatterpolar(
        r=media.values,
        theta=variaveis,
        fill='toself',
        name=est
    ))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True)), template="plotly_dark")
st.plotly_chart(fig_radar, use_container_width=True)
