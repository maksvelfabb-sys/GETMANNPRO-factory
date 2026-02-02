import streamlit as st
import pandas as pd
import io, json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f"
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"
COLS = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']

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
        return df[cols]
    except: return pd.DataFrame(columns=cols)

def get_drawing_link(art):
    """Шукає PDF файл за артикулом (наприклад, 20WS.8247)"""
    if not art or str(art).strip() in ["", "nan"]: return None
    service = get_drive_service()
    if not service: return None
    try:
        # Пошук файлу за назвою в конкретній папці
        q = f"'{FOLDER_DRAWINGS_ID}' in parents and name contains '{str(art).strip()}' and trashed = false"
        results = service.files().list(q=q, fields="files(id, name, webViewLink)").execute()
        files = results.get('files', [])
        if files:
            # Повертаємо посилання на перегляд файлу
            return files[0].get('webViewLink')
        return None
    except: return None

# --- АВТОРИЗАЦІЯ ---
if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP")
    e_in = st.text_input("Логін").lower()
    p_in = st.text_input("Пароль", type="password")
    if st.button("Увійти"):
        if e_in == "maksvel.fabb@gmail.com" and p_in == "1234":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- ЖУРНАЛ ---
df = load_csv(ORDERS_CSV_ID, COLS)
st.header("📋 Журнал замовлень")

for idx, row in df.iloc[::-1].iterrows():
    with st.container(border=True):
        st.subheader(f"№{row['ID']} — {row['Клієнт']}")
        
        try: items = json.loads(row['Товари_JSON'])
        except: items = []
        
        for i, it in enumerate(items):
            col_txt, col_btn = st.columns([3, 1])
            art = str(it.get('арт', '')).strip()
            col_txt.write(f"🔹 {it.get('назва')} ({art})")
            
            # --- БЕЗПЕЧНИЙ ВИКЛИК ПОСИЛАННЯ ---
            if art:
                link = get_drawing_link(art)
                if link:
                    # Тільки якщо посилання існує і це рядок, малюємо кнопку
                    col_btn.link_button("📕 ВІДКРИТИ PDF", url=str(link), use_container_width=True, key=f"btn_{row['ID']}_{i}")
                else:
                    col_btn.button("⚠️ Немає PDF", disabled=True, use_container_width=True, key=f"none_{row['ID']}_{i}")
            else:
                col_btn.button("❌ Без арту", disabled=True, use_container_width=True, key=f"empty_{row['ID']}_{i}")

        st.caption(f"Статус: {row['Готовність']}")
