import streamlit as st
from modules.auth import login_screen
from modules.styles import apply_custom_styles
from modules.database import show_orders_page
from modules.admin_module import show_admin_panel

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")
apply_custom_styles()

# Перевірка авторизації
if 'auth' not in st.session_state:
    login_screen()
    st.stop()

user = st.session_state.auth
role = user.get('role')

# Сайдбар
st.sidebar.title("🏭 GETMANN ERP")
st.sidebar.info(f"👤 {user['email']}\n\n🎭 Роль: {role}")

menu = st.sidebar.radio("Навігація", ["📋 Замовлення", "👥 Адмін-панель", "⚙️ Налаштування"])

if st.sidebar.button("🚪 Вийти"):
    st.session_state.clear()
    st.rerun()

# Маршрутизація
if menu == "📋 Замовлення":
    show_orders_page(role)
elif menu == "👥 Адмін-панель":
    if role == "Супер Адмін":
        show_admin_panel()
    else:
        st.warning("Доступ закрито. Ця панель лише для Супер Адміна.")
elif menu == "⚙️ Налаштування":
    st.header("⚙️ Налаштування")
    st.write("Тут будуть системні налаштування бази даних.")
