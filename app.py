import streamlit as st
import pandas as pd
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

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
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    media = MediaFileUpload(io.BytesIO(csv_buffer.getvalue().encode()), mimetype='text/csv')
    service.files().update(fileId=ORDERS_CSV_ID, media_body=media).execute()

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
        # Визначаємо колір заголовка залежно від статусу
        status = row['Готовність']
        status_emoji = "⚪"
        if status == "В роботі": status_emoji = "🔵"
        if status == "Готово": status_emoji = "🟢"
        
        with st.container(border=True):
            col_info, col_actions = st.columns([3, 1])
            
            with col_info:
                st.markdown(f"### {status_emoji} {row['Клієнт']} (ID: {row['ID']})")
                st.write(f"**Товари:** {row['Товари']}")
                
                # Поле для редагування коментаря прямо в картці
                new_comment = st.text_input("Коментар до замовлення", value=row['Коментар'], key=f"comm_{idx}")
                if new_comment != row['Коментар']:
                    df.at[idx, 'Коментар'] = new_comment
                    save_data(df)
                    st.toast("Коментар оновлено")

            with col_actions:
                st.write("**Статус:**")
                # КНОПКИ ЯК У ПОПЕРЕДНІЙ ВЕРСІЇ
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
    # (Код форми додавання залишається такий самий, як у попередній версії)
    st.subheader("Нове замовлення")
    # ... (код форми)
