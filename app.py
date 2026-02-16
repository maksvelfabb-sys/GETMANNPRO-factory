import streamlit as st
from modules.auth import check_auth, login_screen, logout
from modules.styles import apply_custom_styles
from modules.db.view import show_order_cards
from modules.db.create import show_create_order
from modules.admin_module import show_admin_panel

# 1. Налаштування сторінки
st.set_page_config(
    page_title="GETMANN Pro", 
    layout="wide", 
    page_icon="🏭",
    initial_sidebar_state="expanded"
)

# 2. Стилі
try:
    apply_custom_styles()
except:
    pass

# 3. Перевірка авторизації
if not check_auth():
    login_screen()
    st.stop()

# 4. Дані користувача
user = st.session_state.auth
role = user.get('role', 'Користувач')

# 5. Бічна панель (Sidebar)
with st.sidebar:
    st.title("🏭 GETMANN Pro")
    st.markdown(f"**Вітаємо,** `{user.get('login', 'User')}`")
    st.divider()
    
    # ФОРМУЄМО МЕНЮ (Тепер "Створити" — окремий пункт)
    menu_options = [
        "📋 Журнал замовлень", 
        "➕ Створити замовлення"
    ]
    
    if role in ["Адмін", "Супер Адмін"]:
        menu_options.append("🔐 Адмін-панель")
    
    menu = st.radio("Навігація", menu_options, key="main_nav")
    
    st.divider()
    if st.button("🚪 Вийти", use_container_width=True):
        logout()

# 6. Основна логіка контенту (БЕЗ ВКЛАДОК)
if menu == "📋 Журнал замовлень":
    st.title("🔎 Журнал замовлень")
    show_order_cards()

elif menu == "➕ Створити замовлення":
    st.title("📝 Нове замовлення")
    show_create_order() # Викликаємо модуль створення тут

elif menu == "🔐 Адмін-панель":
    st.title("🔐 Адміністративна панель")
    show_admin_panel()

