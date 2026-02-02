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
        df = pd.read_csv(fh, dtype=str).fillna("")
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
    except: st.error("Помилка синхронізації з Drive")

def get_pdf_link(art):
    """Шукає PDF за артикулом (напр. 20WS.8247)"""
    if not art or str(art).strip() in ["", "nan", "None"]: return None
    service = get_drive_service()
    try:
        q = f"'{FOLDER_DRAWINGS_ID}' in parents and name contains '{str(art).strip()}' and trashed = false"
        res = service.files().list(q=q, fields="files(webViewLink)").execute()
        files = res.get('files', [])
        return files[0]['webViewLink'] if files else None
    except: return None

# --- АВТОРИЗАЦІЯ ---
if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP")
    with st.container(border=True):
        e_in = st.text_input("Логін").strip().lower()
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
df = load_csv(ORDERS_CSV_ID, COLS)

with st.sidebar:
    st.title("🏢 МЕНЮ")
    nav = ["📋 Замовлення", "📐 Креслення", "⚙️ Налаштування"]
    if role == "Супер Адмін": nav.append("👥 Користувачі")
    menu = st.radio("Навігація:", nav)
    if st.button("🚪 Вийти"):
        del st.session_state.auth
        st.rerun()

# --- СТОРІНКА: ЗАМОВЛЕННЯ ---
if menu == "📋 Замовлення":
    st.header("Журнал замовлень")
    
    # 1. Форма створення (Кошик)
    if role in ["Супер Адмін", "Адмін", "Менеджер"]:
        with st.expander("➕ НОВЕ ЗАМОВЛЕННЯ"):
            if 'cart' not in st.session_state: st.session_state.cart = []
            
            c1, c2, c3 = st.columns([1, 2, 2])
            num_ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
            next_id = int(num_ids.max() + 1) if not num_ids.empty else 1001
            f_id = c1.text_input("ID", value=str(next_id))
            f_cl = c2.text_input("Клієнт")
            f_ph = c3.text_input("Телефон")
            
            st.write("📦 **Товари в замовленні:**")
            tc1, tc2, tc3, tc4 = st.columns([3, 1, 1, 1])
            t_n = tc1.text_input("Назва", key="at_n")
            t_a = tc2.text_input("Арт", key="at_a")
            t_q = tc3.number_input("К-ть", 1, key="at_q")
            t_p = tc4.number_input("Ціна", 0.0, key="at_p")
            
            if st.button("➕ Додати товар"):
                if t_n:
                    st.session_state.cart.append({"назва": t_n, "арт": t_a, "к-ть": int(t_q), "ціна": float(t_p)})
                    st.rerun()
            
            if st.session_state.cart:
                st.table(pd.DataFrame(st.session_state.cart))
                if st.button("🚀 ЗБЕРЕГТИ В БАЗУ"):
                    new_row = {
                        'ID': str(f_id), 'Дата': datetime.now().strftime("%d.%m.%Y"),
                        'Клієнт': f_cl, 'Телефон': f_ph, 'Місто': '', 'ТТН': '',
                        'Товари_JSON': json.dumps(st.session_state.cart, ensure_ascii=False),
                        'Аванс': '0', 'Готовність': 'В черзі', 'Коментар': ''
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, df)
                    st.session_state.cart = []
                    st.rerun()

    # 2. Список та Пошук
    search = st.text_input("🔍 Пошук (Клієнт, ID, Арт)...").lower()
    df_v = df.copy().iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        with st.container(border=True):
            col_h, col_s = st.columns([3, 1])
            col_h.subheader(f"№{row['ID']} — {row['Клієнт']}")
            
            # Редагування статусу
            st_opts = ["В черзі", "В роботі", "Готовий", "Відправлений"]
            new_st = col_s.selectbox("Статус", st_opts, index=st_opts.index(row['Готовність']) if row['Готовність'] in st_opts else 0, key=f"st_{row['ID']}")
            if new_st != row['Готовність']:
                df.loc[df['ID'] == row['ID'], 'Ready'] = new_st # Фікс колонки якщо назва відрізняється
                df.loc[df['ID'] == row['ID'], 'Готовність'] = new_st
                save_csv(ORDERS_CSV_ID, df); st.rerun()

            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            
            for i, it in enumerate(items):
                c_txt, c_btn = st.columns([3, 1])
                art = str(it.get('арт', '')).strip()
                c_txt.write(f"🔹 {it.get('назва')} (**{art}**) — {it.get('к-ть')} шт.")
                
                # КНОПКА КРЕСЛЕННЯ (HTML FIX)
                if art:
                    link = get_pdf_link(art)
                    if link:
                        btn_html = f'<a href="{link}" target="_blank" style="text-decoration:none;"><div style="background-color:#ff4b4b;color:white;padding:5px;border-radius:5px;text-align:center;font-weight:bold;font-size:14px;">📕 PDF</div></a>'
                        c_btn.markdown(btn_html, unsafe_allow_html=True)
                    else:
                        c_btn.button("⌛ Немає PDF", disabled=True, key=f"no_{idx}_{i}", use_container_width=True)

            st.caption(f"📅 {row['Дата']} | 📞 {row['Телефон']} | 🚚 ТТН: {row['ТТН']}")

# --- СТОРІНКА: КОРИСТУВАЧІ ---
elif menu == "👥 Користувачі" and role == "Супер Адмін":
    st.header("Керування доступом")
    u_df = load_csv(USERS_CSV_ID, USER_COLS)
    st.dataframe(u_df, use_container_width=True)
    
    with st.expander("➕ ДОДАТИ КОРИСТУВАЧА"):
        nu = st.text_input("Email")
        np = st.text_input("Пароль")
        nr = st.selectbox("Роль", ["Адмін", "Менеджер", "Майстер"])
        if st.button("Зберегти користувача"):
            new_u = pd.DataFrame([{'email': nu, 'password': np, 'role': nr}])
            u_df = pd.concat([u_df, new_u], ignore_index=True)
            save_csv(USERS_CSV_ID, u_df)
            st.rerun()

elif menu == "⚙️ Налаштування":
    st.header("Налаштування")
    st.write(f"Ви увійшли як: **{st.session_state.auth['email']}**")
    st.write(f"Ваша роль: **{role}**")
