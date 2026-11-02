from apify_client import ApifyClient

if st.button("🚀 Start Scraping"):
    if platform == "YouTube":
        if not yt_api_key:
            st.error("Укажите YouTube Data API Key в сайдбаре слева")
        else:
            with st.spinner("Экономичный поиск и накопление базы YouTube..."):
                df, scanned = scrape_youtube_optimized(query, min_subs, max_subs, limit, yt_api_key, region_code, relevance_language, keyword_filter)
                if not df.empty:
                    st.session_state.leads_db = pd.concat([st.session_state.leads_db, df]).drop_duplicates(subset=["Email"]).reset_index(drop=True)
                    st.success(f"Просканировано: {scanned} | Добавлено новых: {len(df)} | Всего в базе: {len(st.session_state.leads_db)}")
                    st.dataframe(df)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Скачать этот батч (CSV)", csv, "influencers_batch.csv", "text/csv")
                else:
                    st.warning(f"Просканировано каналов: {scanned}, но новых уникальных E-mail не найдено.")
                    
    elif platform in ["Instagram", "TikTok"]:
        if not apify_token:
            st.error("Укажите Apify API Token в сайдбаре слева")
        else:
            with st.spinner(f"Запуск Apify парсера для {platform}..."):
                try:
                    client = ApifyClient(apify_token)
                    
                    if platform == "Instagram":
                        # Используем стандартный Instagram Scraper на Apify
                        run_input = {
                            "search": query,
                            "searchType": "user",
                            "resultsLimit": limit,
                        }
                        actor_id = "apify/instagram-scraper"
                    else:
                        # Используем TikTok Scraper на Apify
                        run_input = {
                            "searchQueries": [query],
                            "resultsPerPage": limit,
                        }
                        actor_id = "clockworks/tiktok-scraper"
                        
                    run = client.actor(actor_id).call(run_input=run_input)
                    
                    # Сбор результатов из датасета Apify
                    results = []
                    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                        email = item.get("email") or extract_email(item.get("biography") or item.get("signature", ""))
                        if email and email != "N/A":
                            results.append({
                                "Platform": platform,
                                "Channel Title": item.get("fullName") or item.get("nickname") or item.get("username", "N/A"),
                                "Subscribers": item.get("followersCount") or item.get("followerCount", 0),
                                "Email": email.lower(),
                                "Handle": f"@{item.get('username') or item.get('uniqueId', 'N/A')}",
                                "Channel ID": item.get("id", "N/A"),
                                "Link": item.get("url") or f"https://www.{platform.lower()}.com/@{item.get('username', '')}"
                            })
                            
                    df_apify = pd.DataFrame(results)
                    if not df_apify.empty:
                        df_apify = df_apify.drop_duplicates(subset=["Email"])
                        st.session_state.leads_db = pd.concat([st.session_state.leads_db, df_apify]).drop_duplicates(subset=["Email"]).reset_index(drop=True)
                        st.success(f"Успешно собрано через Apify! Добавлено лидов: {len(df_apify)} | Всего в базе: {len(st.session_state.leads_db)}")
                        st.dataframe(df_apify)
                        csv = df_apify.to_csv(index=False).encode('utf-8')
                        st.download_button("📥 Скачать батч Apify (CSV)", csv, f"{platform.lower()}_leads.csv", "text/csv")
                    else:
                        st.warning("Парсер отработал, но контактов с открытыми e-mail по данному запросу не найдено.")
                        
                except Exception as e:
                    st.error(f"Ошибка при работе с Apify API: {str(e)}")
