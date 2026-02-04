import streamlit as st
from streamlit_cookies_controller import CookieController
from modules.admin_module import load_csv

controller = CookieController()
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"

# ВАШІ РЕЗЕРВНІ ДАНІ (Hardcoded)
SUPER_ADMIN_EMAIL = "maksvel.fabb@gmail.com"
SUPER_ADMIN_LOGIN = "maksvel"
SUPER_ADMIN_PASS = "12345"

def login_screen():
    # 1. Спроба авто-входу через куки (F5)
    try:
        cookies = controller.get_all()
        saved_user = cookies.get('getmann_auth_user') if cookies else None
    except:
        saved_user = None
    
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
            # А) ПРІОРИТЕТНИЙ ВХІД СУПЕР АДМІНА
            if email_input == SUPER_ADMIN_EMAIL and pass_input == SUPER_ADMIN_PASS:
                st.session_state.auth = {
                    'email': SUPER_ADMIN_EMAIL,
                    'login': SUPER_ADMIN_LOGIN,
                    'role': 'Супер Адмін'
                }
                controller.set('getmann_auth_user', email_input)
                st.success(f"Вітаємо, {SUPER_ADMIN_LOGIN}!")
                st.rerun()

            # Б) СТАНДАРТНИЙ ВХІД ЧЕРЕЗ БАЗУ
            df = load_csv(USERS_CSV_ID)
            if not df.empty:
                df['email'] = df['email'].astype(str).str.lower().str.strip()
                df['password'] = df['password'].astype(str).str.strip()
                
                user = df[(df['email'] == email_input) & (df['password'] == pass_input)]
                
                if not user.empty:
                    st.session_state.auth = user.iloc[0].to_dict()
                    controller.set('getmann_auth_user', email_input)
                    st.success("Вхід виконано!")
                    st.rerun()
                else:
                    st.error("❌ Невірний email або пароль")
            else:
                st.error("❌ Помилка зв'язку з базою даних")

def logout():
    controller.remove('getmann_auth_user')
    st.session_state.clear()
    st.rerun()
