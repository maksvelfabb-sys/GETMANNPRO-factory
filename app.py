import streamlit as st

# 1. Налаштування сторінки
st.set_page_config(
    page_title="GETMANN Pro Factory",
    page_icon="🏭",
    layout="wide"
)

# 2. Імпорт модулів
try:
    from modules.auth import check_auth, login_screen, logout
    from modules.styles import apply_custom_styles
    from modules.db.view import show_order_cards
    from modules.db.create import show_create_order
    from modules.admin_module import show_admin_panel
except ImportError as e:
    st.error(f"❌ Помилка імпорту: {e}")
    st.stop()

def main():
    apply_custom_styles()

    if not check_auth():
        login_screen()
        return

    # --- ТИМЧАСОВА ДІАГНОСТИКА (можна видалити потім) ---
    # st.sidebar.write(st.session_state) 
    # --------------------------------------------------

    # Отримуємо дані. Якщо email порожній, пробуємо отримати login (іноді в auth.py так називають)
    u_email = str(st.session_state.get('user_email', st.session_state.get('login', ''))).lower().strip()
    u_role = str(st.session_state.get('user_role', '')).lower()
    u_name = st.session_state.get('user_name', 'Адмін')

    # ВИЗНАЧЕННЯ ПРАВ (Супер-адмін)
    is_super_admin = (u_email == "maksvel.fabb@gmail.com") or (u_role == "admin")

    # Формування меню
    menu_options = ["📦 Журнал замовлень", "➕ Створити замовлення"]
    if is_super_admin:
        menu_options.append("⚙️ Адмін-панель")

    # Бічна панель
    st.sidebar.title("🏭 GETMANN Pro")
    st.sidebar.success(f"✅ Ви увійшли як: {u_name}")
    
    menu = st.sidebar.radio("Навігація", menu_options)

    st.sidebar.divider()
    if st.sidebar.button("🚪 Вийти", width="stretch"):
        logout()

    # ЛОГІКА ЕКРАНІВ
    if menu == "📦 Журнал замовлень":
        st.title("📦 Журнал замовлень")
        show_order_cards()

    elif menu == "➕ Створити замовлення":
        st.title("➕ Нове замовлення")
        show_create_order()

    elif menu == "⚙️ Адмін-панель":
        if is_super_admin:
            st.title("⚙️ Адміністрування системи")
            show_admin_panel()
        else:
            st.error("Доступ обмежено.")

if __name__ == "__main__":
    main()
