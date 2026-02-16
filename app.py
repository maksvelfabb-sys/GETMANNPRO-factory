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

    # Перевірка, чи користувач авторизований
    if not check_auth():
        login_screen()
        return

    # --- ЛОГІКА ВИЗНАЧЕННЯ СУПЕР-АДМІНА ---
    # Перевіряємо всі можливі ключі, куди auth.py міг записати ваш email
    session_keys = st.session_state.keys()
    u_email = ""
    for key in ['user_email', 'email', 'login', 'user']:
        if key in session_keys:
            u_email = str(st.session_state[key]).lower().strip()
            if "@" in u_email: # знайшли щось схоже на email
                break

    # Пряма перевірка вашого доступу
    is_super_admin = (u_email == "maksvel.fabb@gmail.com")
    
    # Якщо email не знайшовся в сесії, але ви пройшли check_auth, 
    # можливо, auth.py використовує іншу назву. 
    # Для тесту можна розкоментувати рядок нижче, щоб побачити ключі:
    # st.sidebar.write(list(st.session_state.keys()))

    # Формування меню
    menu_options = ["📦 Журнал замовлень", "➕ Створити замовлення"]
    if is_super_admin:
        menu_options.append("⚙️ Адмін-панель")

    # Бічна панель
    st.sidebar.title("🏭 GETMANN Pro")
    st.sidebar.info(f"👤 Ви увійшли як: {u_email if u_email else 'Співробітник'}")
    
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
            st.error("Доступ заблоковано. Недостатньо прав.")

if __name__ == "__main__":
    main()
