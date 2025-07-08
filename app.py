import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import time, date

st.set_page_config(page_title="Dashboard Climático", layout="wide")

sheet_url = "https://docs.google.com/spreadsheets/d/1V9s2JgyDUBitQ9eChSqrKQJ5GFG4NKHO_EOzHPm4dgA/export?format=csv&gid=1136868112"

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv(sheet_url)
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    df['Hora'] = pd.to_datetime(df['Hora'], format='%H:%M', errors='coerce').dt.time
    df['DataHora'] = pd.to_datetime(df['Data'].astype(str) + ' ' + df['Hora'].astype(str), errors='coerce')
    return df.dropna(subset=['DataHora'])

df = load_data()

# Função para extrair data com fallback seguro
def safe_date(d):
    if pd.isna(d):
        return date.today()
    if isinstance(d, pd.Timestamp):
        return d.date()
    if isinstance(d, date):
        return d
    return date.today()

# Obtenha valores mínimos e máximos com fallback para evitar NaT
if df.empty or df['Data'].isnull().all():
    data_min_val = date.today()
    data_max_val = date.today()
else:
    data_min_val = safe_date(df['Data'].min())
    data_max_val = safe_date(df['Data'].max())

st.title("🌦️ Dashboard Climático Interativo")

st.sidebar.header("Filtros")

variavel = st.sidebar.selectbox("Selecione a variável", ['Temperatura', 'Umidade', 'Chuva', 'Radiação'])

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

st.markdown(f"### Visualizando: {variavel} de {data_inicio} {hora_inicio} até {data_fim} {hora_fim}")

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para o filtro selecionado.")
else:
    fig = px.line(df_filtrado, x='DataHora', y=variavel,
                  title=f'{variavel} ao longo do tempo',
                  labels={variavel: variavel, 'DataHora': 'Data e Hora'},
                  template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

    if st.sidebar.checkbox("Mostrar média móvel 3 horas"):
        df_filtrado = df_filtrado.sort_values('DataHora')
        df_filtrado[f'{variavel} - Média Móvel 3h'] = df_filtrado[variavel].rolling(window=3).mean()
        fig_mm = px.line(df_filtrado, x='DataHora', y=[variavel, f'{variavel} - Média Móvel 3h'],
                         title=f'{variavel} e Média Móvel 3 horas',
                         labels={'value': variavel, 'DataHora': 'Data e Hora'},
                         template='plotly_white')
        st.plotly_chart(fig_mm, use_container_width=True)

    if st.sidebar.button("Exportar tabela filtrada (CSV)"):
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(label="Clique para baixar CSV", data=csv, file_name='dados_filtrados.csv', mime='text/csv')

    with st.expander("Ver dados filtrados"):
        st.dataframe(df_filtrado)
