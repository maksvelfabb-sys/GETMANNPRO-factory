import streamlit as st
from streamlit_cookies_controller import CookieController # ДОДАЙТЕ ЦЕЙ РЯДОК
from modules.drive_tools import load_csv, save_csv, USERS_CSV_ID
from datetime import datetime

# Ваші резервні дані (Hardcoded)
SUPER_ADMIN_EMAIL = "maksvel.fabb@gmail.com"
SUPER_ADMIN_LOGIN = "maksvel"
SUPER_ADMIN_PASS = "12345"

def login_screen():
    # Ініціалізація всередині функції
    controller = CookieController()
    
    # 1. Спроба авто-входу через куки (F5)
    saved_user = None
    try:
        cookies = controller.get_all()
        if cookies:
            saved_user = cookies.get('getmann_auth_user')
    except:
        pass
    
    if saved_user and 'auth' not in st.session_state:
        # Перевірка на Супер Адміна
        if saved_user == SUPER_ADMIN_EMAIL:
            st.session_state.auth = {
                'email': SUPER_ADMIN_EMAIL,
                'login': SUPER_ADMIN_LOGIN,
                'role': 'Супер Адмін'
            }
            st.rerun()
        
        # Перевірка інших через базу
        df = load_csv(USERS_CSV_ID)
        user_row = df[df['email'].astype(str).str.lower().str.strip() == str(saved_user).lower().strip()]
        if not user_row.empty:
            st.session_state.auth = user_row.iloc[0].to_dict()
            st.rerun()

    # 2. Форма входу
    st.title("🔐 GETMANN ERP | Вхід")
    
    with st.form("login_form"):
        email_input = st.text_input("Email").lower().strip()
        pass_input = st.text_input("Пароль", type="password").strip()
        submit = st.form_submit_button("Увійти", use_container_width=True)

        if submit:
            if email_input == SUPER_ADMIN_EMAIL and pass_input == SUPER_ADMIN_PASS:
                st.session_state.auth = {
                    'email': SUPER_ADMIN_EMAIL, 'login': SUPER_ADMIN_LOGIN, 'role': 'Супер Адмін'
                }
                controller.set('getmann_auth_user', email_input)
                st.rerun()

            df = load_csv(USERS_CSV_ID)
            if not df.empty:
                df['email'] = df['email'].astype(str).str.lower().str.strip()
                df['password'] = df['password'].astype(str).str.strip()
                user = df[(df['email'] == email_input) & (df['password'] == pass_input)]
                
                if not user.empty:
                    st.session_state.auth = user.iloc[0].to_dict()
                    controller.set('getmann_auth_user', email_input)
                    st.rerun()
                else:
                    st.error("❌ Невірний email або пароль")

def logout():
    # Отримуємо контролер кук
    controller = CookieController()
    
    # Видаляємо дані з сесії
    if 'auth' in st.session_state:
        del st.session_state.auth
    
    # БЕЗПЕЧНЕ ВИДАЛЕННЯ КУКИ
    # Перевіряємо, чи є така кука в браузері перед видаленням
    all_cookies = controller.get_all()
    if 'getmann_auth_user' in all_cookies:
        try:
            controller.remove('getmann_auth_user')
        except KeyError:
            # Якщо виникла помилка, просто ігноруємо її
            pass
            
    st.rerun()
    controller = CookieController() # Ініціалізація тут
    controller.remove('getmann_auth_user')
    st.session_state.clear()
    st.rerun()
