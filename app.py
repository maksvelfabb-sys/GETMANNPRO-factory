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

def add_log(user_name, action, order_id):
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    entry = f"[{timestamp}] {user_name}: {action} (№{order_id})"
    if 'history' not in st.session_state: st.session_state.history = []
    st.session_state.history.append(entry)

def get_drawing_link(art):
    if not art: return None
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

if 'auth' not in st.session_state:
    st.title("🏭 Вхід у GETMANN ERP")
    with st.form("login"):
        e = st.text_input("Email")
        p = st.text_input("Пароль", type="password")
        if st.form_submit_button("Увійти"):
            u = st.session_state.users_df
            user = u[(u['email'] == e) & (u['password'] == str(p))]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("❌ Невірні дані")
    st.stop()

me = st.session_state.auth
role = me['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

# --- ДАНІ ---
if 'df' not in st.session_state:
    st.session_state.df = load_csv(ORDERS_CSV_ID, ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])
df = st.session_state.df

# --- НАВІГАЦІЯ ---
st.sidebar.title(f"👤 {me['name']}")
tabs_list = ["📋 Журнал замовлень"]
if can_edit: tabs_list.append("📝 Редактор товарів")
if role in ["Супер Адмін", "Адмін"]: tabs_list.append("⚙️ Адмін")

tabs = st.tabs(tabs_list)

# --- ТАБ 1: ЖУРНАЛ (ОБ'ЄДНАНИЙ) ---
with tabs[0]:
    if can_edit:
        with st.expander("➕ СТВОРИТИ НОВЕ ЗАМОВЛЕННЯ", expanded=False):
            with st.form("new_ord_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                f_id = c1.text_input("ID замовлення*")
                f_cl = c2.text_input("Клієнт*")
                f_ph = c1.text_input("Телефон")
                f_ct = c2.text_input("Місто/Відділення")
                
                st.write("📦 **Товар та коментар:**")
                tc1, tc2, tc3 = st.columns([3, 1, 1])
                t_n = tc1.text_input("Назва товару")
                t_a = tc2.text_input("Артикул")
                t_q = tc3.number_input("К-ть", min_value=1, value=1)
                
                f_cm = st.text_area("Коментар менеджера")
                f_av = st.number_input("Аванс (грн)", min_value=0.0)
                
                if st.form_submit_button("🔥 ЗБЕРЕГТИ"):
                    if f_id and f_cl:
                        items = [{"назва": t_n, "арт": t_a, "к-ть": t_q, "ціна": 0.0}]
                        new_row = {
                            'ID': f_id, 'Дата': datetime.now().strftime("%d.%m.%Y"),
                            'Клієнт': f_cl, 'Телефон': f_ph, 'Місто': f_ct,
                            'Аванс': f_av, 'Готовність': 'В черзі',
                            'Товари_JSON': json.dumps(items, ensure_ascii=False),
                            'Коментар': f_cm
                        }
                        st.session_state.df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        save_csv(ORDERS_CSV_ID, st.session_state.df)
                        add_log(me['name'], "Створив замовлення", f_id)
                        st.rerun()
                    else: st.error("Заповніть обов'язкові поля!")

    st.divider()
    search = st.text_input("🔍 Пошук...")
    df_v = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df
    
    for idx, row in df_v.iterrows():
        with st.container(border=True):
            c_h, c_s = st.columns([4, 1])
            c_h.markdown(f"### №{row['ID']} | {row['Клієнт']}")
            status = row.get('Готовність', 'В черзі')
            new_stat = c_s.selectbox("Статус", ["В черзі", "В роботі", "Готово"], index=["В черзі", "В роботі", "Готово"].index(status), key=f"st_{idx}")
            
            if new_stat != status:
                df.at[idx, 'Готовність'] = new_stat
                save_csv(ORDERS_CSV_ID, df)
                add_log(me['name'], f"Статус -> {new_stat}", row['ID'])
                st.rerun()

            st.write(f"📍 {row['Місто']} | 📞 {row['Телефон']} | 📅 {row['Дата']}")
            items = json.loads(row['Товари_JSON']) if row['Товари_JSON'] else []
            for it in items:
                i_col, d_col = st.columns([3, 1])
                i_col.write(f"📦 **{it.get('назва')}** ({it.get('арт')}) — {it.get('к-ть')} шт.")
                draw = get_drawing_link(it.get('арт'))
                if draw: d_col.link_button("📄 Креслення", draw['webViewLink'])
            if row['Коментар']: st.info(f"💬 {row['Коментар']}")

# --- ТАБ 2: РЕДАКТОР ---
if can_edit:
    with tabs[tabs_list.index("📝 Редактор товарів")]:
        s_id = st.selectbox("Оберіть замовлення", df['ID'].tolist())
        if s_id:
            idx = df[df['ID'] == s_id].index[0]
            items_list = json.loads(df.at[idx, 'Товари_JSON'])
            st.write(f"Редагування №{s_id}")
            new_items = st.data_editor(pd.DataFrame(items_list), num_rows="dynamic")
            new_comm = st.text_area("Змінити коментар", value=df.at[idx, 'Коментар'])
            
            if st.button("💾 Зберегти зміни"):
                df.at[idx, 'Товари_JSON'] = new_items.to_json(orient='records', force_ascii=False)
                df.at[idx, 'Коментар'] = new_comm
                save_csv(ORDERS_CSV_ID, df)
                add_log(me['name'], "Відредагував товари", s_id)
                st.success("Оновлено!")

# --- ТАБ 3: АДМІН ---
if "⚙️ Адмін" in tabs_list:
    with tabs[-1]:
        st.subheader("👥 Користувачі")
        ed_u = st.data_editor(st.session_state.users_df, num_rows="dynamic")
        if st.button("💾 Зберегти доступ"):
            save_csv(USERS_CSV_ID, ed_u)
        if role == "Супер Адмін" and 'history' in st.session_state:
            st.divider()
            st.subheader("📜 Лог дій")
            for entry in reversed(st.session_state.history[-15:]): st.write(entry)

if st.sidebar.button("🚪 Вийти"):
    del st.session_state.auth
    st.rerun()
