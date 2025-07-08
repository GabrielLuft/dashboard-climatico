import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import time, date

st.set_page_config(page_title="Dashboard Climático Técnico", layout="wide", page_icon="🌦️")

sheet_url = "https://docs.google.com/spreadsheets/d/1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA/export?format=csv&gid=1136868112"

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(sheet_url)
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['Hora'] = pd.to_datetime(df['Hora'], format='%H:%M', errors='coerce').dt.time
    df['DataHora'] = pd.to_datetime(df['Data'].astype(str) + ' ' + df['Hora'].astype(str), errors='coerce')
    return df.dropna(subset=['DataHora'])

df = load_data()

def safe_date(d):
    from datetime import date
    if pd.isna(d):
        return date.today()
    if isinstance(d, pd.Timestamp):
        return d.date()
    if isinstance(d, date):
        return d
    return date.today()

if df.empty or df['Data'].isnull().all():
    data_min_val = date.today()
    data_max_val = date.today()
else:
    data_min_val = safe_date(df['Data'].min())
    data_max_val = safe_date(df['Data'].max())

st.title("🌦️ Dashboard Climático Técnico Avançado")

# Sidebar - filtros
st.sidebar.header("Filtros")

variaveis = st.sidebar.multiselect(
    "Selecione 1 a 3 variáveis para visualização",
    ['Temperatura', 'Umidade', 'Chuva', 'Radiação'],
    default=['Temperatura']
)

data_inicio = st.sidebar.date_input("Data Início", data_min_val)
data_fim = st.sidebar.date_input("Data Fim", data_max_val)

hora_inicio = st.sidebar.time_input("Hora Início", time(0,0))
hora_fim = st.sidebar.time_input("Hora Fim", time(23,59))

df_filtrado = df[
    (df['Data'] >= pd.to_datetime(data_inicio)) &
    (df['Data'] <= pd.to_datetime(data_fim)) &
    (df['Hora'] >= hora_inicio) &
    (df['Hora'] <= hora_fim)
]

if len(variaveis) == 0:
    st.warning("Selecione pelo menos uma variável para visualização.")
    st.stop()

st.markdown(f"### Visualizando variáveis: {', '.join(variaveis)}")
st.markdown(f"**Período:** {data_inicio} {hora_inicio} até {data_fim} {hora_fim}")

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para o filtro selecionado.")
    st.stop()

# Layout em abas para 2D e 3D
tabs = st.tabs(["Visualização 2D", "Visualização 3D"])

with tabs[0]:
    st.subheader("Gráfico 2D - Variáveis sobrepostas")
    fig = go.Figure()
    cores = px.colors.qualitative.Dark24
    for i, var in enumerate(variaveis):
        fig.add_trace(go.Scatter(
            x=df_filtrado['DataHora'], y=df_filtrado[var],
            mode='lines+markers',
            name=var,
            line=dict(color=cores[i % len(cores)], width=2),
            marker=dict(size=4)
        ))
    fig.update_layout(
        title="Variáveis Climáticas Sobrepostas ao Longo do Tempo",
        xaxis_title="Data e Hora",
        yaxis_title="Valores",
        legend_title="Variáveis",
        template="plotly_dark",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    if len(variaveis) == 3:
        st.subheader("Gráfico 3D - Dispersão dos 3 parâmetros")
        fig3d = px.scatter_3d(
            df_filtrado,
            x=variaveis[0],
            y=variaveis[1],
            z=variaveis[2],
            color='DataHora',
            title=f"Dispersão 3D: {variaveis[0]} x {variaveis[1]} x {variaveis[2]}",
            labels={variaveis[0]: variaveis[0], variaveis[1]: variaveis[1], variaveis[2]: variaveis[2]},
            color_continuous_scale=px.colors.sequential.Viridis,
            opacity=0.8
        )
        st.plotly_chart(fig3d, use_container_width=True)
    else:
        st.info("Selecione exatamente 3 variáveis para visualizar o gráfico 3D.")

# Exportar dados filtrados
if st.sidebar.button("Exportar tabela filtrada (CSV)"):
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(label="Clique para baixar CSV", data=csv, file_name='dados_filtrados.csv', mime='text/csv')

with st.expander("Ver dados filtrados"):
    st.dataframe(df_filtrado)
