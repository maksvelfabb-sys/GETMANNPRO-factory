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

def get_pdf_link(art):
    """Шукає PDF за артикулом і повертає чисте посилання"""
    if not art or str(art).strip() in ["", "nan"]: return None
    service = get_drive_service()
    try:
        q = f"'{FOLDER_DRAWINGS_ID}' in parents and name contains '{str(art).strip()}' and trashed = false"
        res = service.files().list(q=q, fields="files(webViewLink)").execute()
        files = res.get('files', [])
        return files[0]['webViewLink'] if files else None
    except: return None

# --- АВТОРИЗАЦІЯ ---
if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP")
    with st.form("login"):
        e = st.text_input("Логін").lower()
        p = st.text_input("Пароль", type="password")
        if st.form_submit_button("Увійти"):
            if e == "maksvel.fabb@gmail.com" and p == "1234":
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- ВІДОБРАЖЕННЯ ---
df = load_csv(ORDERS_CSV_ID, COLS)
st.header("📋 Журнал замовлень")

for idx, row in df.iloc[::-1].iterrows():
    with st.container(border=True):
        st.subheader(f"№{row['ID']} — {row['Клієнт']}")
        
        try: items = json.loads(row['Товари_JSON'])
        except: items = []
        
        for i, it in enumerate(items):
            col_t, col_b = st.columns([3, 1])
            art = str(it.get('арт', '')).strip()
            col_t.write(f"🔹 {it.get('назва')} (**{art}**)")
            
            # --- НОВИЙ МЕТОД: ВИКОРИСТОВУЄМО JS ДЛЯ ВІДКРИТТЯ ---
            if art:
                link = get_pdf_link(art)
                if link:
                    # Створюємо кнопку, яка виглядає як звичайна, але працює через HTML
                    link_html = f'''
                        <a href="{link}" target="_blank" style="text-decoration: none;">
                            <div style="background-color: #ff4b4b; color: white; padding: 8px 16px; border-radius: 5px; text-align: center; font-weight: bold;">
                                📕 ВІДКРИТИ PDF
                            </div>
                        </a>
                    '''
                    col_b.markdown(link_html, unsafe_allow_html=True)
                else:
                    col_b.button("❌ Немає PDF", disabled=True, key=f"no_{idx}_{i}", use_container_width=True)
            else:
                col_b.button("⚪ Без арту", disabled=True, key=f"empty_{idx}_{i}", use_container_width=True)

        st.caption(f"Статус: {row['Готовність']} | Артикул на кресленні: 20WS.8247")
