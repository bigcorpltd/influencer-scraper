import streamlit as st
import pandas as pd
import requests
import re
from googleapiclient.discovery import build

st.set_page_config(page_title="Multi-Platform Influencer Finder", layout="wide")
st.title("🎯 Multi-Platform Influencer Leads Finder")

# Инициализация базы данных в session_state
if "leads_db" not in st.session_state:
    st.session_state.leads_db = pd.DataFrame(columns=["Platform", "Channel Title", "Subscribers", "Email", "Handle", "Channel ID", "Link"])

with st.sidebar:
    st.header("API Credentials")
    yt_api_key = st.text_input("YouTube Data API Key", type="password")
    apify_token = st.text_input("Apify API Token (IG/TikTok)", type="password")
    
    st.markdown("---")
    st.header("💾 База лидов")
    total_leads = len(st.session_state.leads_db)
    st.info(f"Накоплено уникальных лидов: {total_leads}")
    
    if total_leads > 0:
        csv_all = st.session_state.leads_db.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Скачать всю базу (CSV)", csv_all, "all_accumulated_leads.csv", "text/csv")
        
        if st.button("🗑 Очистить всю базу"):
            st.session_state.leads_db = pd.DataFrame(columns=["Platform", "Channel Title", "Subscribers", "Email", "Handle", "Channel ID", "Link"])
            st.rerun()

col1, col2, col3 = st.columns(3)
with col1:
    platform = st.selectbox("Platform", ["YouTube", "Instagram", "TikTok"])
    query = st.text_input("Search Keyword / Niche", "unboxing amazon tech")

with col2:
    min_subs = st.number_input("Min Followers", value=1000, step=500)
    max_subs = st.number_input("Max Followers", value=1000000, step=10000)

with col3:
    limit = st.slider("Creators Limit", 10, 10000, 100)
    region_code = st.selectbox("Регион (YouTube Region)", ["ALL", "US", "ES", "RU", "GB", "DE", "FR", "CA", "AU"])
    relevance_language = st.selectbox("Язык контента (Relevance Language)", ["ALL", "en", "es", "ru", "fr", "de"])

keyword_filter = st.text_input("Обязательное слово в описании (оставьте пустым для отключения)", "")

def extract_email(text):
    if not text:
        return "N/A"
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0).lower() if match else "N/A"

def scrape_youtube_direct(base_query, min_s, max_s, target_limit, api_key, region, lang, kw_filter):
    youtube = build('youtube', 'v3', developerKey=api_key)
    results = []
    seen_emails = set(st.session_state.leads_db['Email'].tolist()) if not st.session_state.leads_db.empty else set()
    seen_ids = set(st.session_state.leads_db['Channel ID'].tolist()) if not st.session_state.leads_db.empty else set()
    scanned_count = 0
    next_page_token = None
    
    status_text = st.empty()
    
    while len(results) < target_limit:
        try:
            search_params = {
                "q": base_query,
                "type": 'channel',
                "part": 'id,snippet',
                "maxResults": 50,
                "pageToken": next_page_token
            }
            if region != "ALL":
                search_params["regionCode"] = region
            if lang != "ALL":
                search_params["relevanceLanguage"] = lang
                
            search_req = youtube.search().list(**search_params)
            search_res = search_req.execute()
        except Exception as e:
            st.error(f"Ошибка API: {str(e)}")
            break
        
        channel_ids = [item['id']['channelId'] for item in search_res.get('items', [])]
        if not channel_ids:
            break
            
        ch_req = youtube.channels().list(
            id=','.join(channel_ids),
            part='snippet,statistics'
        )
        ch_res = ch_req.execute()
        
        items = ch_res.get('items', [])
        scanned_count += len(items)
        status_text.text(f"Просканировано: {scanned_count} | Найдено новых уникальных: {len(results)}")
        
        for item in items:
            ch_id = item['id']
            if ch_id in seen_ids:
                continue
                
            subs = int(item['statistics'].get('subscriberCount', 0))
            if min_s <= subs <= max_s:
                description = item['snippet'].get('description', '')
                
                if kw_filter and kw_filter.lower() not in description.lower():
                    continue
                    
                email = extract_email(description)
                
                if email != "N/A" and email not in seen_emails:
                    seen_emails.add(email)
                    seen_ids.add(ch_id)
                    results.append({
                        "Platform": "YouTube",
                        "Channel Title": item['snippet']['title'],
                        "Subscribers": subs,
                        "Email": email,
                        "Handle": item['snippet'].get('customUrl', 'N/A'),
                        "Channel ID": ch_id,
                        "Link": f"https://www.youtube.com/channel/{ch_id}"
                    })
                    if len(results) >= target_limit:
                        break
                    
        next_page_token = search_res.get('nextPageToken')
        if not next_page_token:
            break
            
    status_text.empty()
    return pd.DataFrame(results), scanned_count

def scrape_apify(platform, query, target_limit, token):
    actor_id = "apify/instagram-scraper" if platform == "Instagram" else "clockworks/free-tiktok-scraper"
    url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={token}"
    
    payload = {"search": query, "resultsLimit": target_limit}
    try:
        res = requests.post(url, json=payload)
        if res.status_code in [200, 201]:
            st.info(f"Запрос отправлен в Apify для {platform}. Проверьте Apify Console для получения результатов.")
        else:
            st.error(f"Ошибка Apify API: {res.text}")
    except Exception as e:
        st.error(f"Ошибка подключения: {str(e)}")
    return pd.DataFrame()

if st.button("🚀 Start Scraping"):
    if platform == "YouTube":
        if not yt_api_key:
            st.error("Укажите YouTube Data API Key в сайдбаре слева")
        else:
            with st.spinner("Прямой поиск и накопление базы..."):
                df, scanned = scrape_youtube_direct(query, min_subs, max_subs, limit, yt_api_key, region_code, relevance_language, keyword_filter)
                if not df.empty:
                    st.session_state.leads_db = pd.concat([st.session_state.leads_db, df]).drop_duplicates(subset=["Email"]).reset_index(drop=True)
                    
                    st.success(f"Просканировано: {scanned} | Добавлено новых: {len(df)} | Всего в базе: {len(st.session_state.leads_db)}")
                    st.dataframe(df)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Скачать этот батч (CSV)", csv, "influencers_batch.csv", "text/csv")
                else:
                    st.warning(f"Просканировано каналов: {scanned}, но новых уникальных E-mail не найдено.")
    else:
        if not apify_token:
            st.error(f"Укажите Apify API Token в сайдбаре слева для {platform}")
        else:
            scrape_apify(platform, query, limit, apify_token)
