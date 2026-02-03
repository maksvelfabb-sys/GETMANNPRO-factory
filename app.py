import streamlit as st
import sys
import os
from datetime import datetime

# Налаштування шляхів
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.auth import login_screen
from modules.styles import apply_custom_styles
from modules.database import show_orders_page
# Тепер назви функцій load_csv та save_csv точно збігаються
from modules.admin_module import show_admin_panel, load_csv, save_csv, USERS_CSV_ID

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")
apply_custom_styles()

if 'auth' not in st.session_state:
    login_screen()
    st.stop()

user = st.session_state.auth
role = user.get('role')

# Оновлення статусу активності
try:
    u_df = load_csv(USERS_CSV_ID)
    if not u_df.empty:
        u_df.loc[u_df['email'] == user['email'], 'last_seen'] = datetime.now().strftime("%H:%M")
        save_csv(USERS_CSV_ID, u_df)
except:
    pass

# Меню
st.sidebar.title("🏭 GETMANN ERP")
menu_opts = ["📋 Замовлення"]
if role in ["Адмін", "Супер Адмін"]:
    menu_opts.append("👥 Адмін-панель")

menu = st.sidebar.radio("Навігація", menu_opts)

if st.sidebar.button("🚪 Вийти"):
    st.session_state.clear()
    st.rerun()

if menu == "📋 Замовлення":
    show_orders_page(role)
elif menu == "👥 Адмін-панель":
    show_admin_panel()
