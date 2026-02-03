import streamlit as st
import pandas as pd
import io
from modules.drawings import get_drive_service

USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"

def login_screen():
    st.title("🏭 Вхід")
    with st.container(border=True):
        entry = st.text_input("Email або Логін").strip().lower()
        pwd = st.text_input("Пароль", type="password").strip()
        
        if st.button("Увійти", use_container_width=True):
            # Хардкод для вашого доступу
            if entry == "maksvel.fabb@gmail.com" and pwd == "1234":
                st.session_state.auth = {"email": entry, "role": "Супер Адмін", "login": "maksvel"}
                st.rerun()
            
            from modules.admin_module import load_csv
            u_df = load_csv(USERS_CSV_ID)
            
            # Шукаємо збіг або в email, або в login
            user = u_df[((u_df['email'].str.lower() == entry) | (u_df['login'].str.lower() == entry)) & (u_df['password'] == pwd)]
            
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Помилка входу")
