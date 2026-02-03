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
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done: _, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_csv(fh, dtype=str).fillna("")

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
    
    t1, t2, t3 = st.tabs(["👥 Користувачі", "🔑 Паролі", "💾 База"])

    with t1:
        st.subheader("Список користувачів")
        st.dataframe(u_df[['email', 'login', 'role', 'last_seen']], use_container_width=True)
        
        with st.expander("➕ Додати користувача"):
            with st.form("add_user"):
                n_email = st.text_input("Email")
                n_login = st.text_input("Логін (короткий)")
                n_pass = st.text_input("Пароль")
                n_role = st.selectbox("Роль", ["Адмін", "Менеджер", "Виробництво"])
                if st.form_submit_button("Зберегти"):
                    new_u = pd.DataFrame([{'email': n_email, 'login': n_login, 'password': n_pass, 'role': n_role, 'last_seen': ''}])
                    u_df = pd.concat([u_df, new_u], ignore_index=True)
                    save_csv(USERS_CSV_ID, u_df)
                    st.rerun()

    with t2:
        st.subheader("Зміна пароля")
        target = st.selectbox("Оберіть користувача", u_df['email'].values)
        new_pwd = st.text_input("Новий пароль", type="password")
        if st.button("Оновити пароль"):
            u_df.loc[u_df['email'] == target, 'password'] = new_pwd
            save_csv(USERS_CSV_ID, u_df)
            st.success("Пароль оновлено ✅")

    with t3:
        if role == "Супер Адмін":
            st.subheader("Керування базою замовлень")
            if st.button("🗑️ Очистити базу (ПОТРІБНЕ ПІДТВЕРДЖЕННЯ)"):
                st.warning("Напишіть 'ВИДАЛИТИ' в полі нижче")
            confirm = st.text_input("Підтвердження")
            if confirm == "ВИДАЛИТИ" and st.button("ПІДТВЕРДИТИ ВИДАЛЕННЯ"):
                empty_df = pd.DataFrame(columns=['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])
                save_csv(ORDERS_CSV_ID, empty_df)
                st.success("Базу очищено")
