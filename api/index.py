import os
import pandas as pd

def process_and_deduplicate_leads(new_data_list_or_df, master_db='all_accumulated_leads.csv', output_session='outreach_ready.csv'):
    try:
        print("🔄 [Обработка] Запуск проверки и дедупликации базы...")
        
        # 1. Приводим входящие данные к DataFrame с защитой
        if isinstance(new_data_list_or_df, list):
            df_new = pd.DataFrame(new_data_list_or_df)
        elif isinstance(new_data_list_or_df, pd.DataFrame):
            df_new = new_data_list_or_df.copy()
        else:
            print("❌ [Ошибка] Неверный формат входных данных.")
            return None

        if df_new.empty or 'Email' not in df_new.columns or 'Channel Title' not in df_new.columns:
            print("⚠️ [Предупреждение] В данных отсутствуют обязательные колонки 'Channel Title' или 'Email'.")
            return None

        # Очистка данных
        clean_new = df_new[['Channel Title', 'Email']].dropna().copy()
        clean_new['Email'] = clean_new['Email'].astype(str).str.strip().str.lower()
        clean_new['Channel Title'] = clean_new['Channel Title'].astype(str).str.strip()
        clean_new = clean_new.drop_duplicates(subset=['Email']).reset_index(drop=True)

        # 2. Проверка накопительной базы
        if os.path.exists(master_db):
            try:
                master_df = pd.read_csv(master_db, encoding='utf-8-sig')
                master_df['Email'] = master_df['Email'].astype(str).str.strip().str.lower()
                existing_emails = set(master_df['Email'])
            except Exception as e:
                print(f"⚠️ [Ошибка чтения накопительной базы, создаем заново]: {e}")
                master_df = pd.DataFrame(columns=['Channel Title', 'Email'])
                existing_emails = set()
        else:
            master_df = pd.DataFrame(columns=['Channel Title', 'Email'])
            existing_emails = set()

        # 3. Фильтрация уникальных
        unique_leads = clean_new[~clean_new['Email'].isin(existing_emails)].copy()

        if unique_leads.empty:
            print("ℹ️ [Инфо] Новых уникальных контактов нет. База актуальна.")
            return None

        # 4. Сохранение результатов
        updated_master = pd.concat([master_df, unique_leads], ignore_index=True)
        updated_master.to_csv(master_db, index=False, encoding='utf-8-sig')

        unique_leads.to_csv(output_session, index=False, encoding='utf-8-sig')

        print(f"✅ [Успех] Добавлено новых уникальных лидов: {len(unique_leads)}")
        print(f"📊 [Статистика] Всего в базе: {len(updated_master)}")
        print(f"📁 [Готово] Файл сессии сохранен: {output_session}")
        return output_session

    except Exception as e:
        print(f"❌ [Критическая ошибка скрипта]: {e}")
        return None

if __name__ == '__main__':
    print("🚀 Старт скрипта...")
    
    # Тестовые данные для проверки стабильности
    test_data = [
        {"Channel Title": "Test Channel 1", "Email": "test1@gmail.com"},
        {"Channel Title": "Test Channel 2", "Email": "test2@gmail.com"}
    ]
    
    process_and_deduplicate_leads(test_data)
