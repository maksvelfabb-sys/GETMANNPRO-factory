import streamlit as st
import pandas as pd
from modules.drive_tools import (
    load_csv, save_csv, 
    USERS_CSV_ID, ORDERS_CSV_ID, ITEMS_CSV_ID
)

# Спробуємо отримати ID для хедерів з констант, якщо ні - використовуємо ORDERS_CSV_ID як базу
# ПРИМІТКА: Краще додати ORDERS_HEADER_CSV_ID у файл drive_tools.py
ORDERS_HEADER_CSV_ID = getattr(st.secrets, "1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1", "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i")

def reset_database():
    """Функція повної очистки та автоматичного відновлення структури бази"""
    # 1. Структура для orders_header.csv (Дані клієнтів)
    header_cols = [
        "Номер замовлення", "Дата", "Замовник", "Телефон", 
        "Загальна сума", "Статус", "Коментар менеджера"
    ]
    df_header = pd.DataFrame(columns=header_cols)
    
    # 2. Структура для orders.csv (Склад замовлень)
    items_cols = [
        "Номер замовлення", "Товар", "Артикул", 
        "Кількість", "Ціна за од.", "Сума"
    ]
    df_items = pd.DataFrame(columns=items_cols)
    
    # Запис порожніх шаблонів на Google Drive
    success_h = save_csv(ORDERS_HEADER_CSV_ID, df_header)
    success_i = save_csv(ORDERS_CSV_ID, df_items)
    
    return success_h and success_i

def show_admin_panel():
    auth_data = st.session_state.get('auth', {})
    user_role = auth_data.get('role')
    current_user_email = auth_data.get('email')

    # Доступ лише для Адмінів та Супер Адмінів
    if user_role not in ["Адмін", "Супер Адмін"]:
        st.error("⛔ У вас немає прав для доступу до цього розділу.")
        return

    st.title("🛡️ Адмін-панель керування")

    # Створюємо вкладки
    tab_users, tab_db = st.tabs(["👥 Користувачі", "⚙️ Керування базою"])

    # --- ВКЛАДКА 1: КЕРУВАННЯ КОРИСТУВАЧАМИ ---
    with tab_users:
        df_users = load_csv(USERS_CSV_ID)
        
        if df_users.empty:
            st.warning("⚠️ База користувачів не завантажена або порожня.")
        else:
            # 1.1 Додавання нового користувача
            with st.expander("➕ Додати нового співробітника"):
                with st.form("add_user_form", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    new_login = c1.text_input("Логін (Ім'я)")
                    new_email = c2.text_input("Email (для входу)").lower().strip()
                    new_pass = c1.text_input("Пароль")
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
                                    st.success(f"Акаунт {new_login} створено!")
                                    st.rerun()
                        else:
                            st.warning("Будь ласка, заповніть всі поля.")

            st.divider()

            # 1.2 Список користувачів
            st.subheader("Список користувачів")
            for idx, row in df_users.iterrows():
                with st.expander(f"👤 {row['login']} — {row['role']} ({row['email']})"):
                    with st.form(key=f"edit_user_{idx}"):
                        c1, c2 = st.columns(2)
                        edit_login = c1.text_input("Ім'я", value=str(row['login']))
                        edit_email = c2.text_input("Email", value=str(row['email']))
                        edit_pass = c1.text_input("Пароль", value=str(row['password']))
                        
                        roles_list = ["Менеджер", "Виробництво", "Адмін", "Супер Адмін"]
                        curr_role_idx = roles_list.index(row['role']) if row['role'] in roles_list else 0
                        edit_role = c2.selectbox("Змінити роль", roles_list, index=curr_role_idx)
                        
                        btn_save, btn_del = st.columns(2)
                        if btn_save.form_submit_button("💾 Зберегти"):
                            df_users.loc[idx, ['login', 'email', 'password', 'role']] = [
                                edit_login.strip(), edit_email.lower().strip(), str(edit_pass).strip(), edit_role
                            ]
                            if save_csv(USERS_CSV_ID, df_users):
                                st.success("Оновлено!")
                                st.rerun()

                        if row['email'] == current_user_email:
                            btn_del.disabled_button("🛡️ Ваш акаунт", disabled=True)
                        else:
                            if btn_del.form_submit_button("🗑️ Видалити"):
                                df_users = df_users.drop(idx)
                                if save_csv(USERS_CSV_ID, df_users):
                                    st.rerun()

    # --- ВКЛАДКА 2: ТЕХНІЧНЕ ОБСЛУГОВУ
