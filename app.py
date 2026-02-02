import streamlit as st
import pandas as pd
import io, json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"
ADMIN_PASSWORD = "admin"  # Змініть на свій

st.set_page_config(page_title="GETMANN Pro", layout="wide", page_icon="🏭")

# --- СТИЛІЗАЦІЯ ---
st.markdown("""
    <style>
    .order-header { padding: 12px; border-radius: 8px; color: white; font-weight: bold; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .header-work { background-color: #007bff; }
    .header-done { background-color: #28a745; }
    .header-queue { background-color: #444; }
    div[data-testid="stExpander"] { border: 1px solid #444; border-radius: 8px; background: #1e1e1e; }
    .admin-stat { padding: 20px; border-radius: 10px; background: #262730; border: 1px solid #333; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- СЕРВІСНІ ФУНКЦІЇ ---
def safe_float(value):
    try:
        if isinstance(value, str): value = value.replace(',', '.').strip()
        return float(value) if value else 0.0
    except: return 0.0

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
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh).fillna("")
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame(columns=['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])

def save_data(df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=True)
        service.files().update(fileId=ORDERS_CSV_ID, media_body=media_body).execute()
        st.toast("Збережено в Google Drive ✅")
    except Exception as e:
        st.error(f"Помилка збереження: {e}")

# --- ГОЛОВНИЙ ІНТЕРФЕЙС ---
if 'df' not in st.session_state:
    st.session_state.df = load_data()

tabs = st.tabs(["📋 Журнал", "➕ Нове замовлення", "⚙️ Адмін-панель"])

# --- ВКЛАДКА ЖУРНАЛУ (Аналогічно Build 4.17) ---
with tabs[0]:
    df = st.session_state.df
    search = st.text_input("🔍 Пошук замовлень...")
    # ... логіка відображення карток замовлень ...
    # (Використовуйте попередній код для рендерингу карток тут)

# --- ВКЛАДКА НОВОГО ЗАМОВЛЕННЯ ---
with tabs[1]:
    with st.form("new_order"):
        # ... поля створення нового замовлення ...
        if st.form_submit_button("Створити"):
            # ... додавання в df ...
            save_data(st.session_state.df); st.rerun()

# --- НОВА АДМІН-ПАНЕЛЬ ---
with tabs[2]:
    st.header("⚙️ Керування системою")
    
    pwd = st.text_input("Введіть пароль адміністратора", type="password")
    
    if pwd == ADMIN_PASSWORD:
        st.success("Доступ дозволено")
        
        # Блок статистики
        st.subheader("📊 Аналітика")
        col1, col2, col3 = st.columns(3)
        
        total_debt = 0.0
        active_orders = len(st.session_state.df[st.session_state.df['Готовність'] != 'Готово'])
        
        # Розрахунок загальної суми боргів
        for _, r in st.session_state.df.iterrows():
            try:
                items = json.loads(r['Товари_JSON'])
                order_sum = sum(safe_float(i.get('к-ть')) * safe_float(i.get('ціна')) for i in items)
                total_debt += (order_sum - safe_float(r.get('Аванс')))
            except: continue
            
        col1.markdown(f'<div class="admin-stat">🏁 В роботі<br><h3>{active_orders}</h3></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="admin-stat">💰 Очікується оплат<br><h3>{total_debt} грн</h3></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="admin-stat">📅 Сьогодні<br><h3>{datetime.now().strftime("%d.%m")}</h3></div>', unsafe_allow_html=True)
        
        st.divider()
        
        # Керування базою
        st.subheader("🗄️ Пряме редагування бази")
        edited_df = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Глобально зберегти зміни бази", type="primary"):
            st.session_state.df = edited_df
            save_data(edited_df)
            st.rerun()
            
        st.divider()
        
        # Небезпечна зона
        st.subheader("⚠️ Небезпечна зона")
        if st.button("🗑️ Видалити всі виконані замовлення"):
            new_df = st.session_state.df[st.session_state.df['Готовність'] != 'Готово']
            st.session_state.df = new_df
            save_data(new_df)
            st.rerun()
            
    elif pwd != "":
        st.error("Невірний пароль")

st.sidebar.button("🔄 Оновити дані", on_click=lambda: st.session_state.pop('df'))
