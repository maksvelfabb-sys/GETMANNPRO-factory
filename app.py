import streamlit as st

# 1. Налаштування сторінки
st.set_page_config(
    page_title="GETMANN Pro Factory",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Блок безпечного імпорту
try:
    from modules.auth import check_auth, login_screen, logout
    from modules.styles import apply_custom_styles
    from modules.db.view import show_order_cards
    from modules.db.create import show_create_order
    from modules.admin_module import show_admin_panel
    from modules.drawings import show_drawings_catalog
    # Сюди додасте, коли створите файл:
    # from modules.materials import show_materials 
except ImportError as e:
    st.error(f"❌ Помилка імпорту модулів: {e}")
    st.stop()

def main():
    apply_custom_styles()

    # Перевірка авторизації
    if not check_auth():
        login_screen()
        return

    # Ініціалізація сторінки за замовчуванням
    if 'page' not in st.session_state:
        st.session_state.page = "view"

    # Дані користувача з auth.py
    user_data = st.session_state.get('auth', {})
    u_email = str(user_data.get('email', '')).lower().strip()
    u_role = str(user_data.get('role', '')).strip()
    u_name = user_data.get('login', 'Користувач')

    # ПЕРЕВІРКА ПРАВ
    is_super_admin = (u_email == "maksvel.fabb@gmail.com") or (u_role == 'Супер Адмін')

    # --- БІЧНА ПАНЕЛЬ ---
    with st.sidebar:
        st.title("🏭 GETMANN Pro")
        st.markdown(f"👤 **{u_name}**")
        st.divider()

        # Кнопки навігації
        if st.button("📦 Журнал замовлень", use_container_width=True, 
                     type="primary" if st.session_state.page == "view" else "secondary"):
            st.session_state.page = "view"
            st.rerun()

        if st.button("➕ Створити замовлення", use_container_width=True,
                     type="primary" if st.session_state.page == "create" else "secondary"):
            st.session_state.page = "create"
            st.rerun()

        if st.button("🏗️ Матеріал", use_container_width=True,
                     type="primary" if st.session_state.page == "material" else "secondary"):
            st.session_state.page = "material"
            st.rerun()

        if st.button("📐 Креслення", use_container_width=True,
                     type="primary" if st.session_state.page == "drawings" else "secondary"):
            st.session_state.page = "drawings"
            st.rerun()

        if is_super_admin:
            st.divider()
            if st.button("⚙️ Адмін-панель", use_container_width=True,
                         type="primary" if st.session_state.page == "admin" else "secondary"):
                st.session_state.page = "admin"
                st.rerun()

        st.divider()
        if st.button("🚪 Вийти", use_container_width=True):
            logout()

    # --- ВІДОБРАЖЕННЯ МОДУЛІВ (ЛОГІКА ПЕРЕМИКАННЯ) ---
    
    if st.session_state.page == "view":
        st.title("📦 Журнал замовлень")
        show_order_cards()

    elif st.session_state.page == "create":
        st.title("➕ Нове замовлення")
        show_create_order()

    elif st.session_state.page == "material":
        st.title("🏗️ Склад матеріалів")
        st.info("Розділ у розробці. Тут буде облік металу та комплектуючих.")
        # show_materials() 

    elif st.session_state.page == "drawings":
        st.title("📐 Каталог креслень")
        show_drawings_catalog()

    elif st.session_state.page == "admin":
        if is_super_admin:
            st.title("⚙️ Адміністрування")
            show_admin_panel()
        else:
            st.error("Доступ обмежено.")
            st.session_state.page = "view"
            st.rerun()

if __name__ == "__main__":
    main()
