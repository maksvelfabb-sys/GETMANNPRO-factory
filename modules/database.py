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
    df_v = df.copy().iloc[::-1]
    
    if search:
        # Фільтрація по всіх полях
        df_v = df_v[df_v.apply(lambda r: search in str(r.values).lower(), axis=1)]

    # Вивід карток замовлень
    for idx, row in df_v.iterrows():
        with st.container(border=True):
            col_info, col_status = st.columns([3, 1])
            
            order_id = row.get('ID', '???')
            client = row.get('Клієнт', 'Невідомий')
            
            col_info.subheader(f"№{order_id} — {client}")
            col_status.write(f"**Статус:** {row.get('Готовність', 'Не вказано')}")
            
            # Декодування списку товарів з JSON
            try:
                items = json.loads(row['Товари_JSON']) if row['Товари_JSON'] else []
            except:
                items = []
            
            # Рядки з товарами
            for i, it in enumerate(items):
                c_name, c_btn = st.columns([3, 1])
                
                name = it.get('назва', 'Товар без назви')
                art = str(it.get('арт', '')).strip()
                qty = it.get('к-ть', '1')
                
                c_name.write(f"🔹 {name} (**{art}**) — {qty} шт.")
                
                # Пошук посилання на креслення через модуль drawings.py
                if art:
                    link = get_pdf_link(art)
                    if link:
                        # Використовуємо наш надійний HTML-стиль кнопки зі styles.py
                        btn_html = f'''
                            <a href="{link}" target="_blank" class="pdf-button">
                                📕 PDF
                            </a>
                        '''
                        c_btn.markdown(btn_html, unsafe_allow_html=True)
                    else:
                        c_btn.button("⌛ Немає", disabled=True, key=f"none_{order_id}_{i}", use_container_width=True)
                else:
                    c_btn.button("⚪ Без арту", disabled=True, key=f"empty_{order_id}_{i}", use_container_width=True)

            # Додаткова інформація внизу картки
            st.divider()
            c_bot1, c_bot2, c_bot3 = st.columns(3)
            c_bot1.caption(f"📅 Дата: {row.get('Дата', '-')}")
            c_bot2.caption(f"📞 Тел: {row.get('Телефон', '-')}")
            c_bot3.caption(f"🚚 ТТН: {row.get('ТТН', '-')}")
            
            if row.get('Коментар'):
                st.info(f"💬 {row['Коментар']}")
