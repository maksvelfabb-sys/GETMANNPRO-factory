import streamlit as st
import pandas as pd
import io, json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ТА БЕЗПЕКА ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
USERS_CSV_ID = "1_id_вашого_файла_користувачів" # Створіть файл з полями: username, password, role
st.set_page_config(page_title="GETMANN Factory Control", layout="wide")

# Визначення прав для ролей
ROLE_PERMISSIONS = {
    "Адмін": {"view_finance": True, "edit_orders": True, "admin_tab": True, "view_contacts": True},
    "Менеджер": {"view_finance": True, "edit_orders": True, "admin_tab": False, "view_contacts": True},
    "Токар": {"view_finance": False, "edit_orders": False, "admin_tab": False, "view_contacts": False}
}

# --- ФУНКЦІЇ ДОСТУПУ ---
def check_login():
    if "user" not in st.session_state:
        st.title("🔐 Вхід у систему")
        user = st.text_input("Логін")
        pw = st.text_input("Пароль", type="password")
        if st.button("Увійти"):
            # Тут можна підключити USERS_CSV_ID для перевірки
            # Тимчасовий хардкод для тесту:
            if user == "admin" and pw == "1234":
                st.session_state.user = {"name": "Адмін", "role": "Адмін"}
                st.rerun()
            elif user == "master" and pw == "5555":
                st.session_state.user = {"name": "Іван (Токар)", "role": "Токар"}
                st.rerun()
            else:
                st.error("Невірні дані")
        return False
    return True

if not check_login():
    st.stop()

user_role = st.session_state.user["role"]
perms = ROLE_PERMISSIONS[user_role]

# --- ГРУПУВАННЯ ІНТЕРФЕЙСУ ЗА ПРАВАМИ ---
st.sidebar.write(f"👤 Користувач: **{st.session_state.user['name']}**")
st.sidebar.write(f"🛡️ Роль: `{user_role}`")

tabs_list = ["📋 Журнал"]
if perms["edit_orders"]: tabs_list.append("➕ Нове замовлення")
if perms["admin_tab"]: tabs_list.append("⚙️ Адмін-панель")
tabs = st.tabs(tabs_list)

# --- ЛОГІКА ЖУРНАЛУ (З ФІЛЬТРОМ ПРАВ) ---
with tabs[0]:
    df = load_data() # ваша функція завантаження
    for idx, row in df.iterrows():
        # СТАТУСНА ШАПКА (Бачать всі)
        st.markdown(f"### №{row['ID']} | {row['Клієнт'] if perms['view_contacts'] else 'ЗАМОВЛЕННЯ'}")
        
        with st.expander("👁️ Переглянути деталі"):
            # Відображення товарів та креслень (Бачать всі)
            items = json.loads(row['Товари_JSON'])
            for i in items:
                st.write(f"• {i['назва']} (Арт: {i['арт']}) - **{i['к-ть']} шт**")
                # Кнопка креслення доступна всім ролям
                # if i['арт']: find_and_show_pdf(i['арт']) 

            st.divider()
            
            # ФІНАНСОВИЙ БЛОК (Лише Адмін/Менеджер)
            if perms["view_finance"]:
                st.write(f"💰 Сума: {row['Сума']} | Аванс: {row['Аванс']}")
            
            # КОНТАКТИ (Лише Адмін/Менеджер)
            if perms["view_contacts"]:
                st.write(f"📞 {row['Телефон']} | 📍 {row['Місто']}")

            # КНОПКИ СТАТУСУ (Токар може лише завершити)
            if user_role == "Токар":
                if st.button("✅ Я виконав це замовлення", key=f"done_{idx}"):
                    update_status(idx, "Готово")
            elif perms["edit_orders"]:
                # Повний блок редагування для Менеджера/Адміна
                pass

# --- АДМІНКА (ТІЛЬКИ ДЛЯ АДМІНІВ) ---
if perms["admin_tab"]:
    with tabs[-1]:
        st.header("Керування користувачами")
        # Тут можна додавати нових користувачів у USERS_CSV_ID
        st.info("Тут ви можете змінювати ролі працівників")
