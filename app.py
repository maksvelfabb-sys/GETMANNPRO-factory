import streamlit as st
import pandas as pd
import io, json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
USERS_CSV_ID = "1FDWndpOgRX21lwHk19SUoBfKyMj0K1Zc" 
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")

# --- СЕРВІСНІ ФУНКЦІЇ ---
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
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        # Використовуємо False для resumable, щоб уникнути ResumableUploadError на малих файлах
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=False)
        service.files().update(fileId=file_id, media_body=media_body).execute()
        st.toast("Синхронізовано з хмарою ✅")
    except Exception as e:
        st.error(f"Помилка Google Drive: {e}")

# --- АВТОРИЗАЦІЯ ---
if 'users_df' not in st.session_state:
    st.session_state.users_df = load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name'])

u_df = st.session_state.users_df

# Перевірка та активація Супер Адміна (Максима)
if u_df[u_df['email'] == 'maksvel.fabb@gmail.com'].empty:
    st.warning("Профіль Максима не знайдено у вказаному файлі.")
    if st.button("🚀 Створити профіль Супер Адміна"):
        new_boss = pd.DataFrame([{
            'email': 'maksvel.fabb@gmail.com', 
            'password': '1234', 
            'role': 'Супер Адмін', 
            'name': 'Максим'
        }])
        st.session_state.users_df = pd.concat([u_df, new_boss], ignore_index=True)
        save_csv(USERS_CSV_ID, st.session_state.users_df)
        st.success("Профіль активовано! Тепер увійдіть з паролем 1234")
        st.rerun()

if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP Login")
    with st.form("login"):
        email_in = st.text_input("Email")
        pass_in = st.text_input("Пароль", type="password")
        if st.form_submit_button("Увійти"):
            user = st.session_state.users_df[
                (st.session_state.users_df['email'] == email_in) & 
                (st.session_state.users_df['password'] == str(pass_in))
            ]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("❌ Невірний email або пароль")
    st.stop()

# Дані поточного сеансу
me = st.session_state.auth
role = me['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

# --- ЗАВАНТАЖЕННЯ ДАНИХ ЗАМОВЛЕНЬ ---
if 'df' not in st.session_state:
    st.session_state.df = load_csv(ORDERS_CSV_ID, ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])

# --- НАВІГАЦІЯ ---
st.sidebar.title(f"👤 {me['name']}")
st.sidebar.write(f"🛡️ Роль: **{role}**")
if st.sidebar.button("🚪 Вийти"):
    del st.session_state.auth
    st.rerun()

tabs_list = ["📋 Журнал"]
if can_edit: tabs_list.append("➕ Нове замовлення")
if role in ["Супер Адмін", "Адмін"]: tabs_list.append("⚙️ Адмін")

tabs = st.tabs(tabs_list)

# --- ВКЛАДКА: ЖУРНАЛ ---
with tabs[0]:
    search = st.text_input("🔍 Пошук по базі...")
    df_view = st.session_state.df
    if search:
        df_view = df_view[df_view.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]
    st.dataframe(df_view, use_container_width=True)

# --- ВКЛАДКА: НОВЕ ЗАМОВЛЕННЯ ---
if can_edit and "➕ Нове замовлення" in tabs_list:
    with tabs[tabs_list.index("➕ Нове замовлення")]:
        st.header("📝 Створення замовлення")
        with st.form("new_order", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n_id = c1.text_input("ID замовлення")
            n_name = c2.text_input("Клієнт")
            n_phone = c1.text_input("Телефон")
            n_city = c2.text_input("Місто")
            n_avans = st.number_input("Аванс", min_value=0.0)
            
            if st.form_submit_button("✅ Створити замовлення"):
                if n_id and n_name:
                    new_row = {
                        'ID': n_id, 'Дата': datetime.now().strftime("%d.%m.%Y"),
                        'Клієнт': n_name, 'Телефон': n_phone, 'Місто': n_city,
                        'Аванс': n_avans, 'Готовність': 'В черзі',
                        'Товари_JSON': json.dumps([{"назва": "Товар", "арт": "", "к-ть": 1, "ціна": 0.0}]),
                        'Коментар': ""
                    }
                    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, st.session_state.df)
                    st.success("Замовлення успішно додано!")
                    st.rerun()
                else:
                    st.error("Заповніть ID та ПІБ клієнта!")

# --- ВКЛАДКА: АДМІН ---
if role in ["Супер Адмін", "Адмін"]:
    with tabs[tabs_list.index("⚙️ Адмін")]:
        st.subheader("👥 Керування користувачами")
        edited_u = st.data_editor(st.session_state.users_df, num_rows="dynamic", key="user_editor")
        if st.button("💾 Зберегти зміни користувачів"):
            st.session_state.users_df = edited_u
            save_csv(USERS_CSV_ID, edited_u)
            st.rerun()
