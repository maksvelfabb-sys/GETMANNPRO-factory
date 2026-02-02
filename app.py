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

st.set_page_config(page_title="GETMANN Factory Control", layout="wide", page_icon="🏭")

# --- СИСТЕМА ПРАВ ТА КОРИСТУВАЧІВ ---
# Логін: Пароль : Роль
USERS = {
    "admin": {"pw": "1111", "role": "Адмін", "name": "Олександр (Адмін)"},
    "manager": {"pw": "2222", "role": "Менеджер", "name": "Дмитро (Менеджер)"},
    "tokar": {"pw": "3333", "role": "Токар", "name": "Віталій (Токар)"}
}

PERMS = {
    "Адмін": {"view_fin": True, "edit": True, "full_db": True},
    "Менеджер": {"view_fin": True, "edit": True, "full_db": False},
    "Токар": {"view_fin": False, "edit": False, "full_db": False}
}

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
    try:
        request = service.files().get_media(fileId=ORDERS_CSV_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh).fillna("")
        return df
    except:
        return pd.DataFrame(columns=['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])

def save_data(df):
    service = get_drive_service()
    csv_data = df.to_csv(index=False).encode('utf-8')
    media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=True)
    service.files().update(fileId=ORDERS_CSV_ID, media_body=media_body).execute()
    st.toast("Синхронізовано ☁️")

def safe_float(v):
    try: return float(str(v).replace(',', '.').strip()) if v else 0.0
    except: return 0.0

# --- АВТОРИЗАЦІЯ ---
if "auth" not in st.session_state:
    st.title("🏭 GETMANN Pro System")
    user_in = st.text_input("Логін")
    pass_in = st.text_input("Пароль", type="password")
    if st.button("Увійти"):
        if user_in in USERS and USERS[user_in]["pw"] == pass_in:
            st.session_state.auth = USERS[user_in]
            st.rerun()
        else: st.error("Невірний логін або пароль")
    st.stop()

u_data = st.session_state.auth
u_perm = PERMS[u_data["role"]]

# --- СТИЛІЗАЦІЯ ---
st.markdown(f"""
    <style>
    .order-header {{ padding: 12px; border-radius: 8px; color: white; font-weight: bold; margin-bottom: 5px; display: flex; justify-content: space-between; }}
    .header-work {{ background-color: #007bff; }} .header-done {{ background-color: #28a745; }} .header-queue {{ background-color: #444; }}
    </style>
""", unsafe_allow_html=True)

# --- МЕНЮ ---
st.sidebar.title(f"👤 {u_data['name']}")
if st.sidebar.button("Вийти"):
    del st.session_state.auth
    st.rerun()

tabs_names = ["📋 Журнал"]
if u_perm["edit"]: tabs_names.append("➕ Нове замовлення")
if u_perm["full_db"]: tabs_names.append("⚙️ Адмін")

tabs = st.tabs(tabs_names)

# --- ЗАВАНТАЖЕННЯ ДАНИХ ---
if 'df' not in st.session_state:
    st.session_state.df = load_data()
df = st.session_state.df

# --- ВКЛАДКА: ЖУРНАЛ ---
with tabs[0]:
    search = st.text_input("🔍 Пошук...")
    disp_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df
    
    for idx, row in disp_df.iterrows():
        status = row.get('Готовність', 'В черзі')
        h_col = "header-work" if status == "В роботі" else "header-done" if status == "Готово" else "header-queue"
        
        # Шапка картки (Токар не бачить ПІБ клієнта для безпеки, якщо хочете)
        title = f"№{row['ID']} | {row['Клієнт']}" if u_perm['view_fin'] else f"Замовлення №{row['ID']}"
        st.markdown(f'<div class="order-header {h_col}"><span>{title}</span><span>{status}</span></div>', unsafe_allow_html=True)
        
        with st.expander("Розгорнути деталі"):
            # Список товарів та креслення (Бачать ВСІ)
            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            
            total_sum = 0.0
            for i, item in enumerate(items):
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"📦 **{item.get('назва')}** [{item.get('арт')}]")
                col2.write(f"К-ть: {item.get('к-ть')}")
                
                if u_perm['view_fin']:
                    line_s = safe_float(item.get('к-ть')) * safe_float(item.get('ціна'))
                    total_sum += line_s
                    col3.write(f"{line_s} грн")

            # Кнопки дій
            st.divider()
            c_a, c_b = st.columns(2)
            
            # Токар може тільки перемикати готовність
            if u_data['role'] == "Токар":
                if status != "Готово":
                    if c_a.button("✅ Позначити як ГОТОВО", key=f"btn_d_{idx}"):
                        df.at[idx, 'Готовність'] = "Готово"
                        save_data(df); st.rerun()
            
            # Менеджер/Адмін бачать фінанси та редагування
            if u_perm['view_fin']:
                c_a.metric("Загальна сума", f"{total_sum} грн")
                avans = safe_float(row.get('Аванс'))
                c_b.metric("Залишок", f"{total_sum - avans} грн")
                
                if st.button("📝 Редагувати замовлення", key=f"ed_{idx}"):
                    st.info("Функція редагування доступна в Адмін-панелі або через форму")

# --- ВКЛАДКА: АДМІН (ТІЛЬКИ АДМІН) ---
if u_perm["full_db"]:
    with tabs[-1]:
        st.header("⚙️ Керування базою даних")
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Зберегти глобальні зміни"):
            st.session_state.df = edited_df
            save_data(edited_df)
            st.rerun()

st.sidebar.button("🔄 Оновити дані", on_click=lambda: st.session_state.pop('df'))
