import streamlit as st
import sys
import os
from datetime import datetime

# Системний шлях
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.auth import login_screen
from modules.styles import apply_custom_styles
from modules.database import show_orders_page
from modules.admin_module import show_admin_panel, load_csv, save_csv, USERS_CSV_ID

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")
apply_custom_styles()

if 'auth' not in st.session_state:
    login_screen()
    st.stop()

user = st.session_state.auth
role = user.get('role')

# Оновлюємо статус "В мережі" при кожному кліку
if st.session_state.get('auth'):
    try:
        u_df = load_csv(USERS_CSV_ID)
        u_df.loc[u_df['email'] == user['email'], 'last_seen'] = datetime.now().strftime("%H:%M:%S")
        # Щоб не перевантажувати Drive, можна зберігати раз на кілька хвилин, 
        # але для початку зробимо пряме оновлення
        save_csv(USERS_CSV_ID, u_df)
    except: pass

# --- Сайдбар з фільтрацією меню ---
st.sidebar.title("🏭 GETMANN ERP")
st.sidebar.write(f"👤 {user['email']}")

menu_options = ["📋 Замовлення"]
# Додаємо Адмін-панель тільки для Адмінів та Супер Адмінів
if role in ["Адмін", "Супер Адмін"]:
    menu_options.append("👥 Адмін-панель")

menu = st.sidebar.radio("Навігація", menu_options)

if st.sidebar.button("🚪 Вийти"):
    st.session_state.clear()
    st.rerun()

# Відображення сторінок
if menu == "📋 Замовлення":
    show_orders_page(role)
elif menu == "👥 Адмін-панель":
    show_admin_panel()
