import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2 import service_account

# КОНСТАНТИ (Перевірте, щоб назви збігалися з імпортом)
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
ITEMS_CSV_ID = "1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1"

def get_drive_service():
    """Створює сервіс для роботи з Google Drive API"""
    try:
        creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Помилка авторизації Google: {e}")
        return None

def load_csv(file_id):
    """Завантажує CSV файл з Google Drive"""
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
        st.error(f"Помилка завантаження файлу {file_id}: {e}")
        return pd.DataFrame()

def save_csv(file_id, df):
    """Зберігає Pandas DataFrame у CSV файл на Google Drive"""
    try:
        service = get_drive_service()
        if not service: return False
        
        csv_data = df.to_csv(index=False)
        fh = io.BytesIO(csv_data.encode())
        media = MediaFileUpload(fh, mimetype='text/csv', resumable=True)
        service.files().update(fileId=file_id, media_body=media).execute()
        return True
    except Exception as e:
        st.error(f"Помилка збереження файлу {file_id}: {e}")
        return False
        
