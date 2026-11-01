import streamlit as st
import pandas as pd
import re
import requests
from googleapiclient.discovery import build

st.set_page_config(page_title="Influencer Leads Scraper", layout="wide")
st.title("🎯 Multi-Platform Influencer Leads Finder")

st.sidebar.header("API Credentials")
yt_api_key = st.sidebar.text_input("YouTube Data API Key", type="password")
apify_token = st.sidebar.text_input("Apify API Token (IG/TikTok)", type="password")

with st.form("scraper_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        platform = st.selectbox("Platform", ["YouTube", "Instagram", "TikTok"])
        query = st.text_input("Search Keyword / Niche", "unboxing amazon tech")
    with col2:
        min_subs = st.number_input("Min Followers", value=1000, step=500)
        max_subs = st.number_input("Max Followers", value=10000, step=1000)
    with col3:
        max_results = st.slider("Creators Limit", min_value=10, max_value=200, value=50)
        export_format = st.radio("Export Format", ["CSV", "JSON"])
    submit_button = st.form_submit_button("🚀 Start Scraping")

EMAIL_REGEX = r'[a-zA-Z0-9%._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

def scrape_youtube(query, min_s, max_s, limit, api_key):
    youtube = build('youtube', 'v3', developerKey=api_key)
    results = []
    search_res = youtube.search().list(q=query, type='channel', part='id,snippet', maxResults=limit).execute()
    for item in search_res.get('items', []):
        ch_id = item['id']['channelId']
        ch_info = youtube.channels().list(id=ch_id, part='snippet,statistics').execute()['items'][0]
        subs = int(ch_info['statistics'].get('subscriberCount', 0))
        if min_s <= subs <= max_s:
            desc = ch_info['snippet']['description']
            emails = re.findall(EMAIL_REGEX, desc)
            custom_url = ch_info['snippet'].get('customUrl', '')
            results.append({
                "Platform": "YouTube",
                "Username": ch_info['snippet']['title'],
                "Followers": subs,
                "Email": emails[0] if emails else "N/A",
                "URL": f"https://www.youtube.com/{custom_url}" if custom_url else f"https://youtube.com/channel/{ch_id}",
                "Bio": desc[:200].replace("\n", " ")
            })
    return results

def scrape_apify(platform_name, query, min_s, max_s, limit, token):
    actor_id = "automation_studio/tiktok-email-scraper" if platform_name == "TikTok" else "apify/instagram-scraper"
    url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items?token={token}"
    payload = {"searchKeywords": query, "maxItems": limit}
    res = requests.post(url, json=payload).json()
    results = []
    if isinstance(res, list):
        for item in res:
            followers = item.get("followersCount", item.get("followers", 0))
            if min_s <= followers <= max_s:
                bio = item.get("biography", item.get("bio", ""))
                emails = re.findall(EMAIL_REGEX, bio)
                email = item.get("email") or (emails[0] if emails else "N/A")
                results.append({
                    "Platform": platform_name,
                    "Username": item.get("username", item.get("name")),
                    "Followers": followers,
                    "Email": email,
                    "URL": item.get("url") or f"https://{platform_name.lower()}.com/@{item.get('username')}",
                    "Bio": bio[:200].replace("\n", " ")
                })
    return results

if submit_button:
    st.info(f"Processing {platform} for '{query}'...")
    data = []
    if platform == "YouTube":
        if not yt_api_key:
            st.error("Missing YouTube Data API Key")
        else:
            data = scrape_youtube(query, min_subs, max_subs, max_results, yt_api_key)
    elif platform in ["Instagram", "TikTok"]:
        if not apify_token:
            st.error("Missing Apify Token")
        else:
            data = scrape_apify(platform, query, min_subs, max_subs, max_results, apify_token)

    if data:
        df = pd.DataFrame(data)
        st.success(f"Found {len(df)} leads!")
        st.dataframe(df)
        if export_format == "CSV":
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv_data, "leads.csv", "text/csv")
        else:
            json_data = df.to_json(orient="records").encode('utf-8')
            st.download_button("📥 Download JSON", json_data, "leads.json", "application/json")
    else:
        st.warning("No records found matching criteria.")