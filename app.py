
import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import numpy as np

def get_upload_playlist_id(youtube, channel_id):
    res = youtube.channels().list(part='contentDetails', id=channel_id).execute()
    return res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

def get_video_ids_from_playlist(youtube, playlist_id, max_results=100):
    video_ids = []
    next_page_token = None
    while len(video_ids) < max_results:
        res = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=min(50, max_results - len(video_ids)),
            pageToken=next_page_token
        ).execute()
        for item in res['items']:
            video_ids.append({
                'video_id': item['snippet']['resourceId']['videoId'],
                'title': item['snippet']['title'],
                'description': item['snippet'].get('description', '')
            })
        next_page_token = res.get('nextPageToken')
        if not next_page_token:
            break
    return video_ids

def get_video_stats(youtube, video_ids):
    stats = []
    for i in range(0, len(video_ids), 50):
        ids = [v['video_id'] for v in video_ids[i:i+50]]
        res = youtube.videos().list(part='statistics', id=','.join(ids)).execute()
        for item, base in zip(res['items'], video_ids[i:i+50]):
            stats.append({
                'video_id': item['id'],
                'title': base['title'],
                'description': base['description'],
                'views': int(item['statistics'].get('viewCount', 0))
            })
    return stats

def classify_topic(title, description):
    text = (title + ' ' + description).lower()
    if any(k in text for k in ['tutorial', 'como fazer', 'passo a passo']):
        return 'Tutoriais'
    elif any(k in text for k in ['vlog', 'minha rotina', 'dia']):
        return 'Vlogs'
    elif any(k in text for k in ['notícia', 'atualização', 'últimas']):
        return 'Notícias'
    elif any(k in text for k in ['review', 'análise', 'opinião']):
        return 'Reviews'
    elif any(k in text for k in ['curiosidades', 'fatos']):
        return 'Curiosidades'
    else:
        return 'Outro'

def analyze_videos(df):
    df['tema'] = df.apply(lambda row: classify_topic(row['title'], row['description']), axis=1)
    mediana_geral = df['views'].median()
    media_geral = df['views'].mean()

    resumo = []
    for tema in df['tema'].unique():
        subset = df[df['tema'] == tema]
        media_tema = int(subset['views'].mean())
        sucesso = subset[subset['views'] > mediana_geral]
        taxa_sucesso = f"{len(sucesso)}/{len(subset)}"
        video_rep = subset.sort_values(by='views', ascending=False).iloc[0]['title']
        resumo.append({
            'Tipo de Tema': tema,
            'Nº de Vídeos Publicados': len(subset),
            'Visualizações Médias': media_tema,
            'Taxa de Sucesso': taxa_sucesso,
            'Vídeo Representativo': video_rep
        })

    return pd.DataFrame(resumo), int(media_geral), int(mediana_geral)

st.title("📊 Analisador de Canal do YouTube")
st.markdown("Obtenha estatísticas inteligentes de até 100 vídeos de um canal do YouTube.")

api_key = st.secrets["API_KEY"]
channel_id = st.text_input("📺 ID do Canal (não é a URL!)")

if api_key and channel_id:
    try:
        with st.spinner("🔍 Coletando dados..."):
            youtube = build('youtube', 'v3', developerKey=api_key)
            playlist_id = get_upload_playlist_id(youtube, channel_id)
            video_ids = get_video_ids_from_playlist(youtube, playlist_id)
            stats = get_video_stats(youtube, video_ids)
            df = pd.DataFrame(stats)
            resumo_df, media_geral, mediana_geral = analyze_videos(df)

        st.success("✅ Dados coletados com sucesso!")
        st.write(f"**Total de vídeos analisados:** {len(df)}")
        st.write(f"**Visualizações médias:** {media_geral}")
        st.write(f"**Visualizações medianas:** {mediana_geral}")

        st.markdown("### 📋 Estatísticas por Tema")
        st.dataframe(resumo_df)

        st.markdown("### 📈 Gráfico de Distribuição por Tema")
        st.bar_chart(resumo_df.set_index("Tipo de Tema")["Nº de Vídeos Publicados"])

    except Exception as e:
        st.error(f"❌ Erro: {e}")
else:
    st.info("Insira sua chave de API e ID do canal para começar.")
