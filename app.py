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
    st.error(f"❌ Помилка імпорту модулів: {e}")
    st.stop()

def main():
    apply_custom_styles()

    # Перевірка авторизації
    if not check_auth():
        login_screen()
        return

    # --- ЛОГІКА ДОСТУПУ (спеціально під ваш auth.py) ---
    # Отримуємо словник з даними користувача
    user_data = st.session_state.get('auth', {})
    
    # Витягуємо email та роль (враховуємо регістр і пробіли)
    u_email = str(user_data.get('email', '')).lower().strip()
    u_role = str(user_data.get('role', '')).strip()
    u_login = str(user_data.get('login', 'Користувач'))

    # ПЕРЕВІРКА НА СУПЕР АДМІНА
    # Доступ дозволено, якщо email збігається АБО роль вказана як 'Супер Адмін'
    is_super_admin = (u_email == "maksvel.fabb@gmail.com") or (u_role == 'Супер Адмін')

    # Формування меню
    menu_options = ["📦 Журнал замовлень", "➕ Створити замовлення"]
    if is_super_admin:
        menu_options.append("⚙️ Адмін-панель")

    # Бічна панель
    st.sidebar.title("🏭 GETMANN Pro")
    st.sidebar.info(f"👤 {u_login} ({u_role})")
    
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
            st.title("⚙️ Адміністрування")
            show_admin_panel()
        else:
            st.error("У вас немає доступу до цього розділу.")

if __name__ == "__main__":
    main()
