import streamlit as st
import pandas as pd
# Імпортуємо тільки з drive_tools, щоб розірвати коло імпортів
from modules.drive_tools import load_csv, save_csv, USERS_CSV_ID, ORDERS_CSV_ID, ITEMS_CSV_ID

def show_admin_panel():
    auth_data = st.session_state.get('auth', {})
    user_role = auth_data.get('role')
    current_user_email = auth_data.get('email')

    # Доступ лише для Адмінів та Супер Адмінів
    if user_role not in ["Адмін", "Супер Адмін"]:
        st.error("⛔ У вас немає прав для доступу до цього розділу.")
        return

    st.title("🛡️ Адмін-панель керування")

    # Створюємо вкладки для різних функцій
    tab_users, tab_db = st.tabs(["👥 Користувачі", "⚙️ Керування базою"])

    # --- ВКЛАДКА 1: КЕРУВАННЯ КОРИСТУВАЧАМИ ---
    with tab_users:
        df_users = load_csv(USERS_CSV_ID)
        
        if df_users.empty:
            st.warning("⚠️ База користувачів не завантажена.")
        else:
            # 1.1 Додавання нового користувача
            with st.expander("➕ Додати нового співробітника"):
                with st.form("add_user_form", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    new_login = c1.text_input("Логін (Ім'я)")
                    new_email = c2.text_input("Email (для входу)").lower().strip()
                    new_pass = c1.text_input("Пароль", type="default")
                    new_role = c2.selectbox("Роль", ["Менеджер", "Виробництво", "Адмін", "Супер Адмін"])
                    
                    if st.form_submit_button("Створити акаунт"):
                        if new_login and new_email and new_pass:
                            if new_email in df_users['email'].astype(str).values:
                                st.error("Користувач з таким Email вже існує!")
                            else:
                                new_row = pd.DataFrame([{
                                    'email': new_email,
                                    'login': new_login,
                                    'password': str(new_pass),
                                    'role': new_role,
                                    'last_seen': '-'
                                }])
                                df_users = pd.concat([df_users, new_row], ignore_index=True)
                                if save_csv(USERS_CSV_ID, df_users):
                                    st.success(f"Акаунт {new_login} успішно створено!")
                                    st.rerun()
                        else:
                            st.warning("Будь ласка, заповніть всі поля.")

            st.divider()

            # 1.2 Список та редагування існуючих користувачів
            st.subheader("Список користувачів")
            
            for idx, row in df_users.iterrows():
                # Відображення картки користувача
                with st.expander(f"👤 {row['login']} — {row['role']} ({row['email']})"):
                    with st.form(key=f"edit_user_{idx}"):
                        col1, col2 = st.columns(2)
                        
                        # Поля для редагування
                        edit_login = col1.text_input("Ім'я / Логін", value=str(row['login']))
                        edit_email = col2.text_input("Email", value=str(row['email']))
                        edit_pass = col1.text_input("Пароль", value=str(row['password']))
                        
                        # Вибір ролі з автоматичним фокусом на поточну
                        roles_list = ["Менеджер", "Виробництво", "Адмін", "Супер Адмін"]
                        current_role_idx = roles_list.index(row['role']) if row['role'] in roles_list else 0
                        edit_role = col2.selectbox("Змінити роль", roles_list, index=current_role_idx)
                        
                        btn_save, btn_del = st.columns([1, 1])
                        
                        # Кнопка ЗБЕРЕГТИ
                        if btn_save.form_submit_button("💾 Зберегти зміни"):
                            df_users.loc[idx, 'login'] = edit_login.strip()
                            df_users.loc[idx, 'email'] = edit_email.lower().strip()
                            df_users.loc[idx, 'password'] = str(edit_pass).strip()
                            df_users.loc[idx, 'role'] = edit_role
                            
                            if save_csv(USERS_CSV_ID, df_users):
                                st.success("Дані оновлено!")
                                st.rerun()

                        # Кнопка ВИДАЛИТИ (Заборона на видалення себе)
                        if row['email'] == current_user_email:
                            btn_del.info("🛡️ Ваш акаунт")
                        else:
                            if btn_del.form_submit_button("🗑️ Видалити"):
                                df_users = df_users.drop(idx)
                                if save_csv(USERS_CSV_ID, df_users):
                                    st.success("Користувача видалено")
                                    st.rerun()

    # --- ВКЛАДКА 2: КЕРУВАННЯ БАЗОЮ (Очищення) ---
    with tab_db:
        st.subheader("🧹 Технічне обслуговування")
        st.warning("Увага! Дії в цьому розділі незворотні.")
        
        with st.expander("🔥 Очистити базу замовлень"):
            st.write("Це видалить усі замовлення та товари з системи.")
            confirm = st.text_input("Введіть 'ВИДАЛИТИ' для підтвердження:")
            
            if st.button("Виконати повне очищення"):
                if confirm == "ВИДАЛИТИ":
                    # Очищуємо заголовки замовлень
                    empty_orders = pd.DataFrame(columns=['ID', 'Дата', 'Менеджер', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Сума', 'Готовність', 'Коментар'])
                    save_csv(ORDERS_CSV_ID, empty_orders)
                    
                    # Очищуємо список товарів
                    empty_items = pd.DataFrame(columns=['order_id', 'назва', 'арт', 'ціна', 'к-ть', 'сума'])
                    save_csv(ITEMS_CSV_ID, empty_items)
                    
                    st.success("Бази даних очищені!")
                    st.rerun()
                else:
                    st.error("Код підтвердження невірний.")

# Завершення коду
