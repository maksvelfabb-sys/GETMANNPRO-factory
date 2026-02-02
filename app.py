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

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")

# --- СЕРВІСНІ ФУНКЦІЇ ---
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
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=False)
        service.files().update(fileId=file_id, media_body=media_body).execute()
        st.toast("Дані синхронізовано ✅")
    except Exception as e:
        st.error(f"Помилка Drive: {e}")

def get_drawing_link(art):
    """Пошук PDF креслення за артикулом"""
    if not art or len(str(art)) < 2: return None
    service = get_drive_service()
    try:
        query = f"'{FOLDER_DRAWINGS_ID}' in parents and name contains '{art}' and mimeType = 'application/pdf'"
        res = service.files().list(q=query, fields="files(id, webViewLink)").execute()
        files = res.get('files', [])
        return files[0] if files else None
    except: return None

# --- АВТОРИЗАЦІЯ ---
if 'users_df' not in st.session_state:
    st.session_state.users_df = load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name'])

u_df = st.session_state.users_df

# Перевірка профілю Максима
if u_df[u_df['email'] == 'maksvel.fabb@gmail.com'].empty:
    if st.button("🔥 АКТИВУВАТИ МАКСИМА (Супер Адмін)"):
        new_boss = pd.DataFrame([{'email': 'maksvel.fabb@gmail.com', 'password': '1234', 'role': 'Супер Адмін', 'name': 'Максим'}])
        st.session_state.users_df = pd.concat([u_df, new_boss], ignore_index=True)
        save_csv(USERS_CSV_ID, st.session_state.users_df)
        st.rerun()

if 'auth' not in st.session_state:
    st.title("🏭 GETMANN Login")
    with st.form("login"):
        e = st.text_input("Логін")
        p = st.text_input("Пароль", type="password")
        if st.form_submit_button("Увійти"):
            user = st.session_state.users_df[(st.session_state.users_df['email'] == e) & (st.session_state.users_df['password'] == str(p))]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("❌ Помилка")
    st.stop()

me = st.session_state.auth
role = me['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

# --- ДАНІ ---
if 'df' not in st.session_state:
    st.session_state.df = load_csv(ORDERS_CSV_ID, ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])
df = st.session_state.df

tabs = st.tabs(["📋 Журнал", "📝 Редактор", "⚙️ Адмін"])

# --- ТАБ 1: ЖУРНАЛ ---
with tabs[0]:
    if can_edit:
        with st.expander("➕ СТВОРИТИ ЗАМОВЛЕННЯ"):
            with st.form("new_order", clear_on_submit=True):
                c1, c2 = st.columns(2)
                f_id = c1.text_input("Номер (ID)*")
                f_cl = c2.text_input("Клієнт*")
                f_ph = c1.text_input("Телефон")
                f_ct = c2.text_input("Місто/Відділення")
                tc1, tc2, tc3 = st.columns([3, 1, 1])
                t_n = tc1.text_input("Назва товару")
                t_a = tc2.text_input("Артикул")
                t_q = tc3.number_input("К-ть", min_value=1, value=1)
                f_cm = st.text_area("Коментар")
                f_av = st.number_input("Аванс", min_value=0.0)
                if st.form_submit_button("✅ Зберегти"):
                    if f_id and f_cl:
                        items = [{"назва": t_n, "арт": t_a, "к-ть": t_q}]
                        new_row = {'ID': str(f_id), 'Дата': datetime.now().strftime("%d.%m.%Y"), 'Клієнт': f_cl, 'Телефон': f_ph, 'Місто': f_ct, 'Аванс': f_av, 'Готовність': 'В черзі', 'Товари_JSON': json.dumps(items, ensure_ascii=False), 'Коментар': f_cm}
                        st.session_state.df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        save_csv(ORDERS_CSV_ID, st.session_state.df)
                        st.rerun()

    st.divider()
    search = st.text_input("🔍 Пошук...")
    
    # ПРАВИЛЬНЕ ВІДОБРАЖЕННЯ ВСІХ РЯДКІВ (НОВІ ЗВЕРХУ)
    df_display = df.copy()
    df_display = df_display.iloc[::-1] # Реверс списку
    
    if search:
        df_display = df_display[df_display.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]
    
    status_options = ["В черзі", "В роботі", "Готово"]
    
    for idx, row in df_display.iterrows():
        with st.container(border=True):
            c_h, c_s = st.columns([4, 1])
            c_h.markdown(f"### №{row['ID']} | {row['Клієнт']}")
            
            curr_stat = row.get('Готовність', 'В черзі')
            if curr_stat not in status_options: curr_stat = "В черзі"
            
            new_stat = c_s.selectbox("Статус", status_options, index=status_options.index(curr_stat), key=f"st_{idx}")
            if new_stat != curr_stat:
                df.at[idx, 'Готовність'] = new_stat
                save_csv(ORDERS_CSV_ID, df)
                st.rerun()

            st.write(f"📅 {row['Дата']} | 📍 {row['Місто']} | 📞 {row['Телефон']}")
            
            # Товари та креслення
            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            for it in items:
                col_i, col_d = st.columns([3, 1])
                col_i.write(f"📦 **{it.get('назва')}** (Арт: {it.get('арт')}) — {it.get('к-ть')} шт.")
                draw = get_drawing_link(it.get('арт'))
                if draw: col_d.link_button("📄 Креслення", draw['webViewLink'])
            
            if row['Коментар']: st.info(f"💬 {row['Коментар']}")
            if role != "Токар": st.write(f"💰 Аванс: {row['Аванс']} грн")

# --- ТАБ 2: РЕДАКТОР ---
with tabs[1]:
    if can_edit:
        s_id = st.selectbox("Оберіть замовлення", df['ID'].astype(str).tolist())
        if s_id:
            idx = df[df['ID'].astype(str) == s_id].index[0]
            try: items_l = json.loads(df.at[idx, 'Товари_JSON'])
            except: items_l = []
            st.write(f"Редагування №{s_id}")
            new_items = st.data_editor(pd.DataFrame(items_l), num_rows="dynamic")
            new_c = st.text_area("Коментар", value=df.at[idx, 'Коментар'], key=f"comm_{idx}")
            if st.button("💾 Зберегти зміни"):
                df.at[idx, 'Товари_JSON'] = new_items.to_json(orient='records', force_ascii=False)
                df.at[idx, 'Коментар'] = new_c
                save_csv(ORDERS_CSV_ID, df)
                st.success("Оновлено!")
    else: st.warning("Доступ обмежено")

# --- ТАБ 3: АДМІН ---
with tabs[2]:
    if role in ["Супер Адмін", "Адмін"]:
        ed_u = st.data_editor(st.session_state.users_df, num_rows="dynamic")
        if st.button("💾 Зберегти користувачів"):
            save_csv(USERS_CSV_ID, ed_u)
    else: st.warning("Доступ обмежено")

if st.sidebar.button("🚪 Вийти"):
    del st.session_state.auth
    st.rerun()
