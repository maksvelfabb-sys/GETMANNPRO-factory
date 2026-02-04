# modules/drive_tools.py
import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2 import service_account

def get_drive_service():
    creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    return build('drive', 'v3', credentials=creds)

def load_csv(file_id):
    try:
        service = get_drive_service()
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
        csv_data = df.to_csv(index=False)
        fh = io.BytesIO(csv_data.encode())
        media = MediaFileUpload(fh, mimetype='text/csv', resumable=True)
        service.files().update(fileId=file_id, media_body=media).execute()
        return True
    except Exception as e:
        st.error(f"Помилка збереження: {e}")
        return False
