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
except ImportError as e:
    st.error(f"❌ Критична помилка імпорту: {e}")
    st.stop()

def main():
    # Застосовуємо стилі
    apply_custom_styles()

    # ПЕРЕВІРКА АВТОРИЗАЦІЇ
    if not check_auth():
        login_screen()
        return

    # Отримуємо дані користувача (якщо їх немає - ставимо порожній рядок)
    # Важливо: auth.py має зберігати email при логіні!
    u_email = st.session_state.get('user_email', '').lower().strip()
    u_role = st.session_state.get('user_role', '').lower()
    u_name = st.session_state.get('user_name', 'Користувач')

    # БІЧНА ПАНЕЛЬ
    st.sidebar.title("🏭 GETMANN Pro")
    st.sidebar.info(f"👤 {u_name}")
    
    # Список пунктів меню залежно від ролі
    menu_options = ["📦 Журнал замовлень", "➕ Створити замовлення"]
    
    # Додаємо адмін-панель тільки якщо це ви або адмін
    if u_email == "maksvel.fabb@gmail.com" or u_role == "admin":
        menu_options.append("⚙️ Адмін-панель")

    menu = st.sidebar.radio("Навігація", menu_options)

    st.sidebar.divider()
    if st.sidebar.button("🚪 Вийти", width="stretch"):
        logout()

    # ОСНОВНА ЛОГІКА
    if menu == "📦 Журнал замовлень":
        st.title("📦 Журнал замовлень")
        show_order_cards()

    elif menu == "➕ Створити замовлення":
        st.title("➕ Створення нового замовлення")
        show_create_order()

    elif menu == "⚙️ Адмін-панель":
        st.title("⚙️ Адміністрування")
        # Подвійна перевірка безпеки
        if u_email == "maksvel.fabb@gmail.com" or u_role == "admin":
            show_admin_panel()
        else:
            st.error("Недостатньо прав для доступу.")

if __name__ == "__main__":
    main()
