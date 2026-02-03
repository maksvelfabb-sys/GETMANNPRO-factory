import streamlit as st
import pandas as pd
import io
from modules.drawings import get_drive_service

USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"

def load_users():
    service = get_drive_service()
    request = service.files().get_media(fileId=USERS_CSV_ID)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done: _, done = downloader.next_chunk()
    fh.seek(0)
    return pd.read_csv(fh, dtype=str).fillna("")

def save_users(df):
    service = get_drive_service()
    csv_data = df.to_csv(index=False).encode('utf-8')
    from googleapiclient.http import MediaIoBaseUpload
    media = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv')
    service.files().update(fileId=USERS_CSV_ID, media_body=media).execute()

def show_admin_panel():
    role = st.session_state.auth.get('role')
    st.header(f"🔐 Адмін-панель")
    
    u_df = load_users()
    
    tab_list, tab_edit, tab_db = st.tabs(["👥 Користувачі", "🔑 Зміна паролів", "💾 База даних"])

    with tab_list:
        st.subheader("Активність користувачів")
        st.dataframe(u_df[['email', 'login', 'role', 'last_seen']], use_container_width=True)

    with tab_edit:
        st.subheader("Встановити новий пароль")
        target_user = st.selectbox("Виберіть користувача", u_df['email'].values, key="select_user_pwd")
        new_pass = st.text_input("Новий пароль", type="password")
        
        if st.button("Оновити пароль"):
            if new_pass:
                u_df.loc[u_df['email'] == target_user, 'password'] = new_pass
                save_users(u_df)
                st.success(f"✅ Пароль для {target_user} успішно змінено!")
            else:
                st.warning("Введіть пароль")

    with tab_db:
        if role == "Супер Адмін":
            st.warning("Тут доступні функції видалення та бекапу бази.")
            # Логіка видалення бази, яку ми писали раніше...
