import streamlit as st
import pandas as pd
import json, io
from googleapiclient.http import MediaIoBaseDownload
# Змінено на абсолютний імпорт
from modules.drawings import get_pdf_link, get_drive_service 

ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
COLS = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']

def load_data():
    service = get_drive_service()
    if not service: return pd.DataFrame(columns=COLS)
    try:
        request = service.files().get_media(fileId=ORDERS_CSV_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        return pd.read_csv(fh, dtype=str).fillna("")
    except: return pd.DataFrame(columns=COLS)

def show_orders_page(role):
    st.header("📋 Журнал замовлень")
    df = load_data()
    search = st.text_input("🔍 Пошук...").lower()
    df_v = df.iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        with st.container(border=True):
            st.subheader(f"№{row['ID']} — {row['Клієнт']}")
            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            
            for i, it in enumerate(items):
                c1, c2 = st.columns([3, 1])
                art = str(it.get('арт', '')).strip()
                c1.write(f"🔹 {it.get('назва')} (**{art}**)")
                link = get_pdf_link(art)
                if link:
                    # Використовуємо клас із styles.py
                    c2.markdown(f'<a href="{link}" target="_blank" class="pdf-button">📕 PDF</a>', unsafe_allow_html=True)
                else:
                    c2.button("⌛ Немає", disabled=True, key=f"no_{idx}_{i}")
