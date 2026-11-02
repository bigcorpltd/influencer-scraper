import os
import re
from datetime import datetime
import pandas as pd

# ================= НАСТРОЙКИ =================
API_KEY = "ТВОЙ_API_KEY_ЗДЕСЬ"  # Вставь сюда свой API ключ Google
MASTER_FILE = "master_database.xlsx" # Единая база для проверки дублей
PLATFORM = "youtube"                 # Платформа (youtube, tiktok, instagram)
SEARCH_KEYWORDS = ["temu haul", "budget finds", "ali-express finds", "unboxing toys"]
MAX_RESULTS_PER_KEYWORD = 50
# =============================================

def load_master_emails(file_path):
    """Загружает всю накопленную базу почт из главного файла для исключения дублей."""
    if not os.path.exists(file_path):
        return set()
    try:
        df = pd.read_excel(file_path)
        if 'Email' in df.columns:
            return set(df['Email'].dropna().astype(str).str.lower().str.strip())
    except Exception as e:
        print(f"Ошибка при чтении мастер-файла: {e}")
    return set()

def extract_emails(text):
    """Ищет e-mail адреса в тексте с помощью регулярного выражения."""
    if not text:
        return []
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, text)

def main():
    youtube = build("youtube", "v3", developerKey=API_KEY)
    
    # 1. Загружаем общую базу для проверки дублей
    existing_emails = load_master_emails(MASTER_FILE)
    print(f"В общей базе уже накоплено почт: {len(existing_emails)}")
    
    new_emails_found = set()

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

            # 3. Получение описания каналов
            channels_response = youtube.channels().list(
                id=",".join(channel_ids),
                part="snippet"
            ).execute()

            # 4. Извлечение email из описаний
            for channel in channels_response.get('items', []):
                description = channel['snippet'].get('description', '')
                found_emails = extract_emails(description)
                
                for email in found_emails:
                    email_clean = email.lower().strip()
                    if email_clean not in existing_emails and email_clean not in new_emails_found:
                        new_emails_found.add(email_clean)
                        
        except Exception as e:
            print(f"Ошибка при обработке запроса '{keyword}': {e}")
            break

    # 5. Если нашли новые почты — обновляем мастер-файл и создаем отчет с датой и количеством
    if new_emails_found:
        all_emails = sorted(list(existing_emails.union(new_emails_found)))
        
        # Обновляем главный файл-накопитель
        df_master = pd.DataFrame({'Email': all_emails})
        df_master.to_excel(MASTER_FILE, index=False)
        
        # Генерируем уникальное имя файла с платформой, текущей датой, временем и количеством
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        output_filename = f"{PLATFORM}_{timestamp}_{len(new_emails_found)}_emails.xlsx"
        
        # Сохраняем файл только с новыми почтами текущего захода (или всеми, если хочешь)
        df_new = pd.DataFrame({'Email': sorted(list(new_emails_found))})
        df_new.to_excel(output_filename, index=False)
        
        print(f"Успешно! Найдено новых почт: {len(new_emails_found)}")
        print(f"Создан файл отчета: {output_filename}")
        print(f"Всего в общей базе теперь: {len(all_emails)}")
    else:
        print("Новых почт не найдено (все совпали с уже имеющейся базой).")

if __name__ == "__main__":
    main()
