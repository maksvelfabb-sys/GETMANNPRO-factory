import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2 import service_account

# Ваші ID файлів
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
ITEMS_CSV_ID = "1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1"

def get_drive_service():
    """Ініціалізація сервісу Google Drive"""
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Секрети 'gcp_service_account' не знайдені в Streamlit Secrets!")
            return None
        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(creds_info)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Помилка авторизації Google Drive: {e}")
        return None

def load_csv(file_id):
    """Завантаження CSV з Google Drive"""
    try:
        service = get_drive_service()
        if not service: return pd.DataFrame()
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return pd.read_csv(fh)
    except Exception as e:
        st.error(f"Помилка завантаження файлу: {e}")
        return pd.DataFrame()

def save_csv(file_id, df):
    """Збереження CSV на Google Drive"""
    try:
        service = get_drive_service()
        if not service: return False
        csv_string = df.to_csv(index=False)
        fh = io.BytesIO(csv_string.encode('utf-8'))
        media = MediaIoBaseUpload(fh, mimetype='text/csv', resumable=True)
        service.files().update(fileId=file_id, media_body=media).execute()
        return True
    except Exception as e:
        st.error(f"Помилка запису файлу: {e}")
        return False

def get_file_link_by_name(file_name):
    """Шукає файл на Google Drive за артикулом та повертає посилання"""
    if not file_name or str(file_name).strip() == "":
        return None
    try:
        service = get_drive_service() # Отримуємо сервіс тут
        if not service: return None
        
        # Очищуємо ім'я файлу від зайвих пробілів
        file_name = str(file_name).strip()
        
        # Пошук файлу, який називається як артикул
        query = f"name contains '{file_name}' and trashed = false"
        results = service.files().list(
            q=query, 
            fields="files(id, name, webViewLink)",
            pageSize=1
        ).execute()
        
        files = results.get('files', [])
        if files:
            return files[0]['webViewLink']
    except Exception as e:
        # Використовуємо print для логів, щоб не переривати роботу інтерфейсу Streamlit
        print(f"Помилка Drive API (пошук {file_name}): {e}")
    return None
