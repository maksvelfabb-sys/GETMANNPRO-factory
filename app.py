import streamlit as st
import pandas as pd
import io, json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
USERS_CSV_ID = "1_ВАШ_ID_ФАЙЛА_КОРИСТУВАЧІВ" 
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

st.set_page_config(page_title="GETMANN Factory ERP", layout="wide", page_icon="🏭")

# --- СЕРВІСНІ ФУНКЦІЇ ДЛЯ РОБОТИ З DRIVE ---
@st.cache_resource
def get_drive_service():
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
        creds = service_account.Credentials.from_service_account_info(info)
        return build('drive', 'v3', credentials=creds)
    return None

def load_csv(file_id, cols):
    service = get_drive_service()
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh).fillna("")
        return df
    except Exception as e:
        return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        # ВИПРАВЛЕННЯ: resumable=False для маленьких CSV файлів
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=False)
        service.files().update(fileId=file_id, media_body=media_body).execute()
        st.toast("Дані успішно синхронізовано ☁️")
    except Exception as e:
        st.error(f"Помилка синхронізації з Google Drive: {e}")

def safe_float(v):
    try: return float(str(v).replace(',', '.').strip()) if v else 0.0
    except: return 0.0

# --- АВТОРИЗАЦІЯ ---
if 'users_df' not in st.session_state:
    st.session_state.users_df = load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name'])

u_df = st.session_state.users_df

# Активація Super Admin (Максим)
if u_df[u_df['email'] == 'maksvel.fabb@gmail.com'].empty:
    if st.button("Активувати профіль Super Admin (maksvel.fabb@gmail.com)"):
        new_boss = pd.DataFrame([{'email': 'maksvel.fabb@gmail.com', 'password': '1234', 'role': 'Супер Адмін', 'name': 'Максим'}])
        st.session_state.users_df = pd.concat([u_df, new_boss], ignore_index=True)
        save_csv(USERS_CSV_ID, st.session_state.users_df)
        st.rerun()

if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP Login")
    with st.form("login"):
        e = st.text_input("Email")
        p = st.text_input("Пароль", type="password")
        if st.form_submit_button("Увійти"):
            user = st.session_state.users_df[(st.session_state.users_df['email'] == e) & (st.session_state.users_df['password'] == str(p))]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("❌ Помилка")
    st.stop()

me = st.session_state.auth
role = me['role']

# --- РОЗПОДІЛ ВКЛАДОК ---
tabs_list = ["📋 Журнал"]
if role in ["Супер Адмін", "Адмін", "Менеджер"]: tabs_list.append("➕ Нове замовлення")
if role in ["Супер Адмін", "Адмін"]: 
    tabs_list.append("👥 Персонал")
    tabs_list.append("⚙️ База")

tabs = st.tabs(tabs_list)

# --- ЛОГІКА ТАБІВ (Скорочено для стабільності) ---
if 'df' not in st.session_state:
    st.session_state.df = load_csv(ORDERS_CSV_ID, ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])

with tabs[0]:
    st.subheader("📋 Список замовлень")
    # Тут стандартний код відображення Журналу
    st.dataframe(st.session_state.df, use_container_width=True)

if "👥 Персонал" in tabs_list:
    with tabs[tabs_list.index("👥 Персонал")]:
        st.header("👥 Керування користувачами")
        edited_u = st.data_editor(st.session_state.users_df, num_rows="dynamic")
        if st.button("💾 Зберегти зміни"):
            st.session_state.users_df = edited_u
            save_csv(USERS_CSV_ID, edited_u)
            st.rerun()

# --- КНОПКА ВИХОДУ ---
if st.sidebar.button("Вийти"):
    del st.session_state.auth
    st.rerun()
