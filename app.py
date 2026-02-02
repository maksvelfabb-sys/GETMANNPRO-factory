import streamlit as st
import pandas as pd
import io, json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ (ID ВАШІ) ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"
COLS = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']
USER_COLS = ['email', 'password', 'role']

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")

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

def get_drawing_link(art):
    """Шукає файл за артикулом (наприклад, 20WS.8247) та повертає URL"""
    if not art or pd.isna(art): return None
    art_str = str(art).strip()
    if art_str in ["", "nan", "None"]: return None
    
    service = get_drive_service()
    if not service: return None
    
    try:
        # Пошук файлу, назва якого містить артикул
        query = f"'{FOLDER_DRAWINGS_ID}' in parents and name contains '{art_str}' and trashed = false"
        results = service.files().list(q=query, fields="files(webViewLink)").execute()
        files = results.get('files', [])
        
        if files and 'webViewLink' in files[0]:
            return str(files[0]['webViewLink'])
        return None
    except:
        return None

# --- АВТОРИЗАЦІЯ ( maksvel.fabb@gmail.com ) ---
if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP")
    with st.container(border=True):
        e_in = st.text_input("Логін").strip().lower()
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

# --- ЖУРНАЛ ЗАМОВЛЕНЬ ---
df = load_csv(ORDERS_CSV_ID, COLS)
df_v = df.copy().iloc[::-1]

st.header("📋 Журнал замовлень")

for idx, row in df_v.iterrows():
    order_id = str(row['ID'])
    with st.container(border=True):
        st.subheader(f"Замовлення №{order_id} — {row['Клієнт']}")
        
        try:
            items = json.loads(row['Товари_JSON'])
        except:
            items = []
        
        for i, it in enumerate(items):
            c_info, c_btn = st.columns([3, 1])
            art = str(it.get('арт', '')).strip()
            c_info.write(f"🔹 **{it.get('назва')}** (Арт: {art}) — {it.get('к-ть')} шт.")
            
            # --- ПЕРЕВІРКА ПОСИЛАННЯ ПЕРЕД СТВОРЕННЯМ КНОПКИ ---
            link = get_drawing_link(art)
            
            if link and isinstance(link, str) and link.startswith("http"):
                # Кнопка-посилання (тільки якщо URL валідний)
                c_btn.link_button("📕 PDF Креслення", url=link, use_container_width=True, key=f"lk_{order_id}_{i}")
            else:
                # Звичайна неактивна кнопка (якщо файлу немає або помилка)
                c_btn.button("📕 Не знайдено", disabled=True, use_container_width=True, key=f"no_{order_id}_{i}")

        if row['Коментар']:
            st.info(f"💬 {row['Коментар']}")
