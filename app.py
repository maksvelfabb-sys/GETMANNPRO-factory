import streamlit as st
import pandas as pd
import io, json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
USERS_CSV_ID = "1FDWndpOgRX21lwHk19SUoBfKyMj0K1Zc"
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

st.set_page_config(page_title="GETMANN Pro", layout="wide", page_icon="🏭")

# --- СЕРВІСНІ ФУНКЦІЇ ДЛЯ РОБОТИ З DRIVE ---
@st.cache_resource
def get_drive_service():
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
        creds = service_account.Credentials.from_service_account_info(info)
        return build('drive', 'v3', credentials=creds)
    return None

def load_csv(file_id, cols):
    service = get_drive_service()
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh).fillna("")
        return df
    except:
        return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    csv_data = df.to_csv(index=False).encode('utf-8')
    media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=True)
    service.files().update(fileId=file_id, media_body=media_body).execute()

def safe_float(v):
    try: return float(str(v).replace(',', '.').strip()) if v else 0.0
    except: return 0.0

# --- АВТОРИЗАЦІЯ ТА ПЕРЕВІРКА СУПЕР АДМІНА ---
if 'users_df' not in st.session_state:
    st.session_state.users_df = load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name'])

u_df = st.session_state.users_df

# Активація профілю Максима при першому запуску
if u_df[u_df['email'] == 'maksvel.fabb@gmail.com'].empty:
    st.info("Контроль доступу: Виявлено новий запит на активацію Супер Адміна.")
    if st.button("Активувати профіль maksvel.fabb@gmail.com"):
        new_boss = pd.DataFrame([{'email': 'maksvel.fabb@gmail.com', 'password': '1234', 'role': 'Супер Адмін', 'name': 'Максим'}])
        st.session_state.users_df = pd.concat([u_df, new_boss], ignore_index=True)
        save_csv(USERS_CSV_ID, st.session_state.users_df)
        st.rerun()

if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP Login")
    with st.form("login_form"):
        email_in = st.text_input("Введіть Email")
        pass_in = st.text_input("Введіть Пароль", type="password")
        if st.form_submit_button("Увійти в систему"):
            user = st.session_state.users_df[
                (st.session_state.users_df['email'] == email_in) & 
                (st.session_state.users_df['password'] == str(pass_in))
            ]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("❌ Невірний Email або Пароль")
    st.stop()

# Поточні права
me = st.session_state.auth
role = me['role']

# --- СТИЛІЗАЦІЯ КАРТОК ---
st.markdown("""
    <style>
    .order-card { padding: 12px; border-radius: 8px; color: white; margin-bottom: 5px; font-weight: bold; display: flex; justify-content: space-between; }
    .bg-work { background-color: #007bff; } .bg-done { background-color: #28a745; } .bg-queue { background-color: #444; }
    </style>
""", unsafe_allow_html=True)

# --- МЕНЮ ТА НАВІГАЦІЯ ---
st.sidebar.title(f"👤 {me['name']}")
st.sidebar.write(f"🛡️ Доступ: **{role}**")
if st.sidebar.button("Вийти з акаунта"):
    del st.session_state.auth
    st.rerun()

tabs_list = ["📋 Журнал"]
if role in ["Супер Адмін", "Адмін", "Менеджер"]:
    tabs_list.append("➕ Нове замовлення")
if role in ["Супер Адмін", "Адмін"]:
    tabs_list.append("👥 Персонал")
    tabs_list.append("⚙️ База")

tabs = st.tabs(tabs_list)

# --- ЗАВАНТАЖЕННЯ ЗАМОВЛЕНЬ ---
if 'df' not in st.session_state:
    st.session_state.df = load_csv(ORDERS_CSV_ID, ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])
df = st.session_state.df

# --- ВКЛАДКА 1: ЖУРНАЛ ---
with tabs[0]:
    search = st.text_input("🔍 Швидкий пошук замовлень...")
    disp_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df
    
    for idx, row in disp_df.iterrows():
        status = row.get('Готовність', 'В черзі')
        bg = "bg-work" if status == "В роботі" else "bg-done" if status == "Готово" else "bg-queue"
        
        st.markdown(f'<div class="order-card {bg}"><span>№{row["ID"]} | {row["Клієнт"]}</span><span>{status}</span></div>', unsafe_allow_html=True)
        
        with st.expander("Деталі замовлення"):
            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            
            total_sum = 0.0
            for item in items:
                st.write(f"• **{item.get('назва')}** — {item.get('к-ть')} шт. (Арт: {item.get('арт')})")
                if role != "Токар":
                    total_sum += safe_float(item.get('к-ть')) * safe_float(item.get('ціна'))
            
            if role != "Токар":
                st.divider()
                f1, f2, f3 = st.columns(3)
                f1.metric("Сума замовлення", f"{total_sum} грн")
                av = safe_float(row.get('Аванс'))
                f2.metric("Внесено аванс", f"{av} грн")
                f3.metric("Залишок", f"{total_sum - av} грн", delta_color="inverse")
            
            # Зміна статусу для Токаря
            if role == "Токар" and status != "Готово":
                if st.button("✅ Позначити як виконане", key=f"d_btn_{idx}"):
                    df.at[idx, 'Готовність'] = "Готово"
                    save_csv(ORDERS_CSV_ID, df)
                    st.rerun()

# --- ВКЛАДКА 2: НОВЕ ЗАМОВЛЕННЯ ---
if "➕ Нове замовлення" in tabs_list:
    with tabs[tabs_list.index("➕ Нове замовлення")]:
        st.header("📝 Реєстрація замовлення")
        with st.form("new_order_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            n_id = col1.text_input("Номер (ID)")
            n_client = col2.text_input("ПІБ Клієнта")
            n_phone = col1.text_input("Телефон")
            n_city = col2.text_input("Місто")
            n_avans = st.number_input("Аванс", min_value=0.0)
            
            if st.form_submit_button("Створити"):
                new_row = {
                    'ID': n_id, 'Дата': datetime.now().strftime("%d.%m.%Y"),
                    'Клієнт': n_client, 'Телефон': n_phone, 'Місто': n_city,
                    'Аванс': n_avans, 'Готовність': 'В черзі',
                    'Товари_JSON': json.dumps([{"назва": "Новий товар", "арт": "", "к-ть": 1, "ціна": 0.0}])
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                save_csv(ORDERS_CSV_ID, st.session_state.df)
                st.success("Додано!")
                st.rerun()

# --- ВКЛАДКА 3: ПЕРСОНАЛ (СУПЕР АДМІН ТА АДМІН) ---
if "👥 Персонал" in tabs_list:
    with tabs[tabs_list.index("👥 Персонал")]:
        st.header("👥 Керування доступом")
        
        u_view = st.session_state.users_df.copy()
        if role == "Адмін":
            u_view = u_view[u_view['role'] != 'Супер Адмін']
            
        edited_u = st.data_editor(u_view, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Оновити користувачів"):
            if role == "Супер Адмін":
                st.session_state.users_df = edited_u
            else:
                boss = st.session_state.users_df[st.session_state.users_df['role'] == 'Супер Адмін']
                st.session_state.users_df = pd.concat([boss, edited_u], ignore_index=True).drop_duplicates()
            save_csv(USERS_CSV_ID, st.session_state.users_df)
            st.success("Користувачів оновлено!")

# --- ВКЛАДКА 4: БАЗА ---
if "⚙️ База" in tabs_list:
    with tabs[tabs_list.index("⚙️ База")]:
        st.header("🗄️ Редактор бази замовлень")
        edited_df = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Зберегти зміни в базі"):
            st.session_state.df = edited_df
            save_csv(ORDERS_CSV_ID, edited_df)
            st.rerun()

st.sidebar.divider()
st.sidebar.button("🔄 Оновити дані з хмари", on_click=lambda: st.session_state.pop('df'))
