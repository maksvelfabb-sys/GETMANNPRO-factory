import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2 import service_account

# Ідентифікатори файлів Google Drive (ваші стабільні ID)
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
ITEMS_CSV_ID = "1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1"

def get_drive_service():
    """Створює автентифіковане з'єднання з Google Drive API"""
    try:
        # Перевірка наявності секретів у Streamlit Cloud
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Секрети GCP не знайдені в налаштуваннях Streamlit Cloud.")
            return None
            
        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(creds_info)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"❌ Помилка ініціалізації Google Drive: {e}")
        return None

def load_csv(file_id):
    """Завантажує дані з Google Drive і повертає Pandas DataFrame"""
    try:
        service = get_drive_service()
        if not service:
            return pd.DataFrame()
            
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            
        fh.seek(0)
        # Читаємо CSV, автоматично обробляючи роздільники
        return pd.read_csv(fh)
    except Exception as e:
        st.error(f"❌ Помилка завантаження файлу (ID: {file_id}): {e}")
        return pd.DataFrame()

def save_csv(file_id, df):
    """Зберігає DataFrame у CSV файл на Google Drive (через буфер пам'яті)"""
    try:
        service = get_drive_service()
        if not service:
            return False
            
        # Конвертуємо DataFrame у текстовий потік CSV
        csv_string = df.to_csv(index=False)
        # Перетворюємо в байти (BytesIO) для передачі через API
        fh = io.BytesIO(csv_string.encode('utf-8'))
        
        # ВИПРАВЛЕНО: Використовуємо MediaIoBaseUpload замість MediaFileUpload
        # Це дозволяє працювати з даними в пам'яті без створення тимчасових файлів на диску
        media = MediaIoBaseUpload(fh, mimetype='text/csv', resumable=True)
        
        # Виконуємо запит на оновлення існуючого файлу
        service.files().update(
            fileId=file_id, 
            media_body=media
        ).execute()
        
        return True
    except Exception as e:
        st.error(f"❌
