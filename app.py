import streamlit as st
from modules.auth import check_auth, login_screen, logout
from modules.styles import apply_custom_styles
from modules.db.view import show_order_cards
from modules.db.create import show_create_order
from modules.admin_module import show_admin_panel

# 1. Початкове налаштування сторінки (ЗАВЖДИ МАЄ БУТИ ПЕРШИМ)
st.set_page_config(
    page_title="GETMANN Pro",
    layout="wide",
    page_icon="🏭",
    initial_sidebar_state="expanded"
)

# 2. Перевірка авторизації
# Використовуємо твій check_auth() або перевірку session_state
if 'auth' not in st.session_state:
    login_screen()
    st.stop()  # Зупиняємо виконання, поки користувач не увійде

# --- ЯКЩО АВТОРИЗОВАНО, ВИКОНУЄТЬСЯ КОД НИЖЧЕ ---

# 3. Застосування CSS стилів
apply_custom_styles()

# 4. Дані поточного користувача
user = st.session_state.auth
role = user.get('role', 'Користувач')
user_display = user.get('login') or user.get('email', 'Невідомий')

# 5. Бічна панель (Sidebar)
with st.sidebar:
    st.title("🏭 GETMANN Pro")
    st.markdown(f"**Користувач:** `{user_display}`")
    st.markdown(f"**Роль:** `{role}`")
    st.divider()
    
    # Навігаційне меню
    menu_options = ["📋 Замовлення"]
    if role in ["Адмін", "Супер Адмін"]:
        menu_options.append("🔐 Адмін-панель")
    
    menu = st.radio("Навігація", menu_options)
    
    st.divider()
    
    # Кнопка виходу
    if st.button("🚪 Вийти з системи", use_container_width=True):
        logout()
    
    st.sidebar.caption("GETMANN Pro v3.1 (Stable Build)")

# 6. Основна логіка відображення контенту
if menu == "📋 Замовлення":
    st.title("📦 Керування замовленнями")
    
    # Використання вкладок для розділення функцій
    # Це прибирає конфлікт Duplicate ID, бо контент розділений
    tab_view, tab_create = st.tabs(["🔎 Журнал замовлень", "➕ Створити замовлення"])
    
    with tab_view:
        # Відображення карток
        show_order_cards()
        
    with tab_create:
        # Форма створення замовлення
        show_create_order()

elif menu == "🔐 Адмін-панель":
    show_admin_panel()
