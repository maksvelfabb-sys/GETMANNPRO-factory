import streamlit as st
from streamlit_cookies_controller import CookieController
from modules.admin_module import load_csv

# Ініціалізуємо контролер один раз
controller = CookieController()
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"

def login_screen():
    # 1. Спроба отримати збереженого користувача з куків
    saved_user = None
    try:
        # Отримуємо всі куки спочатку
        cookies = controller.get_all()
        if cookies:
            saved_user = cookies.get('getmann_auth_user')
    except Exception:
        # Якщо контролер ще не готовий, просто ігноруємо і йдемо до форми
        pass
    
    # 2. Якщо знайдено куку і сесія ще не створена - авто-вхід
    if saved_user and 'auth' not in st.session_state:
        df = load_csv(USERS_CSV_ID)
        user_row = df[df['email'] == saved_user]
        if not user_row.empty:
            st.session_state.auth = user_row.iloc[0].to_dict()
            st.rerun()

    # 3. Екран логіну (якщо авто-вхід не спрацював)
    st.title("🔐 Вхід у систему")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Пароль", type="password")
        submit = st.form_submit_button("Увійти", use_container_width=True)

        if submit:
            df = load_csv(USERS_CSV_ID)
            # Перетворюємо пароль на рядок для порівняння
            user = df[(df['email'] == email) & (df['password'].astype(str) == str(password))]
            
            if not user.empty:
                auth_data = user.iloc[0].to_dict()
                st.session_state.auth = auth_data
                
                # Зберігаємо в куки на тривалий термін
                controller.set('getmann_auth_user', email)
                
                st.success("Вхід успішний! Завантаження...")
                st.rerun()
            else:
                st.error("Невірний email або пароль")

def logout():
    """Повне видалення сесії та куків"""
    try:
        controller.remove('getmann_auth_user')
    except:
        pass
    
    # Очищуємо стан сесії
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    st.rerun()
