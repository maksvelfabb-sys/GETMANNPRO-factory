import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

def get_drive_service():
    if "gcp_service_account" in st.secrets:
        try:
            info = dict(st.secrets["gcp_service_account"])
            info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
            creds = service_account.Credentials.from_service_account_info(info)
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            st.error(f"Помилка авторизації Google Drive: {e}")
            return None
    return None

def get_pdf_link(art):
    if not art or str(art).strip() in ["", "nan", "-"]: return None
    service = get_drive_service()
    if not service: return None
    try:
        q = f"'{FOLDER_DRAWINGS_ID}' in parents and name contains '{str(art).strip()}' and trashed = false"
        res = service.files().list(q=q, fields="files(webViewLink)").execute()
        files = res.get('files', [])
        return files[0]['webViewLink'] if files else None
    except:
        return None
