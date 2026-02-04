import streamlit as st
from modules.auth import login_screen, logout

# Важливо: ініціалізація повинна бути на початку
if 'auth' not in st.session_state:
    login_screen()
    if 'auth' not in st.session_state:
        st.stop()
import sys
import os

# Додаємо шлях до модулів
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.auth import login_screen
from modules.styles import apply_custom_styles
# Імпортуємо нові модулі з папки db
from modules.db.view import show_order_cards
from modules.db.create import show_create_order

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")
apply_custom_styles()

if 'auth' not in st.session_state:
    login_screen()
    st.stop()

user = st.session_state.auth
role = user.get('role')

st.sidebar.title("🏭 GETMANN ERP")
st.sidebar.write(f"👤 {user.get('login', user.get('email'))}")

# Меню
menu_options = ["📋 Замовлення"]
if role in ["Адмін", "Супер Адмін"]:
    menu_options.append("👥 Адмін-панель")

menu = st.sidebar.radio("Навігація", menu_options)

if st.sidebar.button("🚪 Вийти"):
    st.session_state.clear()
    st.rerun()

# --- ВІДОБРАЖЕННЯ НОВОЇ СТРУКТУРИ ---
if menu == "📋 Замовлення":
    # Створюємо вкладки: одна для перегляду, інша для створення
    tab_view, tab_create = st.tabs(["🔎 Журнал замовлень", "➕ Нове замовлення"])
    
    with tab_view:
        show_order_cards() # Викликає код з modules/db/view.py
        
    with tab_create:
        show_create_order() # Викликає код з modules/db/create.py

elif menu == "👥 Адмін-панель":
    from modules.admin_module import show_admin_panel
    show_admin_panel()

