import streamlit as st
import pandas as pd
import io, json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f" 
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"
COLS = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']
USER_COLS = ['email', 'password', 'role']

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")

# --- СЕРВІСИ DRIVE ---
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
        df = pd.read_csv(fh, dtype=str).fillna("")
        for c in cols:
            if c not in df.columns: df[c] = ""
        return df[cols]
    except: return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=False)
        service.files().update(fileId=file_id, media_body=media_body).execute()
        st.cache_data.clear()
        st.toast("Дані синхронізовано ✅")
    except: st.error("Помилка Drive")

def get_drawing_link(art):
    if not art or pd.isna(art) or str(art).strip() == "": return None
    service = get_drive_service()
    try:
        query = f"'{FOLDER_DRAWINGS_ID}' in parents and name contains '{art}' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
        files = results.get('files', [])
        if files and 'webViewLink' in files[0]:
            return str(files[0]['webViewLink'])
        return None
    except: return None

# --- АВТОРИЗАЦІЯ (maksvel.fabb@gmail.com) ---
if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP")
    with st.container(border=True):
        e_in = st.text_input("Логін (Email)").strip().lower()
        p_in = st.text_input("Пароль", type="password").strip()
        if st.button("Увійти", use_container_width=True):
            if e_in == "maksvel.fabb@gmail.com" and p_in == "1234":
                st.session_state.auth = {'email': e_in, 'role': 'Супер Адмін'}
                st.rerun()
            u_df = load_csv(USERS_CSV_ID, USER_COLS)
            user = u_df[(u_df['email'].str.lower() == e_in) & (u_df['password'] == p_in)]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Доступ обмежено")
    st.stop()

role = st.session_state.auth.get('role', 'Гість')

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏢 МЕНЮ")
    nav = ["📋 Замовлення", "⚙️ Налаштування"]
    if role == "Супер Адмін": nav.append("👥 Користувачі")
    menu = st.radio("Навігація:", nav)
    if st.button("🚪 Вихід"):
        del st.session_state.auth
        st.rerun()

# --- СТОРІНКА: ЗАМОВЛЕННЯ ---
if menu == "📋 Замовлення":
    st.header("Журнал замовлень")
    df = load_csv(ORDERS_CSV_ID, COLS)
    
    # Виведення замовлень (від нових до старих)
    df_v = df.copy().iloc[::-1]
    
    for idx, row in df_v.iterrows():
        # Створення унікального ID для блоку (використовуємо реальний ID замовлення)
        order_id = str(row['ID'])
        
        with st.container(border=True):
            st.markdown(f"### 📦 Замовлення №{order_id} — {row['Клієнт']}")
            
            try:
                items = json.loads(row['Товари_JSON'])
            except:
                items = []
            
            # Таблиця товарів всередині картки
            for i, it in enumerate(items):
                c_name, c_btn = st.columns([3, 1])
                art = str(it.get('арт', '')).strip()
                c_name.write(f"🔹 {it.get('назва')} ({art}) — {it.get('к-ть')} шт.")
                
                # --- ВИПРАВЛЕННЯ ПОМИЛКИ TYPEERROR ---
                link = get_drawing_link(art)
                
                # Перевіряємо, чи link - це дійсно рядок і чи він не пустий
                if isinstance(link, str) and len(link) > 10:
                    c_btn.link_button("📕 PDF", url=link, use_container_width=True, key=f"lk_{order_id}_{i}")
                else:
                    c_btn.button("⚠️ PDF", disabled=True, use_container_width=True, key=f"no_{order_id}_{i}", help="Креслення не знайдено")
            
            st.divider()
            st.write(f"**Статус:** {row['Готовність']} | **Телефон:** {row['Телефон']}")

elif menu == "👥 Користувачі":
    st.write("Список користувачів доступний Супер Адміну.")
