import streamlit as st
from modules.auth import check_auth, login_screen, logout
from modules.styles import apply_custom_styles
from modules.db.view import show_order_cards
from modules.db.create import show_create_order
from modules.admin_module import show_admin_panel

# 1. Налаштування сторінки (ОБОВ'ЯЗКОВО ПЕРШИМ)
st.set_page_config(
    page_title="GETMANN Pro", 
    layout="wide", 
    page_icon="🏭",
    initial_sidebar_state="expanded"
)

# 2. Застосування CSS стилів
try:
    apply_custom_styles()
except Exception as e:
    st.error(f"Помилка завантаження стилів: {e}")

# 3. Перевірка авторизації
if not check_auth():
    login_screen()
    st.stop()  # Зупиняємо виконання, поки користувач не увійде

# --- ПІСЛЯ АВТОРИЗАЦІЇ ---

# 4. Дані користувача з сесії
user = st.session_state.auth
role = user.get('role', 'Користувач')
user_display = user.get('login') or user.get('email', 'Невідомий')

# 5. Бічна панель (Sidebar)
with st.sidebar:
    st.title("🏭 GETMANN Pro")
    st.markdown(f"**Вітаємо,** `{user_display}`")
    st.markdown(f"**Роль:** `{role}`")
    st.divider()
    
    # Формування списку меню залежно від ролі
    menu_options = ["📋 Замовлення"]
    if role in ["Адмін", "Супер Адмін"]:
        menu_options.append("🔐 Адмін-панель")
    
    # Використовуємо ключ 'main_nav', щоб уникнути конфліктів ID
    menu = st.radio("Навігація", menu_options, key="main_nav")
    
    st.divider()
    
    if st.button("🚪 Вийти з системи", use_container_width=True, key="logout_btn"):
        logout()
    
    st.caption("v3.1 Stable Build (2026)")

# 6. Основна логіка контенту
if menu == "📋 Замовлення":
    st.title("📦 Керування замовленнями")
    
    # Створюємо вкладки для Журналу та Створення
    tab_view, tab_create = st.tabs(["🔎 Журнал замовлень", "➕ Створити нове"])
    
    with tab_view:
        show_order_cards()
        
    with tab_create:
        show_create_order()

elif menu == "🔐 Адмін-панель":
    st.title("🔐 Адміністративна панель")
    show_admin_panel()

# 7. Системний футер (опціонально)
st.sidebar.markdown("---")
st.sidebar.info(f"Логін: {user_display}")
