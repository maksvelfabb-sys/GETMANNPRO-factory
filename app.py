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
        df = pd.read_csv(fh).fillna("")
        # Примусово прибираємо зайві пробіли з назв колонок
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame(columns=['ID', 'Клієнт', 'Телефон', 'Місто', 'Відділення', 'Товари', 'Сума', 'Готовність', 'Коментар'])

def save_data(df):
    service = get_drive_service()
    if not service: return
    try:
        csv_buffer = io.BytesIO()
        df.to_csv(io.TextIOWrapper(csv_buffer, encoding='utf-8'), index=False)
        csv_buffer.seek(0)
        media = MediaIoBaseUpload(csv_buffer, mimetype='text/csv', resumable=True)
        service.files().update(fileId=ORDERS_CSV_ID, media_body=media).execute()
        st.toast("Синхронізовано ✅")
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

tabs = st.tabs(["📋 Список замовлень", "➕ Нове замовлення", "📦 Склад"])

with tabs[0]:
    df = st.session_state.df
    search = st.text_input("🔍 Пошук")
    
    display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df

    for idx, row in display_df.iterrows():
        # БЕЗПЕЧНЕ ОТРИМАННЯ ДАНИХ (щоб не було KeyError)
        r_id = str(row.get('ID', ''))
        r_client = str(row.get('Клієнт', ''))
        r_city = str(row.get('Місто', ''))
        r_status = str(row.get('Готовність', 'В черзі'))
        r_phone = str(row.get('Телефон', ''))
        r_post = str(row.get('Відділення', ''))
        r_items = str(row.get('Товари', ''))
        r_comm = str(row.get('Коментар', ''))
        
        icon = "⚪"
        if r_status == "В роботі": icon = "🔵"
        elif r_status == "Готово": icon = "🟢"
        
        header = f"{icon} {r_id} | {r_client} | {r_city}"
        
        with st.expander(header):
            c1, c2, c3 = st.columns(3)
            new_id = c1.text_input("ID", value=r_id, key=f"id_{idx}")
            new_client = c2.text_input("Клієнт", value=r_client, key=f"cl_{idx}")
            new_phone = c3.text_input("Телефон", value=r_phone, key=f"ph_{idx}")
            
            c4, c5, c6 = st.columns(3)
            new_city = c4.text_input("Місто", value=r_city, key=f"ct_{idx}")
            new_post = c5.text_input("Відділення", value=r_post, key=f"ps_{idx}")
            
            # Сума
            try:
                raw_s = str(row.get('Сума', '0')).replace(',', '.').split('.')[0]
                curr_s = int(raw_s) if raw_s.isdigit() else 0
            except: curr_s = 0
            new_sum = c6.number_input("Сума, грн", value=curr_s, key=f"sm_{idx}")
            
            new_items = st.text_area("Товари", value=r_items, key=f"it_{idx}")
            new_comm = st.text_input("Коментар", value=r_comm, key=f"co_{idx}")
            
            # Статуси
            st.write("**Статус:**")
            ca1, ca2, ca3 = st.columns(3)
            if ca1.button("🔵 В роботу", key=f"bw_{idx}", use_container_width=True):
                df.at[idx, 'Готовність'] = "В роботі"; save_data(df); st.rerun()
            if ca2.button("🟢 Виконано", key=f"bd_{idx}", use_container_width=True):
                df.at[idx, 'Готовність'] = "Готово"; save_data(df); st.rerun()
            if ca3.button("⚪ В чергу", key=f"bq_{idx}", use_container_width=True):
                df.at[idx, 'Готовність'] = "В черзі"; save_data(df); st.rerun()
            
            # Креслення
            for item in new_items.split(';'):
                if "[" in item:
                    sku = item.split("[")[1].split("]")[0]
                    link = find_pdf_link(sku)
                    if link: st.link_button(f"📄 Креслення {sku}", link)

            # Збереження змін
            if (new_id != r_id or new_client != r_client or new_phone != r_phone or 
                new_city != r_city or new_post != r_post or new_items != r_items or 
                new_comm != r_comm or new_sum != curr_s):
                
                df.at[idx, 'ID'], df.at[idx, 'Клієнт'] = new_id, new_client
                df.at[idx, 'Телефон'], df.at[idx, 'Місто'] = new_phone, new_city
                df.at[idx, 'Відділення'], df.at[idx, 'Товари'] = new_post, new_items
                df.at[idx, 'Коментар'], df.at[idx, 'Сума'] = new_comm, new_sum
                save_data(df)

with tabs[1]:
    st.subheader("Нове замовлення")
    with st.form("add"):
        f1, f2, f3 = st.columns(3)
        fid = f1.text_input("ID"); fcl = f2.text_input("Клієнт"); fph = f3.text_input("Телефон")
        f4, f5, f6 = st.columns(3)
        fct = f4.text_input("Місто"); fps = f5.text_input("Відділення"); fsm = f6.number_input("Сума", min_value=0)
        fit = st.text_area("Товари"); fco = st.text_input("Коментар")
        if st.form_submit_button("Зберегти"):
            new_r = {'ID': fid, 'Клієнт': fcl, 'Телефон': fph, 'Місто': fct, 'Відділення': fps, 
                     'Товари': fit, 'Сума': fsm, 'Готовність': 'В черзі', 'Коментар': fco}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_r])], ignore_index=True)
            save_data(st.session_state.df); st.rerun()

st.sidebar.button("🔄 Оновити", on_click=lambda: st.session_state.pop('df'))
