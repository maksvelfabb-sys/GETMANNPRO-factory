import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2 import service_account

# ID файлів
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
ITEMS_CSV_ID = "1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1"

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
        st.error(f"Помилка завантаження: {e}")
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
    except Exception as e:
        st.error(f"Помилка запису: {e}")
        return False

def get_file_link_by_name(file_name):
    """Шукає файл на Drive за назвою та повертає посилання"""
    if not file_name or str(file_name).strip() == "":
        return None
    try:
        service = get_drive_service()
        if not service: return None
        query = f"name contains '{str(file_name).strip()}' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, webViewLink)", pageSize=1).execute()
        files = results.get('files', [])
        return files[0]['webViewLink'] if files else None
    except Exception:
        return None
