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

# --- СЕРВІСНІ ФУНКЦІЇ ---
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
        df.columns = [c.lower().strip() for c in df.columns]
        for c in cols:
            if c not in df.columns: df[c] = ""
        return df[[c.lower() for c in cols]]
    except: return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=False)
        service.files().update(fileId=file_id, media_body=media_body).execute()
        st.cache_data.clear()
        st.toast("Синхронізовано ✅")
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

# --- АВТОРИЗАЦІЯ ---
if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP")
    with st.container(border=True):
        e = st.text_input("Email").strip().lower()
        p = st.text_input("Пароль", type="password").strip()
        if st.button("Увійти", use_container_width=True):
            if e == "maksvel.fabb@gmail.com" and p == "1234":
                st.session_state.auth = {'email': e, 'role': 'Супер Адмін'}
                st.rerun()
            u_df = load_csv(USERS_CSV_ID, USER_COLS)
            user = u_df[(u_df['email'] == e) & (u_df['password'] == p)]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Доступ закритий")
    st.stop()

# --- МЕНЮ ---
role = st.session_state.auth['role']
with st.sidebar:
    st.title("🏢 GETMANN")
    menu = st.radio("Навігація:", ["📋 Замовлення", "⚙️ Налаштування", "👥 Користувачі"] if role == "Супер Адмін" else ["📋 Замовлення", "⚙️ Налаштування"])
    if st.button("🚪 Вийти"):
        del st.session_state.auth
        st.rerun()

# --- ЗАМОВЛЕННЯ ---
if menu == "📋 Замовлення":
    st.header("Журнал замовлень")
    df = load_csv(ORDERS_CSV_ID, COLS)
    
    # Створення нового замовлення
    if role in ["Супер Адмін", "Адмін", "Менеджер"]:
        with st.expander("➕ НОВЕ ЗАМОВЛЕННЯ", expanded=False):
            if 'temp_items' not in st.session_state: st.session_state.temp_items = []
            
            # Поля клієнта
            c1, c2, c3 = st.columns([1, 2, 2])
            f_cl = c2.text_input("Клієнт*")
            f_ph = c3.text_input("Телефон")
            
            st.divider()
            st.write("📦 **Додати товари до списку:**")
            
            # Поля товару
            ti1, ti2, ti3, ti4 = st.columns([3, 1, 1, 1])
            t_name = ti1.text_input("Назва товару")
            t_art = ti2.text_input("Артикул")
            t_qty = ti3.number_input("К-ть", min_value=1, value=1)
            t_price = ti4.number_input("Ціна за шт.", min_value=0.0, value=0.0)
            
            if st.button("➕ Додати товар у список"):
                if t_name:
                    item_sum = round(t_qty * t_price, 2)
                    st.session_state.temp_items.append({
                        "назва": t_name, "арт": t_art, "к-ть": int(t_qty), "ціна": float(t_price), "сума": item_sum
                    })
                    st.rerun()
                else: st.warning("Введіть назву товару")

            # Відображення списку доданих товарів
            if st.session_state.temp_items:
                st.table(pd.DataFrame(st.session_state.temp_items))
                total_order_sum = sum(i['сума'] for i in st.session_state.temp_items)
                st.write(f"**Загальна сума замовлення: {total_order_sum} грн**")
                
                f_av = st.number_input("Аванс", value=0.0)
                f_cm = st.text_area("Коментар")
                
                if st.button("🚀 ЗБЕРЕГТИ ЗАМОВЛЕННЯ В БАЗУ"):
                    if f_cl:
                        numeric_ids = pd.to_numeric(df['id'], errors='coerce').dropna()
                        next_id = int(numeric_ids.max() + 1) if not numeric_ids.empty else 1001
                        
                        new_row = {
                            'id': str(next_id),
                            'дата': datetime.now().strftime("%d.%m.%Y"),
                            'клієнт': f_cl, 'телефон': f_ph,
                            'товари_json': json.dumps(st.session_state.temp_items, ensure_ascii=False),
                            'аванс': str(f_av), 'готовність': 'В черзі', 'коментар': f_cm
                        }
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        save_csv(ORDERS_CSV_ID, df)
                        st.session_state.temp_items = []
                        st.rerun()
                    else: st.error("Вкажіть ім'я клієнта")
                
                if st.button("🗑️ Очистити список"):
                    st.session_state.temp_items = []
                    st.rerun()

    # Відображення існуючих замовлень
    search = st.text_input("🔍 Пошук замовлення...")
    df_v = df.copy().iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        with st.container(border=True):
            st.subheader(f"№{row['id']} | {row['клієнт']}")
            try: items = json.loads(row['товари_json'])
            except: items = []
            
            for it in items:
                c_t1, c_t2 = st.columns([4, 1])
                c_t1.write(f"🔹 **{it['назва']}** ({it['арт']}) — {it['к-ть']} шт. × {it['ціна']} = {it['сума']} грн")
                link = get_drawing_link(it['арт'])
                if link: c_t2.link_button("📄 Креслення", link, use_container_width=True)
            
            st.caption(f"💬 {row['коментар']} | 💰 Аванс: {row['аванс']} грн")
            
# --- НАЛАШТУВАННЯ ---
elif menu == "⚙️ Налаштування":
    st.header("Налаштування")
    u_df = load_csv(USERS_CSV_ID, USER_COLS)
    with st.container(border=True):
        new_p = st.text_input("Новий пароль", type="password")
        if st.button("Змінити пароль"):
            u_df.loc[u_df['email'] == st.session_state.auth['email'], 'password'] = new_p
            save_csv(USERS_CSV_ID, u_df)
            st.success("Пароль змінено!")

# --- КОРИСТУВАЧІ ---
elif menu == "👥 Користувачі":
    st.header("Команда")
    u_df = load_csv(USERS_CSV_ID, USER_COLS)
    st.dataframe(u_df, use_container_width=True)
    # Форма додавання користувача (аналогічно Build 4.89)
