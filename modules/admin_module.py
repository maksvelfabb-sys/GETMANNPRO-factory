import streamlit as st
import pandas as pd
import io
from datetime import datetime
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from modules.drawings import get_drive_service

USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f" # Файл користувачів
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i" # Файл замовлень

def load_csv(file_id):
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done: _, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_csv(fh, dtype=str).fillna("")

def save_csv(file_id, df):
    service = get_drive_service()
    csv_data = df.to_csv(index=False).encode('utf-8')
    media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv')
    service.files().update(fileId=file_id, media_body=media_body).execute()

def show_admin_panel():
    role = st.session_state.auth.get('role')
    st.header(f"🔐 Адмін-панель ({role})")
    
    tab_users, tab_db = st.tabs(["👥 Користувачі", "💾 База даних"])

    # --- ВКЛАДКА КОРИСТУВАЧІВ (Для Адмінів та Супер Адмінів) ---
    with tab_users:
        u_df = load_csv(USERS_CSV_ID)
        
        st.subheader("Список користувачів та активність")
        # Додаємо статус "В мережі", якщо активність була менше 5 хв тому
        st.dataframe(u_df[['email', 'role', 'last_seen']], use_container_width=True)

        st.divider()
        st.subheader("➕ Додати нового користувача")
        with st.form("add_user_form"):
            new_email = st.text_input("Email (Логін)")
            new_pwd = st.text_input("Пароль")
            new_role = st.selectbox("Роль", ["Адмін", "Менеджер", "Виробництво"])
            if st.form_submit_button("Додати"):
                if new_email in u_df['email'].values:
                    st.error("Користувач вже існує!")
                else:
                    new_u = pd.DataFrame([{'email': new_email, 'password': new_pwd, 'role': new_role, 'last_seen': ''}])
                    u_df = pd.concat([u_df, new_u], ignore_index=True)
                    save_csv(USERS_CSV_ID, u_df)
                    st.success("Користувача додано!"); st.rerun()

        st.divider()
        st.subheader("🗑️ Видалити користувача")
        user_to_del = st.selectbox("Виберіть користувача", u_df['email'].values)
        if st.button("Видалити користувача", type="primary"):
            if user_to_del == "maksvel.fabb@gmail.com":
                st.error("Неможливо видалити головного Супер Адміна!")
            else:
                u_df = u_df[u_df['email'] != user_to_del]
                save_csv(USERS_CSV_ID, u_df)
                st.success("Видалено!"); st.rerun()

    # --- ВКЛАДКА БАЗИ ДАНИХ (Тільки для Супер Адміна) ---
    with tab_db:
        if role == "Супер Адмін":
            st.subheader("Керування базою замовлень")
            
            # Збереження (скачування)
            df_orders = load_csv(ORDERS_CSV_ID)
            csv_buffer = io.BytesIO()
            df_orders.to_csv(csv_buffer, index=False)
            st.download_button(
                label="📥 Скачати резервну копію (CSV)",
                data=csv_buffer.getvalue(),
                file_name=f"backup_orders_{datetime.now().strftime('%d_%m_%Y')}.csv",
                mime="text/csv"
            )
            
            st.divider()
            st.subheader("⚠️ Небезпечна зона")
            confirm = st.text_input("Напишіть 'ВИДАЛИТИ' для очищення всієї бази замовлень")
            if st.button("🗑️ Очистити базу замовлень", type="primary"):
                if confirm == "ВИДАЛИТИ":
                    empty_df = pd.DataFrame(columns=['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])
                    save_csv(ORDERS_CSV_ID, empty_df)
                    st.success("Базу очищено!"); st.rerun()
                else:
                    st.warning("Підтвердження невірне")
        else:
            st.info("Доступ до операцій з базою даних має лише Супер Адмін.")
