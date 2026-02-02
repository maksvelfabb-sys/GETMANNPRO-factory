import streamlit as st
import pandas as pd
import io, json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
USERS_CSV_ID = "1qwPXMqIwDATgIsYHo7us6yQgE-JyhT7f" 
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"
COLS = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']
USER_COLS = ['email', 'password', 'role']

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")

# --- СЕРВІСИ DRIVE ---
@st.cache_resource
def get_drive_service():
    if "gcp_service_account" in st.secrets:
        try:
            info = dict(st.secrets["gcp_service_account"])
            info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
            creds = service_account.Credentials.from_service_account_info(info)
            return build('drive', 'v3', credentials=creds)
        except: return None
    return None

def load_csv(file_id, cols):
    service = get_drive_service()
    if not service: return pd.DataFrame(columns=cols)
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh, sep=None, engine='python', dtype=str).fillna("")
        # Вирівнювання стовпців під стандарт COLS
        df.columns = [c.strip() for c in df.columns]
        current_cols = {c.lower(): c for c in df.columns}
        for c in cols:
            if c.lower() not in current_cols: df[c] = ""
            else: df = df.rename(columns={current_cols[c.lower()]: c})
        return df[cols]
    except: return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=False)
        service.files().update(fileId=file_id, media_body=media_body).execute()
        st.cache_data.clear()
        st.toast("Дані синхронізовано ✅")
    except: st.error("Помилка Drive")

def get_drawing_link(art):
    if not art: return None
    service = get_drive_service()
    try:
        query = f"'{FOLDER_DRAWINGS_ID}' in parents and name contains '{art}' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
        files = results.get('files', [])
        return files[0]['webViewLink'] if files else None
    except: return None

# --- ДОПОМІЖНІ ФУНКЦІЇ ---
def safe_float(v):
    try: return float(str(v).replace(',', '.'))
    except: return 0.0

def get_status_style(status):
    styles = {
        "В роботі": "background-color: #FFF9C4; border-left: 5px solid #FBC02D; color: #000;",
        "Готовий": "background-color: #E1F5FE; border-left: 5px solid #0288D1; color: #000;",
        "Відправлений": "background-color: #C8E6C9; border-left: 5px solid #388E3C; color: #000;"
    }
    return styles.get(status, "background-color: #F5F5F5; border-left: 5px solid #9E9E9E; color: #000;")

# --- АВТОРИЗАЦІЯ ---
if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP")
    with st.container(border=True):
        e_in = st.text_input("Логін (Email)").strip().lower()
        p_in = st.text_input("Пароль", type="password").strip()
        if st.button("Увійти", use_container_width=True):
            if e_in == "maksvel.fabb@gmail.com" and p_in == "1234":
                st.session_state.auth = {'email': e_in, 'role': 'Супер Адмін'}
                st.rerun()
            u_df = load_csv(USERS_CSV_ID, USER_COLS)
            user = u_df[(u_df['email'].str.lower() == e_in) & (u_df['password'] == p_in)]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Доступ обмежено")
    st.stop()

# --- МЕНЮ ---
role = st.session_state.auth.get('role', 'Гість')
with st.sidebar:
    st.title("🏢 МЕНЮ")
    nav = ["📋 Замовлення", "📐 Креслення", "⚙️ Налаштування"]
    if role == "Супер Адмін": nav.append("👥 Користувачі")
    menu = st.radio("Навігація:", nav)
    st.divider()
    st.write(f"👤 {st.session_state.auth['email']}")
    if st.button("🚪 Вийти"):
        del st.session_state.auth
        st.rerun()

# --- СТОРІНКА: ЗАМОВЛЕННЯ ---
if menu == "📋 Замовлення":
    st.header("Журнал замовлень")
    df = load_csv(ORDERS_CSV_ID, COLS)
    
    if role in ["Супер Адмін", "Адмін", "Менеджер"]:
        with st.expander("➕ СТВОРЕННЯ ЗАМОВЛЕННЯ"):
            if 'cart' not in st.session_state: st.session_state.cart = []
            
            c1, c2, c3 = st.columns([1, 2, 2])
            ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
            next_id = int(ids.max() + 1) if not ids.empty else 1001
            f_id = c1.text_input("ID", value=str(next_id))
            f_cl = c2.text_input("Клієнт*")
            f_ph = c3.text_input("Телефон")
            
            c4, c5 = st.columns(2)
            f_ct = c4.text_input("Місто")
            f_ttn = c5.text_input("ТТН")
            
            st.write("📦 **Товари:**")
            ti1, ti2, ti3, ti4 = st.columns([3, 1, 1, 1])
            t_n = ti1.text_input("Назва")
            t_a = ti2.text_input("Арт")
            t_q = ti3.number_input("К-ть", 1)
            t_p = ti4.number_input("Ціна", 0.0)
            
            if st.button("➕ Додати товар"):
                if t_n:
                    st.session_state.cart.append({"назва": t_n, "арт": t_a, "к-ть": int(t_q), "ціна": float(t_p), "сума": round(t_q * t_p, 2)})
                    st.rerun()
            
            if st.session_state.cart:
                st.table(pd.DataFrame(st.session_state.cart))
                f_av = st.number_input("Аванс", 0.0)
                f_cm = st.text_area("Коментар")
                if st.button("🚀 ЗБЕРЕГТИ ЗАМОВЛЕННЯ"):
                    new_order = {
                        'ID': str(f_id), 'Дата': datetime.now().strftime("%d.%m.%Y"),
                        'Клієнт': f_cl, 'Телефон': f_ph, 'Місто': f_ct, 'ТТН': f_ttn,
                        'Товари_JSON': json.dumps(st.session_state.cart, ensure_ascii=False),
                        'Аванс': str(f_av), 'Готовність': 'В черзі', 'Коментар': f_cm
                    }
                    df = pd.concat([df, pd.DataFrame([new_order])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, df)
                    st.session_state.cart = []
                    st.rerun()

    search = st.text_input("🔍 Пошук замовлення...")
    df_v = df.copy().iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    for _, row in df_v.iterrows():
        st.markdown(f'<div style="{get_status_style(row["Готовність"])} padding:15px; border-radius:10px; margin-bottom:5px;">'
                    f'<b>№{row["ID"]} | {row["Клієнт"]} | {row["Місто"]}</b></div>', unsafe_allow_html=True)
        with st.container(border=True):
            col_inf, col_st = st.columns([3, 1])
            with col_inf:
                try: items = json.loads(row['Товари_JSON'])
                except: items = []
                for it in items:
                    st.write(f"🔹 {it['назва']} ({it['арт']}) — {it['к-ть']} шт. | {it['сума']} грн")
                    link = get_drawing_link(it['арт'])
                    if link: st.link_button(f"📕 Креслення {it['арт']}", link)
                if row['Коментар']: st.warning(f"💬 {row['Коментар']}")
                if row['ТТН']: st.info(f"🚚 ТТН: {row['ТТН']}")
            with col_st:
                st.write(f"💰 Аванс: {row['Аванс']}")
                st.selectbox("Статус", ["В черзі", "В роботі", "Готовий", "Відправлений"], 
                             index=["В черзі", "В роботі", "Готовий", "Відправлений"].index(row['Готовність']) if row['Готовність'] in ["В черзі", "В роботі", "Готовий", "Відправлений"] else 0,
                             key=f"st_{row['ID']}")

# --- СТОРІНКИ: КОРИСТУВАЧІ ТА НАЛАШТУВАННЯ ---
elif menu == "👥 Користувачі" and role == "Супер Адмін":
    st.header("Користувачі")
    u_df = load_csv(USERS_CSV_ID, USER_COLS)
    with st.expander("Додати акаунт"):
        with st.form("u_add"):
            un, up, ur = st.text_input("Email"), st.text_input("Пароль"), st.selectbox("Роль", ["Адмін", "Менеджер", "Токар"])
            if st.form_submit_button("Створити"):
                u_df = pd.concat([u_df, pd.DataFrame([{'email': un, 'password': up, 'role': ur}])], ignore_index=True)
                save_csv(USERS_CSV_ID, u_df); st.rerun()
    st.dataframe(u_df, use_container_width=True)

elif menu == "⚙️ Налаштування":
    st.header("Налаштування")
    st.info("Ваш профіль: " + st.session_state.auth['email'])

elif menu == "📐 Креслення":
    st.info("Креслення підтягуються автоматично за артикулом.")
