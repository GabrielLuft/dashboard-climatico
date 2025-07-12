import pandas as pd
import numpy as np
from geopy.distance import geodesic
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import HeatMap

# URLs públicas CSV das abas da planilha
URLS_CSV = {
    "Garibaldi": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSgn6_JkQwlFg8EVWQvX0Tv-wZSY3sqH5k-k10Y3XrCgrkHWf-Ewq6R85a0w2KmLLQQ/pub?gid=1136868112&single=true&output=csv",
    "Bento Gonçalves": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSgn6_JkQwlFg8EVWQvX0Tv-wZSY3sqH5k-k10Y3XrCgrkHWf-Ewq6R85a0w2KmLLQQ/pub?gid=1948457634&single=true&output=csv",
    "Farroupilha": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSgn6_JkQwlFg8EVWQvX0Tv-wZSY3sqH5k-k10Y3XrCgrkHWf-Ewq6R85a0w2KmLLQQ/pub?gid=651276718&single=true&output=csv",
    "Monte Belo": "https://docs.google.com/spreadsheets/d/e/2PACX-1vSgn6_JkQwlFg8EVWQvX0Tv-wZSY3sqH5k-k10Y3XrCgrkHWf-Ewq6R85a0w2KmLLQQ/pub?gid=1776247071&single=true&output=csv"
}

def carregar_dados_estacoes():
    """
    Carrega os dados das estações a partir dos links CSV públicos,
    faz o tratamento dos nomes das colunas e converte datas.
    Retorna dict com DataFrames por estação.
    """
    estacoes = {}
    for est, url in URLS_CSV.items():
        df = pd.read_csv(url)
        # Renomear colunas para nomes uniformes
        df.rename(columns={
            'Carimbo de data/hora': 'Carimbo',
            'Data': 'Data',
            'Hora': 'Hora',
            'Umidade': 'Umidade',
            'Temperatura': 'Temperatura',
            'Chuva': 'Chuva',
            'Radiação': 'Radiacao'
        }, inplace=True)
        
        # Converter coluna Data para datetime
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        # Converter coluna Hora para hora do dia (int)
        df['Hora'] = pd.to_datetime(df['Hora'], errors='coerce').dt.hour
        
        # Filtrar linhas com data inválida ou temperatura nula
        df = df.dropna(subset=['Data', 'Temperatura'])
        
        estacoes[est] = df.reset_index(drop=True)
    return estacoes

def localizar_estacao_proxima(lat_user, lon_user, estacoes_coords):
    menor_dist = float("inf")
    estacao_mais_proxima = None
    for nome, (lat, lon) in estacoes_coords.items():
        dist = geodesic((lat_user, lon_user), (lat, lon)).kilometers
        if dist < menor_dist:
            menor_dist = dist
            estacao_mais_proxima = nome
    return estacao_mais_proxima

def heatmap_temporal(df):
    # Agrupa por Data e Hora para média da temperatura
    heat_data = df.groupby(['Data', 'Hora'])['Temperatura'].mean().unstack()
    fig = px.imshow(
        heat_data,
        labels=dict(x="Hora do dia", y="Data", color="Temperatura (°C)"),
        aspect='auto',
        color_continuous_scale="Viridis"
    )
    fig.update_layout(height=400, margin=dict(t=30, b=30))
    return fig

def radar_chart_comparativo(estacoes):
    medias = {}
    for nome, df in estacoes.items():
        medias[nome] = df[['Temperatura', 'Umidade', 'Radiacao', 'Chuva']].mean()
    radar_df = pd.DataFrame(medias).T.fillna(0)
    
    fig = go.Figure()
    for var in radar_df.columns:
        fig.add_trace(go.Scatterpolar(
            r=radar_df[var].values,
            theta=radar_df.index,
            name=var,
            fill='toself'
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=True,
        height=500
    )
    return fig

from io import BytesIO
def exportar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Dados filtrados")
    output.seek(0)
    return output.read()

def mapa_interpolado(estacoes_coords, estacoes):
    media_lat = np.mean([lat for lat, lon in estacoes_coords.values()])
    media_lon = np.mean([lon for lat, lon in estacoes_coords.values()])
    mapa = folium.Map(location=[media_lat, media_lon], zoom_start=9)
    
    pontos = []
    for est, coords in estacoes_coords.items():
        df = estacoes.get(est)
        if df is not None and not df.empty:
            df_ultimo = df.sort_values('Data').iloc[-1]
            temp_media = df_ultimo['Temperatura']
            pontos.append([coords[0], coords[1], temp_media])
            folium.CircleMarker(
                location=[coords[0], coords[1]],
                radius=8,
                popup=f"{est}: {temp_media:.1f}°C",
                color="red",
                fill=True,
                fill_color="red"
            ).add_to(mapa)
    if pontos:
        HeatMap(pontos, radius=60, blur=30).add_to(mapa)
    return mapa

def boxplot_temporal(df):
    df['Semana'] = df['Data'].dt.isocalendar().week
    fig = px.box(df, x='Semana', y='Temperatura', points='all',
                 labels={'Semana': 'Semana do Ano', 'Temperatura': 'Temperatura (°C)'})
    fig.update_layout(height=400, margin=dict(t=30, b=30))
    return fig

def espaguete_3d(df):
    df_sorted = df.sort_values('Data')
    datas = df_sorted['Data'].dt.strftime('%Y-%m-%d').tolist()
    temps = df_sorted['Temperatura'].tolist()
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=list(range(len(datas))),
        y=[1]*len(datas),
        z=temps,
        mode='lines+markers',
        line=dict(color='firebrick', width=4),
        marker=dict(size=4),
        name='Temperatura'
    ))
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Tempo (dias)', tickvals=list(range(len(datas))), ticktext=datas, tickangle=45),
            yaxis=dict(title='Estação', tickvals=[1], ticktext=['Estação Selecionada']),
            zaxis=dict(title='Temperatura (°C)')
        ),
        height=500,
        margin=dict(t=40, b=40)
    )
    return fig
