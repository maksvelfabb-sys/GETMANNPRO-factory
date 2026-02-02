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

# СТИЛІЗАЦІЯ (CSS для кольорових карток)
st.markdown("""
    <style>
    .order-card { padding: 20px; border-radius: 12px; margin-bottom: 15px; border-left: 10px solid #d1d1d1; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-work { border-left-color: #007bff; background-color: #f0f7ff; }
    .status-done { border-left-color: #28a745; background-color: #f2fff5; }
    .status-queue { border-left-color: #6c757d; background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

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
        csv_buffer = io.BytesIO()
        df.to_csv(io.TextIOWrapper(csv_buffer, encoding='utf-8'), index=False)
        csv_buffer.seek(0)
        media = MediaIoBaseUpload(csv_buffer, mimetype='text/csv', resumable=True)
        service.files().update(fileId=ORDERS_CSV_ID, media_body=media).execute()
        st.toast("Дані синхронізовано ☁️")
    except Exception as e:
        st.error(f"Помилка збереження: {e}")

def find_pdf_link(article):
    service = get_drive_service()
    if not service: return None
    try:
        query = f"name = '{article}.pdf' and '{FOLDER_DRAWINGS_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, webViewLink)").execute()
        files = results.get('files', [])
        return files[0]['webViewLink'] if files else None
    except: return None

# --- ГОЛОВНИЙ ІНТЕРФЕЙС ---
st.title("🏭 GETMANN Pro")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

tabs = st.tabs(["📋 Замовлення", "➕ Нове замовлення", "📦 Склад"])

with tabs[0]:
    df = st.session_state.df
    search = st.text_input("🔍 Пошук (клієнт, товар або ID)")
    
    display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df

    for idx, row in display_df.iterrows():
        # Динамічний клас для кольору картки
        card_style = "status-queue"
        if row['Готовність'] == "В роботі": card_style = "status-work"
        elif row['Готовність'] == "Готово": card_style = "status-done"
        
        st.markdown(f'<div class="order-card {card_style}">', unsafe_allow_html=True)
        
        c1, c2 = st.columns([3, 1])
        
        with c1:
            # РЕДАГУВАННЯ КЛІЄНТА ТА ID
            col_id, col_cl = st.columns([1, 2])
            new_id = col_id.text_input("ID", value=row['ID'], key=f"id_{idx}")
            new_client = col_cl.text_input("Клієнт", value=row['Клієнт'], key=f"cl_{idx}")
            
            # РЕДАГУВАННЯ ТОВАРІВ
            new_items = st.text_area("Товари", value=row['Товари'], key=f"it_{idx}", height=100)
            
            # РЕДАГУВАННЯ КОМЕНТАРЯ
            new_comm = st.text_input("Коментар", value=row['Коментар'], key=f"co_{idx}")
            
            # Перевірка змін для збереження
            if (new_id != row['ID'] or new_client != row['Клієнт'] or 
                new_items != row['Товари'] or new_comm != row['Коментар']):
                df.at[idx, 'ID'] = new_id
                df.at[idx, 'Клієнт'] = new_client
                df.at[idx, 'Товари'] = new_items
                df.at[idx, 'Коментар'] = new_comm
                save_data(df)

            # Кнопки креслень (Парсинг артикулів)
            for item in str(new_items).split(';'):
                if "[" in item:
                    sku = item.split("[")[1].split("]")[0]
                    link = find_pdf_link(sku)
                    if link: st.link_button(f"📄 Креслення {sku}", link)

        with c2:
            st.write(f"**Статус: {row['Готовність']}**")
            if st.button("🔵 В роботу", key=f"btn_w_{idx}", use_container_width=True):
                df.at[idx, 'Готовність'] = "В роботі"; save_data(df); st.rerun()
            if st.button("🟢 Виконано", key=f"btn_d_{idx}", use_container_width=True):
                df.at[idx, 'Готовність'] = "Готово"; save_data(df); st.rerun()
            if st.button("⚪ В чергу", key=f"btn_q_{idx}", use_container_width=True):
                df.at[idx, 'Готовність'] = "В черзі"; save_data(df); st.rerun()
            
            st.markdown("---")
            new_sum = st.number_input("Сума, грн", value=int(row['Сума']) if str(row['Sum']).isdigit() else 0, key=f"sum_{idx}")
            if new_sum != row['Сума']:
                df.at[idx, 'Сума'] = new_sum
                save_data(df)
            
        st.markdown('</div>', unsafe_allow_html=True)

with tabs[1]:
    st.subheader("Додати нове замовлення")
    with st.form("add_order"):
        f_id = st.text_input("ID замовлення")
        f_client = st.text_input("Клієнт")
        f_items = st.text_area("Товари (Артикули в [])")
        f_sum = st.number_input("Сума", min_value=0)
        f_comm = st.text_input("Коментар")
        if st.form_submit_button("Створити замовлення"):
            new_row = {'ID': f_id, 'Клієнт': f_client, 'Товари': f_items, 'Сума': f_sum, 'Готовність': 'В черзі', 'Коментар': f_comm}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df); st.rerun()

st.sidebar.button("🔄 Повне оновлення", on_click=lambda: st.session_state.pop('df'))
