import streamlit as st
import pandas as pd
from modules.config import USERS_CSV_ID, ORDERS_CSV_ID, ITEMS_CSV_ID
from modules.drive_tools import load_csv, save_csv

# ID баз даних
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
ITEMS_CSV_ID = "1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1"

def show_admin_panel():
    auth_data = st.session_state.get('auth', {})
    role = auth_data.get('role')
    
    st.header("🔐 Панель адміністратора")

    t1, t2, t3 = st.tabs(["👥 Користувачі", "🔑 Безпека", "⚙️ База даних"])

    # --- ВКЛАДКА 1: УПРАВЛІННЯ КОРИСТУВАЧАМИ ---
    with t1:
        if role in ["Адмін", "Супер Адмін"]:
            df_users = load_csv(USERS_CSV_ID)
            
            # --- 1.1 Додавання нового користувача ---
            with st.expander("➕ Додати нового співробітника"):
                with st.form("add_user_form", clear_on_submit=True):
                    new_email = st.text_input("Email (логін для входу)")
                    new_login = st.text_input("Ім'я (відображення в системі)")
                    new_pass = st.text_input("Пароль", type="password")
                    new_role = st.selectbox("Роль", ["Менеджер", "Виробництво", "Адмін", "Супер Адмін"])
                    
                    if st.form_submit_button("Створити акаунт"):
                        if new_email and new_pass and new_login:
                            if new_email in df_users['email'].values:
                                st.error("Користувач з таким Email вже існує!")
                            else:
                                new_row = pd.DataFrame([{
                                    'email': new_email.lower().strip(),
                                    'login': new_login.strip(),
                                    'password': str(new_pass).strip(),
                                    'role': new_role,
                                    'last_seen': '-'
                                }])
                                df_users = pd.concat([df_users, new_row], ignore_index=True)
                                save_csv(USERS_CSV_ID, df_users)
                                st.success(f"Користувача {new_login} додано!")
                                st.rerun()
                        else:
                            st.warning("Заповніть усі поля")

            st.divider()

            # --- 1.2 Список та видалення ---
            st.subheader("Список активних користувачів")
            for idx, row in df_users.iterrows():
                c1, c2, c3, c4 = st.columns([2, 2, 1.5, 0.5])
                c1.write(f"**{row['login']}**")
                c2.write(f"`{row['email']}`")
                c3.info(f"{row['role']}")
                
                # Кнопка видалення (не можна видалити самого себе)
                if row['email'] != auth_data.get('email'):
                    if c4.button("🗑️", key=f"del_u_{idx}"):
                        df_users = df_users.drop(idx)
                        save_csv(USERS_CSV_ID, df_users)
                        st.success("Користувача видалено")
                        st.rerun()
                else:
                    c4.write("🛡️") # Ви не можете видалити себе
        else:
            st.info("Доступ до керування користувачами обмежено.")

    # --- ВКЛАДКА 2: ЗМІНА ПАРОЛЯ ---
    with t2:
        st.subheader("Зміна пароля")
        df_users = load_csv(USERS_CSV_ID)
        
        # Вибір користувача для зміни пароля
        if role in ["Адмін", "Супер Адмін"]:
            target_user = st.selectbox("Виберіть акаунт", df_users['email'].tolist())
        else:
            target_user = auth_data.get('email')
            st.write(f"Зміна пароля для: **{target_user}**")

        new_password = st.text_input("Введіть новий пароль", type="password")
        if st.button("Оновити пароль"):
            if new_password:
                df_users.loc[df_users['email'] == target_user, 'password'] = str(new_password)
                save_csv(USERS_CSV_ID, df_users)
                st.success("Пароль оновлено!")
            else:
                st.error("Пароль порожній")

    # --- ВКЛАДКА 3: КЕРУВАННЯ БАЗОЮ ---
    with t3:
        if role in ["Адмін", "Супер Адмін"]:
            st.subheader("Очищення системи")
            st.warning("⚠️ Це видалить усі замовлення та товари з бази даних!")
            confirm = st.text_input("Введіть 'ВИДАЛИТИ' для дії")
            if st.button("🔥 Очистити базу") and confirm == "ВИДАЛИТИ":
                # Очищення заголовків
                save_csv(ORDERS_CSV_ID, pd.DataFrame(columns=['ID', 'Дата', 'Менеджер', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Сума', 'Готовність', 'Коментар']))
                # Очищення товарів
                save_csv(ITEMS_CSV_ID, pd.DataFrame(columns=['order_id', 'назва', 'арт', 'ціна', 'к-ть', 'сума']))
                st.success("Базу очищено!")
                st.rerun()
