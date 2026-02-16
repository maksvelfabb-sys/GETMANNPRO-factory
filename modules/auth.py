import streamlit as st
from streamlit_cookies_controller import CookieController
from modules.drive_tools import load_csv, save_csv, USERS_CSV_ID
from datetime import datetime

# Резервні дані
SUPER_ADMIN_EMAIL = "maksvel.fabb@gmail.com"
SUPER_ADMIN_LOGIN = "maksvel"
SUPER_ADMIN_PASS = "12345"

def check_auth():
    """Перевірка наявності авторизації у сесії"""
    return 'auth' in st.session_state

def login_screen():
    # Ініціалізація контролера кук
    controller = CookieController()
    
    # 1. Авто-вхід (якщо сесія порожня, але куки є)
    if 'auth' not in st.session_state:
        try:
            # Деякі версії використовують get_all(), деякі getAll()
            cookies = controller.get_all() if hasattr(controller, 'get_all') else controller.getAll()
            saved_user = cookies.get('getmann_auth_user')
            
            if saved_user:
                if saved_user == SUPER_ADMIN_EMAIL:
                    st.session_state.auth = {
                        'email': SUPER_ADMIN_EMAIL, 
                        'login': SUPER_ADMIN_LOGIN, 
                        'role': 'Супер Адмін'
                    }
                    st.rerun()
                
                df = load_csv(USERS_CSV_ID)
                if not df.empty:
                    user_row = df[df['email'].astype(str).str.lower().strip() == str(saved_user).lower().strip()]
                    if not user_row.empty:
                        st.session_state.auth = user_row.iloc[0].to_dict()
                        st.rerun()
        except:
            pass

    # 2. Форма входу
    st.title("🔐 GETMANN Pro | Вхід")
    
    with st.form(key="login_form_v3"): # Додано унікальний ключ
        email_input = st.text_input("Email").lower().strip()
        pass_input = st.text_input("Пароль", type="password").strip()
        submit = st.form_submit_button("Увійти", use_container_width=True)

        if submit:
            # Перевірка Супер Адміна
            if email_input == SUPER_ADMIN_EMAIL and pass_input == SUPER_ADMIN_PASS:
                st.session_state.auth = {
                    'email': SUPER_ADMIN_EMAIL, 'login': SUPER_ADMIN_LOGIN, 'role': 'Супер Адмін'
                }
                controller.set('getmann_auth_user', email_input)
                st.rerun()

            # Перевірка через базу даних
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
    controller = CookieController()
    
    # Видаляємо куку
    try:
        controller.remove('getmann_auth_user')
    except:
        pass
        
    # Очищуємо session_state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    st.rerun()
