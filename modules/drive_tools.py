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
# Додайте сюди ID створеного вами CSV для мапінгу
DRAWINGS_MAP_CSV_ID = "ТУТ_ВАШ_НОВИЙ_ID" 

def get_drive_service():
    try:
        if "gcp_service_account" not in st.secrets:
            st.error("Секрети не знайдені в Streamlit Secrets!")
            return None
        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(creds_info)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Помилка сервісу Drive: {e}")
        return None

# ГАРАНТОВАНО ДОДАЄМО load_csv
def load_csv(file_id):
    """Завантажує будь-який CSV файл з Google Drive за його ID"""
    if not file_id or len(file_id) < 5:
        return pd.DataFrame()
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
        # Вказуємо кодування, щоб уникнути помилок з кирилицею
        return pd.read_csv(fh, encoding='utf-8')
    except Exception as e:
        # Не виводимо помилку, якщо файл просто порожній
        return pd.DataFrame()

def save_csv(file_id, df):
    """Зберігає DataFrame у CSV файл на Google Drive"""
    try:
        service = get_drive_service()
        if not service: return False
        
        csv_string = df.to_csv(index=False)
        fh = io.BytesIO(csv_string.encode('utf-8'))
        media = MediaIoBaseUpload(fh, mimetype='text/csv', resumable=True)
        
        service.files().update(fileId=file_id, media_body=media).execute()
        return True
    except Exception as e:
        st.error(f"Помилка запису CSV: {e}")
        return False

def get_file_link_by_name(file_name):
    """Шукає файл за назвою (для сумісності зі старим кодом)"""
    if not file_name: return None
    try:
        service = get_drive_service()
        if not service: return None
        query = f"name contains '{str(file_name).strip()}' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, webViewLink)", pageSize=1).execute()
        files = results.get('files', [])
        return files[0]['webViewLink'] if files else None
    except:
        return None

# --- НОВІ ФУНКЦІЇ ДЛЯ АВТО-КРЕСЛЕНЬ ---

def load_drawing_map():
    """Завантажує словник {file_id: custom_name}"""
    df = load_csv(DRAWINGS_MAP_CSV_ID)
    if df.empty or 'file_id' not in df.columns:
        return {}
    return dict(zip(df['file_id'].astype(str), df['custom_name'].astype(str)))

def save_drawing_map(mapping_dict):
    """Зберігає мапінг у файл"""
    df = pd.DataFrame(list(mapping_dict.items()), columns=['file_id', 'custom_name'])
    return save_csv(DRAWINGS_MAP_CSV_ID, df)
