import streamlit as st
import pandas as pd
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

st.set_page_config(page_title="GETMANN Pro", layout="wide", page_icon="🏭")

# --- СЕРВІСНІ ФУНКЦІЇ ---
@st.cache_resource
def get_drive_service():
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
        creds = service_account.Credentials.from_service_account_info(info)
        return build('drive', 'v3', credentials=creds)
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
    if not service: return
    try:
        # Перетворюємо DataFrame в CSV
        csv_buffer = io.BytesIO()
        df.to_csv(io.TextIOWrapper(csv_buffer, encoding='utf-8'), index=False)
        csv_buffer.seek(0)
        
        # Використовуємо MediaIoBaseUpload для роботи з BytesIO
        media = MediaIoBaseUpload(csv_buffer, mimetype='text/csv', resumable=True)
        service.files().update(fileId=ORDERS_CSV_ID, media_body=media).execute()
        st.toast("Синхронізовано з хмарою ✅")
    except Exception as e:
        st.error(f"Помилка збереження: {e}")

# --- ГОЛОВНИЙ ІНТЕРФЕЙС ---
st.title("🏭 GETMANN Pro")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

tabs = st.tabs(["📋 Замовлення", "➕ Нове замовлення", "📦 Склад"])

with tabs[0]:
    df = st.session_state.df
    search = st.text_input("🔍 Пошук")
    
    display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df

    for idx, row in display_df.iterrows():
        status = row['Готовність']
        # Кольорова індикація
        if status == "В роботі": color = "primary"
        elif status == "Готово": color = "success"
        else: color = "secondary"
        
        with st.container(border=True):
            col_info, col_actions = st.columns([3, 1])
            
            with col_info:
                st.subheader(f"{row['Клієнт']} (ID: {row['ID']})")
                st.write(f"**Товари:** {row['Товари']}")
                
                # Редагування коментаря
                new_comment = st.text_input("Редагувати коментар", value=row['Коментар'], key=f"comm_{idx}")
                if new_comment != row['Коментар']:
                    df.at[idx, 'Коментар'] = new_comment
                    save_data(df)

            with col_actions:
                st.write(f"**Статус: {status}**")
                # Кнопки швидкої зміни статусу
                if st.button("🔵 В роботу", key=f"work_{idx}", use_container_width=True):
                    df.at[idx, 'Готовність'] = "В роботі"
                    save_data(df)
                    st.rerun()
                
                if st.button("🟢 Виконано", key=f"done_{idx}", use_container_width=True):
                    df.at[idx, 'Готовність'] = "Готово"
                    save_data(df)
                    st.rerun()
                
                if st.button("⚪ В чергу", key=f"queue_{idx}", use_container_width=True):
                    df.at[idx, 'Готовність'] = "В черзі"
                    save_data(df)
                    st.rerun()

with tabs[1]:
    st.subheader("Створити нове замовлення")
    with st.form("new_order_form"):
        f_id = st.text_input("ID")
        f_client = st.text_input("Клієнт")
        f_items = st.text_area("Товари")
        f_sum = st.number_input("Сума", min_value=0)
        f_comment = st.text_input("Коментар")
        
        if st.form_submit_button("Зберегти на диск"):
            new_row = {'ID': f_id, 'Клієнт': f_client, 'Товари': f_items, 
                       'Сума': f_sum, 'Готовність': 'В черзі', 'Коментар': f_comment}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df)
            st.rerun()

st.sidebar.button("🔄 Оновити дані", on_click=lambda: st.session_state.pop('df'))
