import streamlit as st
import pandas as pd
import json
import io
from googleapiclient.http import MediaIoBaseDownload
# Відносний імпорт для роботи всередині папки modules
from .drawings import get_pdf_link, get_drive_service 

# ID вашого файлу замовлень на Google Drive
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
COLS = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']

def load_data():
    """Завантажує актуальні дані з Google Drive CSV"""
    service = get_drive_service()
    if not service:
        st.error("Не вдалося підключитися до Google Drive")
        return pd.DataFrame(columns=COLS)
    
    try:
        request = service.files().get_media(fileId=ORDERS_CSV_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        # fillna("") запобігає появі помилок з пустими клітинками
        return pd.read_csv(fh, dtype=str).fillna("")
    except Exception as e:
        st.error(f"Помилка завантаження бази: {e}")
        return pd.DataFrame(columns=COLS)

def show_orders_page(role):
    """Відображає сторінку замовлень з пошуком та картками"""
    st.header("📋 Журнал замовлень")
    
    # Завантаження даних
    df = load_data()
    
    if df.empty:
        st.info("Замовлень поки немає або база порожня.")
        return

    # Пошуковий рядок
    search = st.text_input("🔍 Швидкий пошук (ID, Клієнт, Артикул)...").lower()
    
    # Створюємо копію для відображення (нові зверху)
    df_v = df.copy().
