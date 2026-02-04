import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, USERS_CSV_ID

def show_admin_panel():
    auth_data = st.session_state.get('auth', {})
    user_role = auth_data.get('role')
    
    # Доступ лише для Адмінів та Супер Адмінів
    if user_role not in ["Адмін", "Супер Адмін"]:
        st.error("У вас немає прав для перегляду цієї сторінки.")
        return

    st.title("👥 Керування персоналом")

    df_users = load_csv(USERS_CSV_ID)
    if df_users.empty:
        st.warning("База користувачів порожня або не завантажена.")
        return

    # Вкладки: Список та Додавання
    tab_list, tab_add = st.tabs(["📋 Список користувачів", "➕ Додати нового"])

    # --- ВКЛАДКА: СПИСОК ТА РЕДАГУВАННЯ ---
    with tab_list:
        st.subheader("Активні співробітники")
        
        for idx, row in df_users.iterrows():
            with st.expander(f"👤 {row['login']} ({row['role']})"):
                # Форма редагування для кожного користувача
                with st.form(key=f"edit_user_{idx}"):
                    col1, col2 = st.columns(2)
                    edit_login = col1.text_input("Логін (Ім'я)", value=str(row['login']))
                    edit_email = col2.text_input("Email", value=str(row['email']))
                    edit_pass = col1.text_input("Пароль", value=str(row['password']))
                    edit_role = col2.selectbox(
                        "Роль", 
                        ["Менеджер", "Виробництво", "Адмін", "Супер Адмін"],
                        index=["Менеджер", "Виробництво", "Адмін", "Супер Адмін"].index(row['role']) if row['role'] in ["Менеджер", "Виробництво", "Адмін", "Супер Адмін"] else 0
                    )
                    
                    btn_save, btn_del = st.columns([1, 1])
                    
if btn_save.form_submit_button("💾 Зберегти зміни"):
    # Створюємо новий рядок з оновленими даними
    updated_row = {
        'email': edit_email.lower().strip(),
        'login': edit_login.strip(),
        'password': str(edit_pass).strip(),
        'role': edit_role,
        'last_seen': row.get('last_seen', '-')
    }
    
    # Оновлюємо DataFrame через фільтр по email (найнадійніший спосіб)
    df_users.loc[df_users['email'] == row['email'], ['email', 'login', 'password', 'role']] = [
        updated_row['email'], updated_row['login'], updated_row['password'], updated_row['role']
    ]
    
    # Спроба збереження
    success = save_csv(USERS_CSV_ID, df_users)
    
    if success:
        st.success(f"Зміни для {edit_login} збережено в хмарі!")
        st.rerun()
    else:
        st.error("Не вдалося відправити дані на Google Drive. Перевірте консоль.")

                    # Видалення (забороняємо видаляти самого себе)
                    if row['email'] != auth_data.get('email'):
                        if btn_del.form_submit_button("🗑️ Видалити користувача"):
                            df_users = df_users.drop(idx)
                            save_csv(USERS_CSV_ID, df_users)
                            st.success("Користувача видалено!")
                            st.rerun()
                    else:
                        btn_del.info("Це ваш акаунт")

    # --- ВКЛАДКА: ДОДАВАННЯ НОВОГО ---
    with tab_add:
        st.subheader("Створення нового акаунта")
        with st.form("new_user_form", clear_on_submit=True):
            new_login = st.text_input("Ім'я (логін)")
            new_email = st.text_input("Email (для входу)")
            new_pass = st.text_input("Пароль")
            new_role = st.selectbox("Призначити роль", ["Менеджер", "Виробництво", "Адмін", "Супер Адмін"])
            
            if st.form_submit_button("✨ Створити"):
                if new_login and new_email and new_pass:
                    # Перевірка на дублікат email
                    if new_email.lower().strip() in df_users['email'].astype(str).values:
                        st.error("Користувач з таким Email вже існує!")
                    else:
                        new_data = {
                            'email': new_email.lower().strip(),
                            'login': new_login.strip(),
                            'password': str(new_pass).strip(),
                            'role': new_role,
                            'last_seen': '-'
                        }
                        df_users = pd.concat([df_users, pd.DataFrame([new_data])], ignore_index=True)
                        save_csv(USERS_CSV_ID, df_users)
                        st.success(f"Користувача {new_login} успішно додано!")
                        st.rerun()
                else:
                    st.warning("Заповніть усі поля!")
