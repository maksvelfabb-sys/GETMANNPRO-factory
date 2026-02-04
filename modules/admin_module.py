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
    
    # Використовуємо тільки ті колонки, які точно є (після нашої перевірки вище)
    display_cols = ['email', 'login', 'role', 'last_seen']
    
    t1, t2, t3 = st.tabs(["👥 Користувачі", "🔑 Паролі", "💾 База"])

    with t1:
        st.subheader("Список користувачів")
        if not u_df.empty:
            st.dataframe(u_df[display_cols], use_container_width=True)
        
        with st.expander("➕ Додати користувача"):
            with st.form("add_user"):
                n_email = st.text_input("Email")
                n_login = st.text_input("Логін (короткий)")
                n_pass = st.text_input("Пароль")
                n_role = st.selectbox("Роль", ["Адмін", "Менеджер", "Виробництво"])
                if st.form_submit_button("Зберегти"):
                    if n_email and n_login:
                        new_u = pd.DataFrame([{'email': n_email, 'login': n_login, 'password': n_pass, 'role': n_role, 'last_seen': ''}])
                        u_df = pd.concat([u_df, new_u], ignore_index=True)
                        save_csv(USERS_CSV_ID, u_df)
                        st.success("Користувача додано!")
                        st.rerun()
                    else:
                        st.warning("Заповніть Email та Логін")

    with t2:
        st.subheader("Зміна пароля")
        if not u_df.empty:
            target = st.selectbox("Оберіть користувача", u_df['email'].values)
            new_pwd = st.text_input("Новий пароль", type="password")
            if st.button("Оновити пароль"):
                u_df.loc[u_df['email'] == target, 'password'] = new_pwd
                save_csv(USERS_CSV_ID, u_df)
                st.success("Пароль оновлено ✅")

with t3:
        if role in ["Адмін", "Супер Адмін"]:
            st.subheader("💾 Керування базою замовлень")
            st.warning("⚠️ УВАГА: Очищення видалить ВСІ замовлення та ВСІ товари з бази!")
            
            confirm = st.text_input("Напишіть 'ВИДАЛИТИ' для підтвердження")
            
            if st.button("🔥 Очистити повну базу") and confirm == "ВИДАЛИТИ":
                # 1. Очищення основної таблиці (Headers)
                empty_headers = pd.DataFrame(columns=[
                    'ID', 'Дата', 'Менеджер', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Сума', 'Готовність', 'Коментар'
                ])
                save_csv(ORDERS_CSV_ID, empty_headers)
                
                # 2. Очищення таблиці товарів (Items)
                # ID: 1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1
                empty_items = pd.DataFrame(columns=[
                    'order_id', 'назва', 'арт', 'ціна', 'к-ть', 'сума'
                ])
                save_csv("1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1", empty_items)
                
                st.success("Базу замовлень та товарів повністю очищено! ✨")
                st.rerun()
