import streamlit as st
import pandas as pd
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# --- КОНФІГУРАЦІЯ (Ваші ID) ---
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"  # Папка з PDF
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"      # Файл orders.csv

st.set_page_config(page_title="Factory CRM | Build 4.0", page_icon="🏭", layout="wide")

# --- АВТОРИЗАЦІЯ ---
@st.cache_resource
def get_drive_service():
    try:
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            # Обов'язкове виправлення формату ключа для Streamlit Cloud
            info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
            creds = service_account.Credentials.from_service_account_info(info)
            return build('drive', 'v3', credentials=creds)
        else:
            st.error("Ключі не знайдено в Secrets!")
            return None
    except Exception as e:
        st.error(f"Помилка авторизації: {e}")
        return None

# --- РОБОТА З ДАНИМИ ---
def load_data():
    service = get_drive_service()
    if not service: return pd.DataFrame()
    try:
        request = service.files().get_media(fileId=ORDERS_CSV_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        return pd.read_csv(fh, on_bad_lines='skip')
    except Exception as e:
        st.error(f"Помилка завантаження CSV: {e}")
        return pd.DataFrame()

def find_pdf_link(article):
    service = get_drive_service()
    if not service: return None
    try:
        query = f"name = '{article}.pdf' and '{FOLDER_DRAWINGS_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, webViewLink)").execute()
        files = results.get('files', [])
        return files[0]['webViewLink'] if files else None
    except:
        return None

def decode_sku(sku):
    try:
        sku = str(sku).strip()
        thickness, type_code = sku[:2], sku[2:5]
        material = "Алюміній (FA6)" if "FA6" in sku else "Стандарт"
        return f"📏 {thickness}мм | 🏗️ {type_code} | 🧪 {material}"
    except:
        return "⚙️ Параметри не визначено"

# --- ІНТЕРФЕЙС ---
st.title("🏭 Factory CRM — Build 4.0")

if 'orders_df' not in st.session_state:
    st.session_state.orders_df = load_data()

if st.button("🔄 Оновити дані"):
    st.session_state.orders_df = load_data()
    st.rerun()

df = st.session_state.orders_df

if not df.empty:
    search = st.text_input("🔍 Пошук", "")
    display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df

    for idx, row in display_df.iterrows():
        with st.expander(f"📦 Замовлення №{row.get('ID', idx)} — {row.get('Клієнт', 'Невідомо')}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                items = str(row.get('Товари', '')).split(';')
                for item in items:
                    if "[" in item:
                        sku = item.split("[")[1].split("]")[0]
                        st.markdown(f"✅ **{item}**")
                        st.caption(decode_sku(sku))
                        link = find_pdf_link(sku)
                        if link: st.link_button(f"📄 Креслення {sku}", link)
                    else: st.write(f"• {item}")
            with col2:
                st.metric("Сума", f"{row.get('Сума', 0)} грн")
                st.info(f"Статус: {row.get('Готовність', 'В роботі')}")
else:
    st.info("Підключення до бази...")
