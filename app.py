import streamlit as st
import pandas as pd
import io
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КЛЮЧОВІ НАЛАШТУВАННЯ (З Build 3.0) ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

st.set_page_config(page_title="GETMANN Pro", layout="wide", page_icon="🏭")

# --- ОРИГІНАЛЬНИЙ СТИЛЬ 3.0 ---
st.markdown("""
    <style>
    .order-card {
        border: 1px solid #444;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: #1e1e1e;
        color: white;
    }
    .status-work { border-left: 10px solid #007bff; }
    .status-done { border-left: 10px solid #28a745; }
    .status-queue { border-left: 10px solid #888; }
    .stCheckbox label { font-size: 18px !important; font-weight: bold; }
    .item-list { margin-top: 10px; font-size: 16px; }
    </style>
""", unsafe_allow_html=True)

# --- ХМАРНІ ФУНКЦІЇ (Міст до Google Drive) ---
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
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame(columns=['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Відділення', 'Товари', 'Сума', 'Готовність', 'Коментар'])

def save_data(df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=True)
        service.files().update(fileId=ORDERS_CSV_ID, media_body=media_body).execute()
        st.toast("Синхронізовано з хмарою ✅")
    except Exception as e:
        st.error(f"Помилка синхронізації: {e}")

def find_pdf_link(article):
    service = get_drive_service()
    if not service: return None
    try:
        query = f"name = '{article}.pdf' and '{FOLDER_DRAWINGS_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, webViewLink)").execute()
        files = results.get('files', [])
        return files[0]['webViewLink'] if files else None
    except: return None

# --- ГОЛОВНИЙ ЕКРАН (ТОЧНА КОПІЯ 3.0) ---
st.title("🏭 GETMANN Pro | Журнал замовлень")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

tabs = st.tabs(["📑 Журнал замовлень", "➕ Створити замовлення", "📊 Склад"])

with tabs[0]:
    df = st.session_state.df
    search = st.text_input("🔍 Пошук замовлення...", placeholder="Клієнт, ID або Артикул")
    
    # Фільтрація
    display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df

    for idx, row in display_df.iterrows():
        status = row.get('Готовність', 'В черзі')
        css_class = "status-queue"
        if status == "В роботі": css_class = "status-work"
        elif status == "Готово": css_class = "status-done"
        
        # Рендеринг картки
        st.markdown(f"""
            <div class="order-card {css_class}">
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-size: 20px;"><b>⌛ №{row.get('ID')}</b> | {row.get('Дата')} | 👤 <b>{row.get('Клієнт')}</b></span>
                    <span style="color: #888;">{row.get('Місто', '')}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Функціональні кнопки та чекбокси як у 3.0
        c1, c2, c3 = st.columns([1, 1, 2])
        
        # Логіка чекбоксів
        is_work = c1.checkbox("🏗️ У виробництво", value=(status == "В роботі"), key=f"w_{idx}")
        is_done = c2.checkbox("✅ Виконано", value=(status == "Готово"), key=f"d_{idx}")
        
        # Автоматичне оновлення статусу при натисканні
        new_status = status
        if is_done: new_status = "Готово"
        elif is_work: new_status = "В роботі"
        else: new_status = "В черзі"
        
        if new_status != status:
            df.at[idx, 'Готовність'] = new_status
            save_data(df)
            st.rerun()

        # Вивід товарів (Список як у 3.0)
        st.markdown("**📦 Товари та деталі:**")
        items = str(row.get('Товари', '')).split(';')
        for item in items:
            if item.strip():
                col_item, col_link = st.columns([3, 1])
                col_item.write(f"• {item.strip()}")
                if "[" in item:
                    sku = item.split("[")[1].split("]")[0]
                    link = find_pdf_link(sku)
                    if link:
                        col_link.link_button("📄 Креслення", link)

        # РЕДАКТОР (Як у 3.0)
        with st.expander("🛠️ Редагувати замовлення"):
            col1, col2 = st.columns(2)
            u_id = col1.text_input("ID", value=str(row.get('ID')), key=f"edit_id_{idx}")
            u_cl = col2.text_input("Клієнт", value=str(row.get('Клієнт')), key=f"edit_cl_{idx}")
            u_ph = col1.text_input("Телефон", value=str(row.get('Телефон')), key=f"edit_ph_{idx}")
            u_ct = col2.text_input("Місто/Відділення", value=f"{row.get('Місто')} / {row.get('Відділення')}", key=f"edit_ct_{idx}")
            u_it = st.text_area("Товари (через ;)", value=str(row.get('Товари')), key=f"edit_it_{idx}")
            u_co = st.text_input("Коментар", value=str(row.get('Коментар')), key=f"edit_co_{idx}")
            
            if st.button("💾 Зберегти зміни", key=f"save_btn_{idx}"):
                df.at[idx, 'ID'], df.at[idx, 'Клієнт'] = u_id, u_cl
                df.at[idx, 'Телефон'], df.at[idx, 'Товари'] = u_ph, u_it
                df.at[idx, 'Коментар'] = u_co
                if "/" in u_ct:
                    df.at[idx, 'Місто'], df.at[idx, 'Відділення'] = u_ct.split("/")[0].strip(), u_ct.split("/")[1].strip()
                save_data(df)
                st.rerun()
        st.markdown("---")

with tabs[1]:
    st.subheader("📝 Створення нового замовлення")
    with st.form("new_order_form"):
        f1, f2 = st.columns(2)
        new_id = f1.text_input("Номер (ID)")
        new_cl = f2.text_input("Клієнт")
        new_ph = f1.text_input("Телефон")
        new_ct = f2.text_input("Місто / Відділення")
        new_it = st.text_area("Товари (Артикули в [])")
        new_co = st.text_input("Коментар")
        
        if st.form_submit_button("Додати в базу"):
            city = new_ct.split("/")[0].strip() if "/" in new_ct else new_ct
            post = new_ct.split("/")[1].strip() if "/" in new_ct else ""
            
            new_row = {
                'ID': new_id, 'Дата': datetime.now().strftime("%d.%m.%Y"),
                'Клієнт': new_cl, 'Телефон': new_phone, 'Місто': city, 'Відділення': post,
                'Товари': new_it, 'Коментар': new_co, 'Готовність': 'В черзі'
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df)
            st.rerun()

st.sidebar.markdown("### ⚙️ Керування")
if st.sidebar.button("🔄 Оновити дані з хмари"):
    st.session_state.pop('df')
    st.rerun()
