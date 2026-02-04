import streamlit as st
from streamlit_cookies_controller import CookieController
from modules.admin_module import load_csv

controller = CookieController()
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"

def login_screen():
    # 1. Спроба авто-входу через куки
    try:
        cookies = controller.get_all()
        saved_user = cookies.get('getmann_auth_user') if cookies else None
    except:
        saved_user = None
    
    if saved_user and 'auth' not in st.session_state:
        df = load_csv(USERS_CSV_ID)
        # Пошук без урахування регістру та пробілів
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
            df = load_csv(USERS_CSV_ID)
            
            # ОЧИЩЕННЯ ТА ПЕРЕВІРКА ДАНИХ БАЗИ
            df['email'] = df['email'].astype(str).str.lower().str.strip()
            df['password'] = df['password'].astype(str).str.strip()
            
            # Пошук користувача
            user = df[(df['email'] == email_input) & (df['password'] == pass_input)]
            
            if not user.empty:
                auth_data = user.iloc[0].to_dict()
                st.session_state.auth = auth_data
                controller.set('getmann_auth_user', email_input)
                st.success("Авторизація успішна!")
                st.rerun()
            else:
                # ПЕРЕВІРКА: Чи існує імейл взагалі?
                if email_input in df['email'].values:
                    st.error("❌ Невірний пароль")
                else:
                    st.error("❌ Користувача з таким Email не знайдено")

def logout():
    controller.remove('getmann_auth_user')
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
