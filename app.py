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

# --- ФУНКЦІЇ DRIVE ---
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

@st.cache_data(ttl=60)
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
        df.columns = [c.lower().strip() for c in df.columns]
        for c in cols:
            if c not in df.columns: df[c] = ""
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

# --- ДОПОМІЖНІ ФУНКЦІЇ ---
def get_drawing_link(art):
    if not art: return None
    service = get_drive_service()
    try:
        query = f"'{FOLDER_DRAWINGS_ID}' in parents and name contains '{art}' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
        files = results.get('files', [])
        return files[0]['webViewLink'] if files else None
    except: return None

def safe_float(v):
    try: return float(str(v).replace(',', '.'))
    except: return 0.0

def safe_int(v):
    try: return int(float(v))
    except: return 1

def get_card_style(status):
    styles = {
        "В роботі": "background-color: #FFF9C4; border: 1px solid #FBC02D;",
        "Готовий до відправлення": "background-color: #E1F5FE; border: 1px solid #0288D1;",
        "Відправлений": "background-color: #C8E6C9; border: 1px solid #388E3C;"
    }
    return styles.get(status, "background-color: #FAFAFA; border: 1px solid #D1D1D1;")

# --- АВТОРИЗАЦІЯ ---
if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP")
    with st.container(border=True):
        e = st.text_input("Логін (Email)").strip().lower()
        p = st.text_input("Пароль", type="password").strip()
        if st.button("Увійти", use_container_width=True):
            if e == "maksvel.fabb@gmail.com" and p == "1234":
                st.session_state.auth = {'email': e, 'role': 'Супер Адмін'}
                st.cache_data.clear()
                st.rerun()
            
            st.cache_data.clear()
            u_df = load_csv(USERS_CSV_ID, USER_COLS)
            u_df['email'] = u_df['email'].str.strip().str.lower()
            u_df['password'] = u_df['password'].astype(str).str.strip()
            user_match = u_df[(u_df['email'] == e) & (u_df['password'] == p)]
            if not user_match.empty:
                st.session_state.auth = user_match.iloc[0].to_dict()
                st.rerun()
            else: st.error("❌ Доступ обмежено")
    st.stop()

# --- SIDEBAR МЕНЮ ---
role = st.session_state.auth.get('role', 'Гість')
with st.sidebar:
    st.title("🏢 МЕНЮ")
    nav_list = ["📋 Замовлення", "⚙️ Налаштування", "📐 Каталог креслень", "🏗️ Матеріали"]
    if role == "Супер Адмін": nav_list.append("👥 Користувачі")
    menu = st.radio("Навігація:", nav_list)
    st.divider()
    st.write(f"👤 {st.session_state.auth['email']}")
    if st.button("🚪 Вихід"):
        del st.session_state.auth
        st.rerun()

# --- СТОРІНКА: ЗАМОВЛЕННЯ ---
if menu == "📋 Замовлення":
    st.header("Журнал замовлень")
    df = load_csv(ORDERS_CSV_ID, COLS)
    can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

    if can_edit:
        with st.expander("➕ НОВЕ ЗАМОВЛЕННЯ"):
            numeric_ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
            next_id = int(numeric_ids.max() + 1) if not numeric_ids.empty else 1001
            with st.form("new_order", clear_on_submit=True):
                c1, c2, c3 = st.columns([1, 2, 2])
                f_id, f_cl, f_ph = c1.text_input("№*", value=str(next_id)), c2.text_input("Клієнт*"), c3.text_input("Телефон")
                c4, c5, c6 = st.columns([2, 2, 1])
                f_ct, f_ttn, f_av = c4.text_input("Місто"), c5.text_input("ТТН"), c6.number_input("Аванс", 0.0)
                f_cm = st.text_area("Коментар")
                tc1, tc2, tc3, tc4 = st.columns([3, 1, 1, 1])
                t_n, t_a, t_q, t_p = tc1.text_input("Назва"), tc2.text_input("Арт"), tc3.number_input("К-ть", 1), tc4.number_input("Ціна", 0.0)
                if st.form_submit_button("🚀 Створити"):
                    items = [{"назва": t_n, "арт": t_a, "к-ть": int(t_q), "ціна": float(t_p), "сума": round(t_q * t_p, 2)}]
                    new_row = {'ID': str(f_id), 'Дата': datetime.now().strftime("%d.%m.%Y"), 'Клієнт': f_cl, 'Телефон': str(f_ph), 'Місто': f_ct, 'ТТН': f_ttn, 'Аванс': str(f_av), 'Готовність': 'В черзі', 'Товари_JSON': json.dumps(items, ensure_ascii=False), 'Коментар': f_cm}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

    search = st.text_input("🔍 Швидкий пошук...")
    df_v = df.copy().iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        status = row.get('Готовність', 'В черзі')
        style = get_card_style(status)
        try: items = json.loads(row['Товари_JSON'])
        except: items = []
        st.markdown(f'<div style="{style} padding: 10px 15px; border-radius: 8px; color: #000; margin-bottom: 5px;"><b>№{row["ID"]} | {row["Клієнт"]} | {row["Телефон"]}</b></div>', unsafe_allow_html=True)
        with st.container(border=True):
            c_info, c_status = st.columns([4, 1.2])
            with c_info:
                t_sum = 0
                for i, it in enumerate(items):
                    art = str(it.get('арт', '')).strip()
                    link = get_drawing_link(art)
                    col_t1, col_t2 = st.columns([4.5, 1.5])
                    with col_t1: st.markdown(f"🔹 **{it.get('назва')}** ({art}) — {it.get('к-ть')} шт")
                    with col_t2: 
                        if link: st.link_button("📕 PDF", link, use_container_width=True, key=f"lk_{idx}_{i}")
                    t_sum += safe_float(it.get('сума'))
                st.write(f"**Разом: {t_sum} грн** | Аванс: {row['Аванс']}")
            with c_status:
                opts = ["В черзі", "В роботі", "Готовий до відправлення", "Відправлений"]
                new_st = st.selectbox("Статус", opts, index=opts.index(status) if status in opts else 0, key=f"st_{idx}")
                if new_st != status:
                    df.loc[df['ID'] == row['ID'], 'Готовність'] = new_st
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

# --- СТОРІНКА: НАЛАШТУВАННЯ (ВІДНОВЛЕНО) ---
elif menu == "⚙️ Налаштування":
    st.header("Налаштування профілю")
    u_df = load_csv(USERS_CSV_ID, USER_COLS)
    my_email = st.session_state.auth['email']
    
    with st.container(border=True):
        st.write(f"**Ваш логін:** {my_email}")
        new_pass = st.text_input("Змінити пароль", type="password")
        if st.button("Оновити пароль"):
            if new_pass:
                u_df.loc[u_df['email'] == my_email, 'password'] = new_pass
                save_csv(USERS_CSV_ID, u_df)
                st.success("Пароль успішно змінено!")
            else: st.error("Введіть новий пароль")

    if role == "Супер Адмін":
        st.divider()
        st.subheader("🔴 Зона ризику")
        if st.button("❌ ОЧИСТИТИ БАЗУ ЗАМОВЛЕНЬ"):
            st.session_state.confirm_delete = True
        
        if st.session_state.get('confirm_delete'):
            st.warning("Ви впевнені, що хочете видалити ВСІ замовлення?")
            col1, col2 = st.columns(2)
            if col1.button("ТАК, ВИДАЛИТИ"):
                save_csv(ORDERS_CSV_ID, pd.DataFrame(columns=COLS))
                st.session_state.confirm_delete = False
                st.rerun()
            if col2.button("СКАСУВАТИ"):
                st.session_state.confirm_delete = False
                st.rerun()

# --- СТОРІНКА: КОРИСТУВАЧІ ---
elif menu == "👥 Користувачі" and role == "Супер Адмін":
    st.header("Керування командою")
    u_df = load_csv(USERS_CSV_ID, USER_COLS)
    with st.expander("➕ Додати користувача"):
        with st.form("add_u"):
            ne, np, nr = st.text_input("Email"), st.text_input("Пароль"), st.selectbox("Роль", ["Менеджер", "Адмін", "Токар", "Гість"])
            if st.form_submit_button("Створити"):
                new_u = pd.DataFrame([{'email': ne.strip().lower(), 'password': np.strip(), 'role': nr}])
                u_df = pd.concat([u_df, new_u], ignore_index=True)
                save_csv(USERS_CSV_ID, u_df); st.rerun()
    st.dataframe(u_df, use_container_width=True)
    del_u = st.selectbox("Видалити користувача", u_df['email'].tolist())
    if st.button("❌ Видалити"):
        if del_u != st.session_state.auth['email']:
            u_df = u_df[u_df['email'] != del_u]
            save_csv(USERS_CSV_ID, u_df); st.rerun()

elif menu == "📐 Каталог креслень": st.info("🚧 У розробці")
elif menu == "🏗️ Матеріали": st.info("🚧 У розробці")
