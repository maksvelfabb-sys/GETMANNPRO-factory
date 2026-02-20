import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2 import service_account

# ID файлів (Переконайтеся, що вони вірні)
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
ITEMS_CSV_ID = "1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1"
# ID вашого файлу-реєстру імен креслень
DRAWINGS_MAP_CSV_ID = "1X_J_INSERT_YOUR_MAP_CSV_ID_HERE" 

def get_drive_service():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Секрети не знайдені!")
            return None
        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(creds_info)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Помилка Drive: {e}")
        return None

def load_csv(file_id):
    if not file_id: return pd.DataFrame()
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
    except Exception:
        return pd.DataFrame()

def save_csv(file_id, df):
    try:
        service = get_drive_service()
        if not service: return False
        csv_string = df.to_csv(index=False)
        fh = io.BytesIO(csv_string.encode('utf-8'))
        media = MediaIoBaseUpload(fh, mimetype='text/csv', resumable=True)
        service.files().update(fileId=file_id, media_body=media).execute()
        return True
    except Exception:
        return False

# --- ТА САМА ФУНКЦІЯ, ЯКОЇ НЕ ВИСТАЧАЛО ---
def get_all_files_in_folder(folder_id="1_INSERT_YOUR_DRAWINGS_FOLDER_ID"):
    """Отримує список усіх файлів з папки на Drive"""
    try:
        service = get_drive_service()
        if not service: return []
        
        # Запит: файли в конкретній папці, що не в кошику
        query = f"'{folder_id}' in parents and trashed = false
