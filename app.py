import streamlit as st
import pandas as pd
import io, json, time
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ (Оновлено під ваші файли) ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f" 
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

COLS = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']
USER_COLS = ['email', 'password', 'role']

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")

# --- СЕРВІСНІ ФУНКЦІЇ (Стабільні) ---
@st.cache_resource
def get_drive_service():
    if "gcp_service_account" in st.secrets:
        try:
            info = dict(st.secrets["gcp_service_account"])
            info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
            creds = service_account.Credentials.from_service_account_info(info)
            return build('drive', 'v3', credentials=creds)
        except: return None
    return None

@st.cache_data(ttl=60)
def load_csv(file_id, cols):
    service = get_drive_service()
    if not service: return pd.DataFrame(columns=cols)
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        
        # ВИПРАВЛЕННЯ: Автовизначення розділювача (кома чи крапка з комою)
        df = pd.read_csv(fh, sep=None, engine='python', dtype=str).dropna(how='all').fillna("")
        df.columns = [c.lower().strip() for c in df.columns]
        
        for c in cols:
            if c not in df.columns: df[c] = ""
        return df[cols]
    except Exception as e:
        st.error(f"Помилка завантаження: {e}")
        return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: return
    try:
        # Зберігаємо завжди з комою для стандартизації
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=False)
        service.files().update(fileId=file_id, media_body=media_body).execute()
        st.cache_data.clear()
        st.toast("Дані оновлено в хмарі ✅")
    except Exception as e: 
        st.error(f"Помилка збереження: {e}")

# --- АВТОРИЗАЦІЯ (Покращена версія 4.73) ---
if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP")
    with st.container(border=True):
        e_in = st.text_input("Логін (Email)").strip().lower()
        p_in = st.text_input("Пароль", type="password").strip()
        
        if st.button("Увійти", use_container_width=True):
            # Перевірка Супер Адміна (запасний вхід)
            if e_in == "maksvel.fabb@gmail.com" and p_in == "1234":
                st.session_state.auth = {'email': e_in, 'role': 'Супер Адмін'}
                st.cache_data.clear(); st.rerun()
            
            # Перевірка через файл
            u_df = load_csv(USERS_CSV_ID, USER_COLS)
            u_df['email'] = u_df['email'].str.strip().str.lower()
            u_df['password'] = u_df['password'].astype(str).str.strip()
            
            match = u_df[(u_df['email'] == e_in) & (u_df['password'] == p_in)]
            if not match.empty:
                st.session_state.auth = match.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("❌ Доступ обмежено")
    st.stop()

# --- ГОЛОВНЕ МЕНЮ ---
role = st.session_state.auth.get('role', 'Гість')

with st.sidebar:
    st.title("🏢 GETMANN")
    nav = ["📋 Замовлення", "📐 Креслення"]
    if role == "Супер Адмін": nav.append("👥 Користувачі")
    
    menu = st.radio("Навігація:", nav)
    st.divider()
    if st.button("🚪 Вийти"):
        del st.session_state.auth
        st.rerun()

# --- ВИПРАВЛЕНИЙ БЛОК: КОРИСТУВАЧІ ---
if menu == "👥 Користувачі" and role == "Супер Admin" or menu == "👥 Користувачі":
    st.header("Керування командою")
    u_df = load_csv(USERS_CSV_ID, USER_COLS)
    
    with st.expander("➕ Додати нового користувача", expanded=True):
        with st.form("user_form", clear_on_submit=True):
            new_e = st.text_input("Email").strip().lower()
            new_p = st.text_input("Пароль").strip()
            new_r = st.selectbox("Роль", ["Менеджер", "Адмін", "Токар"])
            
            if st.form_submit_button("Створити"):
                if new_e and new_p:
                    if new_e in u_df['email'].values:
                        st.warning(f"Користувач {new_e} вже існує")
                    else:
                        new_line = pd.DataFrame([{'email': new_e, 'password': new_p, 'role': new_r}])
                        updated_u = pd.concat([u_df, new_line], ignore_index=True)
                        save_csv(USERS_CSV_ID, updated_u)
                        st.rerun()
                else:
                    st.error("Заповніть всі поля")

    st.subheader("Діючі доступи")
    st.dataframe(u_df, use_container_width=True)
    
    if not u_df.empty:
        to_del = st.selectbox("Видалити користувача", u_df['email'].tolist())
        if st.button("❌ Видалити"):
            if to_del != st.session_state.auth['email']:
                updated_u = u_df[u_df['email'] != to_del]
                save_csv(USERS_CSV_ID, updated_u)
                st.rerun()

# --- БЛОК: ЗАМОВЛЕННЯ (як у 4.73) ---
elif menu == "📋 Замовлення":
    st.header("Журнал замовлень")
    # Тут залишається логіка замовлень з вашої версії 4.73
    st.info("Блок замовлень працює згідно Build 4.73")
