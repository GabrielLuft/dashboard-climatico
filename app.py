import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import time, date, timedelta
import numpy as np

st.set_page_config(page_title="Dashboard Climático Premium", layout="wide", page_icon="🌦️")

# URL da planilha CSV exportada do Google Sheets
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

st.title("🌦️ Dashboard Climático Premium")

# --- Sidebar filtros ---
st.sidebar.header("Filtros")

variaveis_disponiveis = ['Temperatura', 'Umidade', 'Chuva', 'Radiação']

# Seleção múltipla de variáveis (1 a 3)
variaveis = st.sidebar.multiselect(
    "Selecione 1 a 3 variáveis para visualização",
    variaveis_disponiveis,
    default=['Temperatura', 'Umidade']
)

data_inicio = st.sidebar.date_input("Data Início", data_min_val, min_value=data_min_val, max_value=data_max_val)
data_fim = st.sidebar.date_input("Data Fim", data_max_val, min_value=data_min_val, max_value=data_max_val)

hora_inicio = st.sidebar.slider("Hora Início", 0, 23, 0, 1, format="%02d:00")
hora_fim = st.sidebar.slider("Hora Fim", 0, 23, 23, 1, format="%02d:00")

# Ajusta hora fim >= hora inicio
if hora_fim < hora_inicio:
    st.sidebar.error("Hora Fim não pode ser menor que Hora Início.")
    st.stop()

hora_inicio_time = time(hora_inicio, 0)
hora_fim_time = time(hora_fim, 59)

# Média móvel para suavizar as séries
janela_mm = st.sidebar.slider("Janela média móvel (horas)", 1, 24, 3, 1)

# --- Filtra dados ---
df_filtrado = df[
    (df['Data'] >= pd.to_datetime(data_inicio)) &
    (df['Data'] <= pd.to_datetime(data_fim)) &
    (df['Hora'] >= hora_inicio_time) &
    (df['Hora'] <= hora_fim_time)
]

if len(variaveis) == 0:
    st.warning("Selecione pelo menos uma variável para visualização.")
    st.stop()

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para o filtro selecionado.")
    st.stop()

# --- Indicadores no topo ---
with st.container():
    col1, col2, col3, col4 = st.columns(4)
    for col, var in zip([col1, col2, col3, col4], variaveis_disponiveis):
        if var in df_filtrado.columns:
            val_min = df_filtrado[var].min()
            val_max = df_filtrado[var].max()
            val_mean = df_filtrado[var].mean()
            col.metric(label=f"{var} (mín / média / máx)",
                       value=f"{val_mean:.2f}",
                       delta=f"{val_max - val_min:.2f}")

# --- Layout gráfico com abas ---
tabs = st.tabs(["Visualização 2D", "Visualização 3D", "Matriz de Correlação"])

with tabs[0]:
    st.subheader("Gráfico 2D - Variáveis Sobrepostas com Média Móvel")
    fig = go.Figure()
    cores = px.colors.qualitative.Dark24
    for i, var in enumerate(variaveis):
        serie = df_filtrado[var].rolling(window=janela_mm).mean()
        fig.add_trace(go.Scatter(
            x=df_filtrado['DataHora'], y=serie,
            mode='lines',
            name=f"{var} (média móvel {janela_mm}h)",
            line=dict(color=cores[i % len(cores)], width=3)
        ))
    fig.update_layout(
        title="Variáveis Climáticas com Média Móvel",
        xaxis_title="Data e Hora",
        yaxis_title="Valores",
        legend_title="Variáveis",
        template="plotly_dark",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    if len(variaveis) == 3:
        st.subheader("Gráfico 3D - Dispersão com Intensidade por Radiação")
        # Usa radiação para o tamanho das bolhas, se for uma das variáveis
        tamanho_bolha = None
        if 'Radiação' in variaveis:
            tamanho_bolha = df_filtrado['Radiação']
        else:
            tamanho_bolha = np.ones(len(df_filtrado)) * 10  # tamanho fixo

        fig3d = px.scatter_3d(
            df_filtrado,
            x=variaveis[0],
            y=variaveis[1],
            z=variaveis[2],
            color='DataHora',
            size=tamanho_bolha,
            title=f"Dispersão 3D: {variaveis[0]} x {variaveis[1]} x {variaveis[2]}",
            labels={variaveis[0]: variaveis[0], variaveis[1]: variaveis[1], variaveis[2]: variaveis[2]},
            color_continuous_scale=px.colors.sequential.Viridis,
            opacity=0.8
        )
        st.plotly_chart(fig3d, use_container_width=True)
    else:
        st.info("Selecione exatamente 3 variáveis para visualizar o gráfico 3D.")

with tabs[2]:
    st.subheader("Matriz de Correlação das Variáveis Selecionadas")
    corr_df = df_filtrado[variaveis].corr()
    fig_corr = px.imshow(
        corr_df,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale=px.colors.diverging.RdBu,
        title="Matriz de Correlação",
        template="plotly_white"
    )
    st.plotly_chart(fig_corr, use_container_width=True)

# --- Exportar dados filtrados ---
if st.sidebar.button("Exportar dados filtrados CSV"):
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(label="Download CSV", data=csv, file_name='dados_filtrados.csv', mime='text/csv')

with st.expander("Ver tabela de dados filtrados"):
    st.dataframe(df_filtrado)
