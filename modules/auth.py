import streamlit as st
import pandas as pd
import io
from googleapiclient.http import MediaIoBaseDownload
# Абсолютний імпорт для стабільності
from modules.drawings import get_drive_service 

USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"

def login_screen():
    st.title("🏭 Вхід у систему")
    with st.container(border=True):
        email = st.text_input("Логін (Email)").strip().lower()
        pwd = st.text_input("Пароль", type="password").strip()
        
        if st.button("Увійти", use_container_width=True):
            if email == "maksvel.fabb@gmail.com" and pwd == "1234":
                st.session_state.auth = {"email": email, "role": "Супер Адмін"}
                st.rerun()
            
            try:
                service = get_drive_service()
                request = service.files().get_media(fileId=USERS_CSV_ID)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done: _, done = downloader.next_chunk()
                fh.seek(0)
                u_df = pd.read_csv(fh, dtype=str)
                
                user = u_df[(u_df['email'] == email) & (u_df['password'] == pwd)]
                if not user.empty:
                    st.session_state.auth = user.iloc[0].to_dict()
                    st.rerun()
                else: st.error("Невірний логін або пароль")
            except Exception as e:
                st.error(f"Помилка бази: {e}")
