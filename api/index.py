import streamlit as st
import pandas as pd
import requests
import re
from googleapiclient.discovery import build

st.set_page_config(page_title="Multi-Platform Influencer Finder", layout="wide")
st.title("🎯 Multi-Platform Influencer Leads Finder")

with st.sidebar:
    st.header("API Credentials")
    yt_api_key = st.text_input("YouTube Data API Key", type="password")
    apify_token = st.text_input("Apify API Token (IG/TikTok)", type="password")

col1, col2, col3 = st.columns(3)
with col1:
    platform = st.selectbox("Platform", ["YouTube", "Instagram", "TikTok"])
    query = st.text_input("Search Keyword / Niche", "unboxing amazon tech")

with col2:
    min_subs = st.number_input("Min Followers", value=1000, step=500)
    max_subs = st.number_input("Max Followers", value=10000, step=1000)

with col3:
    limit = st.slider("Creators Limit", 10, 500, 50)
    export_format = st.radio("Export Format", ["CSV", "JSON"])

def extract_email(text):
    """Поиск email в тексте с помощью регулярных выражений"""
    if not text:
        return "N/A"
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else "N/A"

def scrape_youtube_paginated(query, min_s, max_s, target_limit, api_key):
    youtube = build('youtube', 'v3', developerKey=api_key)
    results = []
    next_page_token = None
    
    while len(results) < target_limit:
        search_req = youtube.search().list(
            q=query,
            type='channel',
            part='id,snippet',
            maxResults=min(50, target_limit - len(results)),
            pageToken=next_page_token
        )
        search_res = search_req.execute()
        
        channel_ids = [item['id']['channelId'] for item in search_res.get('items', [])]
        if not channel_ids:
            break
            
        ch_req = youtube.channels().list(
            id=','.join(channel_ids),
            part='snippet,statistics'
        )
        ch_res = ch_req.execute()
        
        for item in ch_res.get('items', []):
            subs = int(item['statistics'].get('subscriberCount', 0))
            if min_s <= subs <= max_s:
                description = item['snippet'].get('description', '')
                email = extract_email(description)
                
                results.append({
                    "Platform": "YouTube",
                    "Channel Title": item['snippet']['title'],
                    "Subscribers": subs,
                    "Email": email,
                    "Handle": item['snippet'].get('customUrl', 'N/A'),
                    "Channel ID": item['id'],
                    "Link": f"https://www.youtube.com/channel/{item['id']}"
                })
                if len(results) >= target_limit:
                    break
                    
        next_page_token = search_res.get('nextPageToken')
        if not next_page_token:
            break
            
    return pd.DataFrame(results)

def scrape_apify(platform, query, target_limit, token):
    actor_id = "apify/instagram-scraper" if platform == "Instagram" else "clockworks/free-tiktok-scraper"
    url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={token}"
    
    payload = {"search": query, "resultsLimit": target_limit}
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 201 or res.status_code == 200:
            st.info(f"Запрос отправлен в Apify для {platform}. Проверьте Apify Console для получения результатов.")
        else:
            st.error(f"Ошибка Apify API: {res.text}")
    except Exception as e:
        st.error(f"Ошибка подключения к Apify: {str(e)}")
    return pd.DataFrame()

if st.button("🚀 Start Scraping"):
    if platform == "YouTube":
        if not yt_api_key:
            st.error("Укажите YouTube Data API Key в сайдбаре слева")
        else:
            with st.spinner("Сбор данных YouTube и парсинг Email..."):
                df = scrape_youtube_paginated(query, min_subs, max_subs, limit, yt_api_key)
                if not df.empty:
                    st.success(f"Найдено каналов: {len(df)}")
                    st.dataframe(df)
                    
                    # Кнопка скачивания
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Скачать CSV", csv, "influencers.csv", "text/csv")
                else:
                    st.warning("Каналы по заданным критериям не найдены.")
    else:
        if not apify_token:
            st.error(f"Укажите Apify API Token в сайдбаре слева для {platform}")
        else:
            scrape_apify(platform, query, limit, apify_token)
