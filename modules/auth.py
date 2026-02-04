import streamlit as st
from streamlit_cookies_controller import CookieController
from modules.admin_module import load_csv

controller = CookieController()
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"

def login_screen():
    # 1. Перевіряємо куки при завантаженні
    saved_user = controller.get('getmann_auth_user')
    
    if saved_user and 'auth' not in st.session_state:
        df = load_csv(USERS_CSV_ID)
        user_row = df[df['email'] == saved_user]
        if not user_row.empty:
            st.session_state.auth = user_row.iloc[0].to_dict()
            st.rerun()

    # 2. Якщо не авторизований — показуємо форму
    st.title("🔐 Вхід у систему")
    email = st.text_input("Email")
    password = st.text_input("Пароль", type="password")

    if st.button("Увійти"):
        df = load_csv(USERS_CSV_ID)
        user = df[(df['email'] == email) & (df['password'] == str(password))]
        
        if not user.empty:
            auth_data = user.iloc[0].to_dict()
            st.session_state.auth = auth_data
            
            # ЗАПИСУЄМО В КУКИ (на 7 днів)
            controller.set('getmann_auth_user', email)
            
            st.success("Вхід успішний!")
            st.rerun()
        else:
            st.error("Невірний email або пароль")

def logout():
    controller.remove('getmann_auth_user')
    st.session_state.clear()
    st.rerun()
