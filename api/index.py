import os
import re
from datetime import datetime
import pandas as pd
from googleapiclient.discovery import build

# ================= НАСТРОЙКИ =================
API_KEY = "ТВОЙ_API_KEY_ЗДЕСЬ"        # Вставь сюда свой API ключ Google
MASTER_FILE = "master_database.xlsx"  # Главная база для проверки дублей
PLATFORM = "youtube"                   # Платформа (youtube)
SEARCH_KEYWORDS = ["temu haul", "budget finds", "ali-express finds", "unboxing toys"]
MAX_RESULTS_PER_KEYWORD = 50
# =============================================

def load_master_database(file_path):
    """Загружает уже имеющиеся почты из мастер-файла для исключения дублей."""
    if not os.path.exists(file_path):
        return pd.DataFrame(columns=['Email', 'Channel Name'])
    try:
        df = pd.read_excel(file_path)
        if 'Email' in df.columns and 'Channel Name' in df.columns:
            return df
    except Exception as e:
        print(f"Ошибка при чтении мастер-файла: {e}")
    return pd.DataFrame(columns=['Email', 'Channel Name'])

def extract_emails(text):
    """Ищет e-mail адреса в тексте с помощью регулярного выражения."""
    if not text:
        return []
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, text)

def main():
    youtube = build("youtube", "v3", developerKey=API_KEY)
    
    # 1. Загружаем мастер-базу
    master_df = load_master_database(MASTER_FILE)
    existing_emails = set(master_df['Email'].dropna().astype(str).str.lower().str.strip())
    print(f"В общей базе уже накоплено контактов: {len(existing_emails)}")
    
    new_records = []
    seen_in_run = set()

    for keyword in SEARCH_KEYWORDS:
        print(f"Ищем по ключевому слову: '{keyword}'...")
        try:
            # 2. Поиск видео
            search_response = youtube.search().list(
                q=keyword,
                type="video",
                part="snippet",
                maxResults=MAX_RESULTS_PER_KEYWORD
            ).execute()

            channel_ids = [item['snippet']['channelId'] for item in search_response.get('items', [])]
            channel_ids = list(set(channel_ids))

            if not channel_ids:
                continue

            # 3. Получение данных каналов (название + описание)
            channels_response = youtube.channels().list(
                id=",".join(channel_ids),
                part="snippet"
            ).execute()

            # 4. Извлечение email и связка с названием канала
            for channel in channels_response.get('items', []):
                snippet = channel['snippet']
                channel_title = snippet.get('title', 'Unknown')
                description = snippet.get('description', '')
                
                found_emails = extract_emails(description)
                
                for email in found_emails:
                    email_clean = email.lower().strip()
                    if email_clean not in existing_emails and email_clean not in seen_in_run:
                        seen_in_run.add(email_clean)
                        new_records.append({
                            'Email': email_clean,
                            'Channel Name': channel_title
                        })
                        
        except Exception as e:
            print(f"Ошибка при обработке запроса '{keyword}': {e}")
            break

    # 5. Сохранение результатов
    if new_records:
        df_new = pd.DataFrame(new_records)
        
        # Объединяем со старой мастер-базой
        combined_df = pd.concat([master_df, df_new], ignore_index=True)
        combined_df.drop_duplicates(subset=['Email'], keep='first', inplace=True)
        
        # Обновляем главный файл
        combined_df.to_excel(MASTER_FILE, index=False)
        
        # Создаем отчетный файл для текущего запуска
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        output_filename = f"{PLATFORM}_{timestamp}_{len(new_records)}_emails.xlsx"
        df_new.to_excel(output_filename, index=False)
        
        print(f"Успешно! Найдено новых уникальных контактов: {len(new_records)}")
        print(f"Создан отчет: {output_filename}")
        print(f"Всего в общей базе теперь: {len(combined_df)}")
    else:
        print("Новых почт не найдено (все совпали с уже имеющейся базой).")

if __name__ == "__main__":
    main()
