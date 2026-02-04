import streamlit as st
import pandas as pd
from .auth import USERS_CSV_ID # Або вкажіть ID вручну "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"
from .admin_module_core import load_csv, save_csv # Переконайтеся, що імпорт вірний

# Ваші ID файлів
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
ITEMS_CSV_ID = "1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1"

def show_admin_panel():
    auth_data = st.session_state.get('auth', {})
    role = auth_data.get('role')
    current_user_email = auth_data.get('email')

    st.header("🔐 Панель керування")

    # Створюємо вкладки
    t1, t2, t3 = st.tabs(["👥 Користувачі", "🔑 Зміна пароля", "⚙️ База даних"])

    # --- ВКЛАДКА 1: СПИСОК КОРИСТУВАЧІВ (Тільки для Адмінів) ---
    with t1:
        if role in ["Адмін", "Супер Адмін"]:
            st.subheader("Управління доступом")
            df_users = load_csv(USERS_CSV_ID)
            st.dataframe(df_users[['email', 'login', 'role', 'last_seen']], use_container_width=True)
        else:
            st.info("Ця вкладка доступна лише адміністраторам.")

    # --- ВКЛАДКА 2: ЗМІНА ПАРОЛЯ ---
    with t2:
        st.subheader("Оновлення безпеки")
        df_users = load_csv(USERS_CSV_ID)

        if role in ["Адмін", "Супер Адмін"]:
            # Адмін може вибрати будь-якого юзера
            target_user = st.selectbox("Виберіть користувача", df_users['email'].tolist())
        else:
            # Звичайний юзер бачить тільки себе
            target_user = current_user_email
            st.write(f"Зміна пароля для: **{target_user}**")

        new_pass = st.text_input("Новий пароль", type="password")
        if st.button("Оновити пароль"):
            if new_pass:
                df_users.loc[df_users['email'] == target_user, 'password'] = new_pass
                save_csv(USERS_CSV_ID, df_users)
                st.success(f"Пароль для {target_user} успішно змінено!")
            else:
                st.error("Пароль не може бути порожнім")

    # --- ВКЛАДКА 3: ОЧИЩЕННЯ БАЗИ (Тільки для Адмінів) ---
    with t3:
        if role in ["Адмін", "Супер Адмін"]:
            st.subheader("Небезпечна зона")
            st.error("⚠️ Видалення бази замовлень та товарів неможливо скасувати!")
            
            confirm = st.text_input("Введіть 'ВИДАЛИТИ' для підтвердження", key="confirm_clear")
            
            if st.button("🔥 ОЧИСТИТИ ВСІ ЗАМОВЛЕННЯ"):
                if confirm == "ВИДАЛИТИ":
                    # Очищення Headers
                    empty_h = pd.DataFrame(columns=['ID', 'Дата', 'Менеджер', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Сума', 'Готовність', 'Коментар'])
                    save_csv(ORDERS_CSV_ID, empty_h)
                    
                    # Очищення Items
                    empty_i = pd.DataFrame(columns=['order_id', 'назва', 'арт', 'ціна', 'к-ть', 'сума'])
                    save_csv(ITEMS_CSV_ID, empty_i)
                    
                    st.success("Бази успішно очищені!")
                    st.rerun()
                else:
                    st.warning("Підтвердження невірне")
        else:
            st.info("Доступ обмежено.")
