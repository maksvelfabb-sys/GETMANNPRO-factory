import streamlit as st
import pandas as pd
import io
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

st.set_page_config(page_title="GETMANN Pro", layout="wide", page_icon="🏭")

# --- СТИЛІЗАЦІЯ ПІД ВЕРСІЮ 3.0 ---
st.markdown("""
    <style>
    .order-card {
        border: 1px solid #444;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: #1e1e1e;
    }
    .status-work { border-left: 5px solid #007bff; }
    .status-done { border-left: 5px solid #28a745; }
    .status-queue { border-left: 5px solid #888; }
    .stCheckbox { margin-bottom: -15px; }
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

# --- ІНТЕРФЕЙС ЖУРНАЛУ ---
st.title("📚 Журнал замовлень")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

tabs = st.tabs(["📑 Журнал", "📝 Нове замовлення", "🏗️ Склад"])

with tabs[0]:
    df = st.session_state.df
    search = st.text_input("🔍 Швидкий пошук")
    display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df

    for idx, row in display_df.iterrows():
        status = row.get('Готовність', 'В черзі')
        css_class = "status-queue"
        if status == "В роботі": css_class = "status-work"
        elif status == "Готово": css_class = "status-done"
        
        # Відображення картки як у версії 3
        st.markdown(f"""
            <div class="order-card {css_class}">
                <div style="display: flex; justify-content: space-between; color: #bbb; font-size: 0.9em;">
                    <span>⌛ №{row.get('ID')} | {row.get('Дата', '02.02.2026')} | <b>{row.get('Клієнт')}</b></span>
                    <span>Менеджер: Головний Адмін</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Чекбокси статусів (логіка перемикання)
        c1, c2, _ = st.columns([1, 1, 2])
        is_work = c1.checkbox("🏗️ У виробництво", value=(status == "В роботі"), key=f"ch_w_{idx}")
        is_done = c2.checkbox("✅ Виконано", value=(status == "Готово"), key=f"ch_d_{idx}")
        
        # Обробка зміни чекбоксів
        new_status = status
        if is_done: new_status = "Готово"
        elif is_work: new_status = "В роботі"
        else: new_status = "В черзі"
        
        if new_status != status:
            df.at[idx, 'Готовність'] = new_status
            save_data(df)
            st.rerun()

        # Список товарів списком (булітами)
        items = str(row.get('Товари', '')).split(';')
        for item in items:
            if item.strip():
                st.markdown(f"• {item.strip()}")
                if "[" in item:
                    sku = item.split("[")[1].split("]")[0]
                    link = find_pdf_link(sku)
                    if link: st.link_button(f"📄 Креслення {sku}", link, src="small")

        # Редагування деталей (Expander як на фото)
        with st.expander("📝 Редагувати деталі"):
            col_a, col_b = st.columns(2)
            u_client = col_a.text_input("Клієнт", value=str(row.get('Клієнт')), key=f"u_cl_{idx}")
            u_phone = col_b.text_input("Телефон", value=str(row.get('Телефон')), key=f"u_ph_{idx}")
            u_items = st.text_area("Товари", value=str(row.get('Товари')), key=f"u_it_{idx}")
            u_city = st.text_input("Місто/Відділення", value=f"{row.get('Місто')} / {row.get('Відділення')}", key=f"u_ct_{idx}")
            
            if st.button("💾 Зберегти зміни", key=f"u_btn_{idx}"):
                df.at[idx, 'Клієнт'] = u_client
                df.at[idx, 'Телефон'] = u_phone
                df.at[idx, 'Товари'] = u_items
                # Розділяємо місто та відділення назад
                if "/" in u_city:
                    parts = u_city.split("/")
                    df.at[idx, 'Місто'] = parts[0].strip()
                    df.at[idx, 'Відділення'] = parts[1].strip()
                save_data(df)
                st.rerun()

with tabs[1]:
    st.subheader("🆕 Нове замовлення")
    with st.form("new"):
        f1, f2 = st.columns(2)
        fid = f1.text_input("ID замовлення")
        fcl = f2.text_input("Клієнт")
        fit = st.text_area("Товари (через ;)")
        if st.form_submit_button("Додати в журнал"):
            new_r = {'ID': fid, 'Клієнт': fcl, 'Товари': fit, 'Дата': datetime.now().strftime("%d.%m.%Y"), 'Готовність': 'В черзі'}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_r])], ignore_index=True)
            save_data(st.session_state.df); st.rerun()

st.sidebar.button("🔄 Оновити", on_click=lambda: st.session_state.pop('df'))
