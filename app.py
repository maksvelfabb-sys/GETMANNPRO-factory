import streamlit as st

# Налаштування сторінки (має бути першою командою Streamlit)
st.set_page_config(
    page_title="GETMANN Pro Factory",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Блок безпечного імпорту модулів
try:
    from modules.auth import check_auth, login_screen, logout
    from modules.styles import apply_custom_styles
    from modules.db.view import show_order_cards
    from modules.db.create import show_create_order
    from modules.admin_module import show_admin_panel
except ImportError as e:
    st.error(f"❌ Критична помилка імпорту: {e}")
    st.info("Перевірте наявність файлів у папці modules та файлів __init__.py")
    st.stop()

def main():
    # Пристосування стилів (логотипи, кольори)
    apply_custom_styles()

    # Перевірка авторизації
    if not check_auth():
        login_screen()
        return

    # Бічна панель (Sidebar)
    st.sidebar.title(f"🏭 GETMANN Pro")
    st.sidebar.write(f"Користувач: `{st.session_state.get('user_name', 'maksvel.fabb')}`")
    
    menu = st.sidebar.radio(
        "Навігація",
        ["📦 Журнал замовлень", "➕ Створити замовлення", "⚙️ Адмін-панель"]
    )

    st.sidebar.divider()
    if st.sidebar.button("🚪 Вийти", width="stretch"):
        logout()

    # Основна логіка перемикання екранів
    if menu == "📦 Журнал замовлень":
        st.title("📦 Журнал замовлень")
        show_order_cards()

    elif menu == "➕ Створити замовлення":
        st.title("➕ Створення нового замовлення")
        show_create_order()

   elif menu == "⚙️ Адмін-панель":
        st.title("⚙️ Адміністрування")
        
        # Отримуємо дані користувача із сесії
        user_email = st.session_state.get('user_email', '')
        user_role = st.session_state.get('user_role', '')

        # ПРЯМА ПЕРЕВІРКА ДЛЯ СУПЕР-АДМІНА
        if user_email == "maksvel.fabb@gmail.com" or user_role == "admin":
            show_admin_panel()
        else:
            st.error(f"Доступ заборонено! Ваш email: {user_email}")
            st.warning("Зверніться до головного адміністратора для отримання прав.")

if __name__ == "__main__":
    main()

