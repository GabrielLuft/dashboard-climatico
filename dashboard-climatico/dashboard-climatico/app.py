
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import time

st.set_page_config(page_title="Dashboard Climático", layout="wide")

# URL para CSV exportado da Google Sheets (sua planilha)
sheet_url = "https://docs.google.com/spreadsheets/d/1EKvWxwZiEnY4mqsUkc9HV0bLr4eGjZvKn-Q2Zc66hcQ/export?format=csv&gid=1136868112"

@st.cache_data(ttl=600)  # cacheia por 10 minutos para não carregar sempre
def load_data():
    df = pd.read_csv(sheet_url)
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['Hora'] = pd.to_datetime(df['Hora'], format='%H:%M:%S', errors='coerce').dt.time
    df['DataHora'] = pd.to_datetime(df['Data'].astype(str) + ' ' + df['Hora'].astype(str), errors='coerce')
    return df.dropna(subset=['DataHora'])

df = load_data()

st.title("🌦️ Dashboard Climático Interativo")

# Filtros sidebar
st.sidebar.header("Filtros")

variavel = st.sidebar.selectbox("Selecione a variável", ['Temperatura', 'Umidade', 'Chuva', 'Radiação'])

data_inicio = st.sidebar.date_input("Data Início", df['Data'].min().date())
data_fim = st.sidebar.date_input("Data Fim", df['Data'].max().date())

hora_inicio = st.sidebar.time_input("Hora Início", time(0,0))
hora_fim = st.sidebar.time_input("Hora Fim", time(23,59))

# Filtro por período e hora
df_filtrado = df[
    (df['Data'] >= pd.to_datetime(data_inicio)) &
    (df['Data'] <= pd.to_datetime(data_fim)) &
    (df['Hora'] >= hora_inicio) &
    (df['Hora'] <= hora_fim)
]

st.markdown(f"### Visualizando: {variavel} de {data_inicio} {hora_inicio} até {data_fim} {hora_fim}")

# Gráfico linha interativo
fig = px.line(df_filtrado, x='DataHora', y=variavel,
              title=f'{variavel} ao longo do tempo',
              labels={variavel: variavel, 'DataHora': 'Data e Hora'},
              template='plotly_white')
st.plotly_chart(fig, use_container_width=True)

# Média móvel simples opcional
if st.sidebar.checkbox("Mostrar média móvel 3 horas"):
    df_filtrado = df_filtrado.sort_values('DataHora')
    df_filtrado[f'{variavel} - Média Móvel 3h'] = df_filtrado[variavel].rolling(window=3).mean()
    fig_mm = px.line(df_filtrado, x='DataHora', y=[variavel, f'{variavel} - Média Móvel 3h'],
                     title=f'{variavel} e Média Móvel 3 horas',
                     labels={'value': variavel, 'DataHora': 'Data e Hora'},
                     template='plotly_white')
    st.plotly_chart(fig_mm, use_container_width=True)

# Exportar tabela filtrada
if st.sidebar.button("Exportar tabela filtrada (CSV)"):
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(label="Clique para baixar CSV", data=csv, file_name='dados_filtrados.csv', mime='text/csv')

# Mostrar tabela de dados filtrados
with st.expander("Ver dados filtrados"):
    st.dataframe(df_filtrado)
