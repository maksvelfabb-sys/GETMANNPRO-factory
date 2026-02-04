import streamlit as st
import pandas as pd
import io
from datetime import datetime
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from modules.drawings import get_drive_service

USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"

def load_csv(file_id):
    service = get_drive_service()
    if not service: return pd.DataFrame()
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh, dtype=str).fillna("")
        
        # Автоматичне виправлення структури, якщо колонок немає
        required_cols = ['email', 'login', 'password', 'role', 'last_seen']
        if file_id == USERS_CSV_ID:
            changed = False
            for col in required_cols:
                if col not in df.columns:
                    df[col] = ""
                    changed = True
            if changed: # Зберігаємо виправлену структуру назад на Drive
                save_csv(file_id, df)
        return df
    except Exception as e:
        st.error(f"Помилка читання CSV: {e}")
        return pd.DataFrame()

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: return
    csv_data = df.to_csv(index=False).encode('utf-8')
    media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv')
    service.files().update(fileId=file_id, media_body=media_body).execute()

def show_admin_panel():
    role = st.session_state.auth.get('role')
    st.header(f"🔐 Адмін-панель")
    
    u_df = load_csv(USERS_CSV_ID)
    
    # Створюємо вкладки ТУТ
    t1, t2, t3 = st.tabs(["👥 Користувачі", "🔑 Паролі", "💾 База"])

    with t1:
        st.subheader("Список користувачів")
        # ... ваш код керування користувачами ...

    with t2:
        st.subheader("Зміна пароля")
        # ... ваш код зміни пароля ...

    with t3:
        # ТЕПЕР t3 доступна, бо ми всередині функції
        if role in ["Адмін", "Супер Адмін"]:
            st.subheader("💾 Керування базою замовлень")
            st.warning("⚠️ Очищення видалить ВСІ замовлення та товари!")
            
            confirm = st.text_input("Напишіть 'ВИДАЛИТИ' для підтвердження", key="db_clear_confirm")
            
            if st.button("🔥 Очистити повну базу") and confirm == "ВИДАЛИТИ":
                # Очищення основного файлу замовлень
                empty_headers = pd.DataFrame(columns=[
                    'ID', 'Дата', 'Менеджер', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Сума', 'Готовність', 'Коментар'
                ])
                save_csv(ORDERS_CSV_ID, empty_headers)
                
                # Очищення файлу товарів
                items_id = "1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1"
                empty_items = pd.DataFrame(columns=[
                    'order_id', 'назва', 'арт', 'ціна', 'к-ть', 'сума'
                ])
                save_csv(items_id, empty_items)
                
                st.success("Бази повністю очищені!")
                st.rerun()
