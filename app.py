import streamlit as st
import pandas as pd
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# --- КОНФІГУРАЦІЯ ---
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"

st.set_page_config(page_title="Factory CRM | Build 4.1", layout="wide")

# --- СЕРВІСНІ ФУНКЦІЇ ---
@st.cache_resource
def get_drive_service():
    try:
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
            creds = service_account.Credentials.from_service_account_info(info)
            return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Помилка авторизації: {e}")
    return None

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
        return pd.read_csv(fh).fillna("")
    except:
        return pd.DataFrame(columns=['ID', 'Клієнт', 'Товари', 'Сума', 'Готовність', 'Коментар'])

def save_data(df):
    service = get_drive_service()
    try:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        media = MediaFileUpload(
            io.BytesIO(csv_buffer.getvalue().encode()), 
            mimetype='text/csv', 
            resumable=True
        )
        service.files().update(fileId=ORDERS_CSV_ID, media_body=media).execute()
        st.success("Дані збережено в хмарі! ✅")
    except Exception as e:
        st.error(f"Помилка збереження: {e}")

# --- ЛОГІКА ПРОГРАМИ ---
st.title("🏭 Factory CRM — Build 4.1")

if 'orders_df' not in st.session_state:
    st.session_state.orders_df = load_data()

tabs = st.tabs(["📋 Список замовлень", "➕ Додати замовлення", "📦 Склад матеріалів"])

# --- ВКЛАДКА 1: СПИСОК ТА СТАТУСИ ---
with tabs[0]:
    df = st.session_state.orders_df
    search = st.text_input("🔍 Пошук замовлення")
    
    for idx, row in df.iterrows():
        if search.lower() in str(row.values).lower():
            with st.expander(f"📦 {row['Клієнт']} (ID: {row['ID']}) — {row['Готовність']}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Товари:** {row['Товари']}")
                    # Тут можна додати логіку пошуку PDF як раніше
                
                with col2:
                    new_status = st.selectbox(
                        "Змінити статус", 
                        ["В черзі", "В роботі", "Готово", "Відвантажено"], 
                        key=f"status_{idx}",
                        index=["В черзі", "В роботі", "Готово", "Відвантажено"].index(row['Готовність']) if row['Готовність'] in ["В черзі", "В роботі", "Готово", "Відвантажено"] else 0
                    )
                    if new_status != row['Готовність']:
                        df.at[idx, 'Готовність'] = new_status
                        save_data(df)
                        st.rerun()

# --- ВКЛАДКА 2: АДМІН-ПАНЕЛЬ ---
with tabs[1]:
    st.subheader("Нове замовлення")
    with st.form("new_order"):
        new_id = st.text_input("ID замовлення")
        new_client = st.text_input("Клієнт")
        new_items = st.text_area("Товари (через ;)")
        new_sum = st.number_input("Сума", min_value=0)
        
        if st.form_submit_button("Створити замовлення"):
            new_row = {
                'ID': new_id, 'Клієнт': new_client, 
                'Товари': new_items, 'Сума': new_sum, 
                'Готовність': 'В черзі', 'Коментар': ''
            }
            st.session_state.orders_df = pd.concat([st.session_state.orders_df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.orders_df)
            st.rerun()

# --- ВКЛАДКА 3: СКЛАД (ПРОСТИЙ) ---
with tabs[2]:
    st.info("Цей розділ буде синхронізовано з окремим файлом materials.csv у наступному патчі.")
