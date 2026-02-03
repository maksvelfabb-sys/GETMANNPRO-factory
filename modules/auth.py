import streamlit as st
import pandas as pd
import io
from datetime import datetime
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from modules.drawings import get_drive_service

USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"

def login_screen():
    st.title("🏭 Вхід у GETMANN ERP")
    
    with st.container(border=True):
        # Поле приймає і емейл, і логін
        identifier = st.text_input("Емейл або Логін").strip().lower()
        pwd = st.text_input("Пароль", type="password").strip()
        
        if st.button("Увійти", use_container_width=True):
            if not identifier or not pwd:
                st.warning("Заповніть всі поля")
                return

            # Спеціальний вхід для головного Супер Адміна
            if identifier == "maksvel.fabb@gmail.com" and pwd == "1234":
                st.session_state.auth = {"email": identifier, "role": "Супер Адмін", "login": "maksvel"}
                st.rerun()

            try:
                service = get_drive_service()
                request = service.files().get_media(fileId=USERS_CSV_ID)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done: _, done = downloader.next_chunk()
                fh.seek(0)
                u_df = pd.read_csv(fh, dtype=str).fillna("")

                # Пошук по двох колонках: email або login
                user = u_df[((u_df['email'].str.lower() == identifier) | 
                             (u_df['login'].str.lower() == identifier)) & 
                            (u_df['password'] == pwd)]

                if not user.empty:
                    user_data = user.iloc[0].to_dict()
                    st.session_state.auth = user_data
                    
                    # Оновлюємо час входу
                    u_df.loc[user.index, 'last_seen'] = datetime.now().strftime("%d.%m %H:%M")
                    csv_data = u_df.to_csv(index=False).encode('utf-8')
                    media = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv')
                    service.files().update(fileId=USERS_CSV_ID, media_body=media).execute()
                    
                    st.rerun()
                else:
                    st.error("❌ Невірні дані для входу")
            except Exception as e:
                st.error(f"Помилка зв'язку з базою: {e}")
