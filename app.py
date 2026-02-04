import streamlit as st
import sys
import os

# Додаємо шлях до модулів для коректного імпорту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Імпорт модулів
from modules.auth import login_screen, logout
from modules.styles import apply_custom_styles
from modules.db.view import show_order_cards
from modules.db.create import show_create_order
from modules.admin_module import show_admin_panel

# 1. Початкове налаштування сторінки
st.set_page_config(
    page_title="GETMANN ERP",
    layout="wide",
    page_icon="🏭",
    initial_sidebar_state="expanded"
)

# 2. Застосування CSS стилів (включаючи кольори карток та компактність)
apply_custom_styles()

# 3. Перевірка авторизації та підтримка сесії через Cookies
# Якщо користувач не в сесії, login_screen спробує знайти куки
if 'auth' not in st.session_state:
    login_screen()

# Якщо після перевірки кук та форми входу сесія все ще порожня - зупиняємо додаток
if 'auth' not in st.session_state:
    st.stop()

# 4. Дані поточного користувача
user = st.session_state.auth
role = user.get('role', 'Користувач')
user_display = user.get('login') or user.get('email', 'Невідомий')

# 5. Бічна панель (Sidebar)
with st.sidebar:
    st.title("🏭 GETMANN ERP")
    st.markdown(f"**Користувач:** `{user_display}`")
    st.markdown(f"**Роль:** `{role}`")
    st.divider()
    
    # Навігаційне меню
    menu_options = ["📋 Замовлення"]
    
    # Доступ до адмін-панелі лише для відповідних ролей
    if role in ["Адмін", "Супер Адмін"]:
        menu_options.append("🔐 Адмін-панель")
    
    menu = st.radio("Навігація", menu_options)
    
    st.spacer = st.container() # Для відступу вниз
    st.divider()
    
    # Кнопка виходу (видаляє куки та сесію)
    if st.button("🚪 Вийти з системи", use_container_width=True):
        logout()

# 6. Основна логіка відображення контенту
if menu == "📋 Замовлення":
    st.title("📦 Керування замовленнями")
    
    # Використання вкладок для розділення функцій
    tab_view, tab_create = st.tabs(["🔎 Журнал замовлень", "➕ Створити замовлення"])
    
    with tab_view:
        # Модуль перегляду, сортування за менеджером та кольорових карток
        show_order_cards()
        
    with tab_create:
        # Модуль створення замовлення з динамічним кошиком товарів
        show_create_order()

elif menu == "🔐 Адмін-панель":
    # Модуль керування користувачами, паролями та очищенням бази
    show_admin_panel()

# 7. Футер (опціонально)
st.sidebar.caption("GETMANN ERP v3.0 (Stable Build)")
