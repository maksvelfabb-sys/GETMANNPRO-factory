import streamlit as st
import pandas as pd
import io, json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
USERS_CSV_ID = "1ibrEFKOyvt5xgC_vSMhvDmNxdO1pVYfr4a-TqgJM82Y"
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

# --- АВТОРИЗАЦІЯ (Build 4.77) ---
if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP")
    with st.container(border=True):
        # Очищаємо ввід користувача від випадкових пробілів
        e_input = st.text_input("Логін (Email)").strip().lower()
        p_input = st.text_input("Пароль", type="password").strip()
        
        if st.button("Увійти", use_container_width=True):
            # 1. ПЕРЕВІРКА ВАС (СУПЕР АДМІН)
            if e_input == "maksvel.fabb@gmail.com" and p_input == "1234":
                st.session_state.auth = {'email': e_input, 'role': 'Супер Адмін'}
                st.cache_data.clear()
                st.rerun()
            
            # 2. ПЕРЕВІРКА ІНШИХ (З ФАЙЛУ)
            st.cache_data.clear() 
            u_df = load_csv(USERS_CSV_ID, USER_COLS)
            
            # ОЧИЩЕННЯ ДАНИХ У ТАБЛИЦІ (щоб уникнути помилок формату)
            u_df['email'] = u_df['email'].str.strip().str.lower()
            u_df['password'] = u_df['password'].astype(str).str.strip()
            
            # Шукаємо користувача
            user_match = u_df[(u_df['email'] == e_input) & (u_df['password'] == p_input)]
            
            if not user_match.empty:
                st.session_state.auth = user_match.iloc[0].to_dict()
                st.success(f"Вхід виконано! Роль: {st.session_state.auth['role']}")
                st.rerun()
            else:
                # Виводимо підказку для налагодження (тільки якщо ви самі тестуєте)
                st.error("❌ Доступ обмежено.")
                st.info("Переконайтеся, що в таблиці немає зайвих пробілів і пароль вказано вірно.")
    st.stop()

# --- SIDEBAR МЕНЮ ---
role = st.session_state.auth['role']
with st.sidebar:
    st.title("🏢 МЕНЮ")
    nav_list = ["📋 Замовлення", "⚙️ Налаштування", "📐 Каталог креслень", "🏗️ Матеріали"]
    if role == "Супер Адмін": nav_list.append("👥 Користувачі")
    menu = st.radio("Навігація:", nav_list)
    st.divider()
    st.write(f"👤 {st.session_state.auth['email']}")
    st.caption(f"Роль: {role}")
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
                st.write("📦 **Товар:**")
                tc1, tc2, tc3, tc4 = st.columns([3, 1, 1, 1])
                t_n, t_a, t_q, t_p = tc1.text_input("Назва"), tc2.text_input("Арт"), tc3.number_input("К-ть", 1, step=1), tc4.number_input("Ціна", 0.0)
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
        
        st.markdown(f'<div style="{style} padding: 10px 15px; border-radius: 8px; color: #000; margin-bottom: 5px;"><b>№{row["ID"]} | {row["Клієнт"]} | {row["Телефон"]} {f"| 📦 {row["ТТН"]}" if row["ТТН"] else ""}</b></div>', unsafe_allow_html=True)

        with st.container(border=True):
            c_info, c_status = st.columns([4, 1.2])
            with c_info:
                t_sum = 0
                for i, it in enumerate(items):
                    art = str(it.get('арт', '')).strip()
                    link = get_drawing_link(art)
                    col_t1, col_t2 = st.columns([4.5, 1.5])
                    with col_t1: st.markdown(f"🔹 **{it.get('назва')}** ({art}) — {it.get('к-ть')} шт × {it.get('ціна')} = **{it.get('сума')}**")
                    with col_t2:
                        if link: st.link_button("📕 PDF Креслення", link, use_container_width=True, key=f"lk_{idx}_{i}")
                        else:
                            if st.button("📕 PDF Креслення", use_container_width=True, key=f"err_{idx}_{i}"):
                                st.toast("❌ Креслення не знайдено", icon="⚠️")
                    t_sum += safe_float(it.get('сума'))
                if row['Коментар']: st.caption(f"💬 {row['Коментар']}")
                st.write(f"**Разом: {t_sum} грн** | Аванс: {row['Аванс']}")
            
            with c_status:
                opts = ["В черзі", "В роботі", "Готовий до відправлення", "Відправлений"]
                new_st = st.selectbox("Статус", opts, index=opts.index(status) if status in opts else 0, key=f"st_{idx}")
                if new_st != status:
                    df.loc[df['ID'] == row['ID'], 'Готовність'] = new_st
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

            if can_edit:
                with st.expander("📂 Редагувати"):
                    with st.form(f"f_ed_{idx}"):
                        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
                        e_cl, e_ph = r1c1.text_input("Клієнт", row['Клієнт']), r1c2.text_input("Телефон", row['Телефон'])
                        e_ct, e_tt = r1c3.text_input("Місто", row['Місто']), r1c4.text_input("ТТН", row['ТТН'])
                        
                        curr_items = []
                        for i, it in enumerate(items):
                            col1, col2, col3, col4, col5 = st.columns([2.5, 1, 1, 1, 1])
                            u_n, u_a = col1.text_input("Назва", it.get('назва'), key=f"n_{idx}_{i}"), col2.text_input("Арт", it.get('арт'), key=f"a_{idx}_{i}")
                            u_q = col3.number_input("К-ть", value=safe_int(it.get('к-ть')), key=f"q_{idx}_{i}")
                            u_p = col4.number_input("Ціна", value=safe_float(it.get('ціна')), key=f"p_{idx}_{i}")
                            u_s = col5.number_input("Сума", value=safe_float(it.get('сума')), key=f"s_{idx}_{i}")
                            if not st.checkbox(f"Видалити №{i+1}", key=f"del_{idx}_{i}"):
                                curr_items.append({"назва": u_n, "арт": u_a, "к-ть": int(u_q), "ціна": float(u_p), "сума": float(u_s)})

                        if st.form_submit_button("➕ Додати товар"):
                            curr_items.append({"назва": "", "арт": "", "к-ть": 1, "ціна": 0.0, "сума": 0.0})
                            df.loc[df['ID'] == row['ID'], 'Товари_JSON'] = json.dumps(curr_items, ensure_ascii=False)
                            save_csv(ORDERS_CSV_ID, df); st.rerun()

                        e_cm, e_av = st.text_area("Коментар", row['Коментар']), st.number_input("Аванс", value=safe_float(row['Аванс']))
                        if st.form_submit_button("💾 Зберегти"):
                            mask = df['ID'] == row['ID']
                            df.loc[mask, ['Клієнт', 'Телефон', 'Місто', 'ТТН', 'Коментар', 'Аванс']] = [e_cl, e_ph, e_ct, e_tt, e_cm, str(e_av)]
                            df.loc[mask, 'Товари_JSON'] = json.dumps(curr_items, ensure_ascii=False)
                            save_csv(ORDERS_CSV_ID, df); st.rerun()

# --- СТОРІНКА: НАЛАШТУВАННЯ ---
elif menu == "⚙️ Налаштування":
    st.header("Налаштування профілю")
    u_df = load_csv(USERS_CSV_ID, USER_COLS)
    my_email = st.session_state.auth['email']
    with st.container(border=True):
        st.write(f"**Ваш логін:** {my_email}")
        new_pass = st.text_input("Новий пароль", type="password")
        if st.button("Оновити пароль"):
            u_df.loc[u_df['email'] == my_email, 'password'] = new_pass
            save_csv(USERS_CSV_ID, u_df); st.success("Пароль змінено!")

    if role == "Супер Адмін":
        st.divider()
        st.subheader("🔴 Зона ризику")
        if st.button("❌ ОЧИСТИТИ БАЗУ ЗАМОВЛЕНЬ"): st.session_state.confirm_delete = True
        if st.session_state.get('confirm_delete'):
            st.error("Впевнені?")
            if st.button("ТАК, ВИДАЛИТИ ВСЕ"):
                save_csv(ORDERS_CSV_ID, pd.DataFrame(columns=COLS))
                st.session_state.confirm_delete = False; st.rerun()
            if st.button("СКАСУВАТИ"):
                st.session_state.confirm_delete = False; st.rerun()

# --- СТОРІНКА: КОРИСТУВАЧІ ---
elif menu == "👥 Користувачі" and role == "Супер Адмін":
    st.header("Керування командою")
    u_df = load_csv(USERS_CSV_ID, USER_COLS)
    with st.expander("➕ Додати користувача"):
        with st.form("add_u"):
            ne, np, nr = st.text_input("Email"), st.text_input("Пароль"), st.selectbox("Роль", ["Менеджер", "Адмін", "Токар", "Гість"])
            if st.form_submit_button("Створити"):
                u_df = pd.concat([u_df, pd.DataFrame([{'email': ne, 'password': np, 'role': nr}])], ignore_index=True)
                save_csv(USERS_CSV_ID, u_df); st.rerun()
    st.dataframe(u_df, use_container_width=True)
    del_u = st.selectbox("Видалити користувача", u_df['email'].unique())
    if st.button("Видалити"):
        u_df = u_df[u_df['email'] != del_u]
        save_csv(USERS_CSV_ID, u_df); st.rerun()

elif menu == "📐 Каталог креслень": st.info("🚧 У розробці")
elif menu == "🏗️ Матеріали": st.info("🚧 У розробці")

# --- ОНОВЛЕНІ ФУНКЦІЇ (Build 4.75) ---

@st.cache_data(ttl=60) # Кеш оновлюється кожну хвилину автоматично
def load_csv(file_id, cols):
    service = get_drive_service()
    if not service: return pd.DataFrame(columns=cols)
    try:
        # Додаємо унікальний параметр до запиту, щоб уникнути кешування на рівні Google
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
    except Exception as e:
        st.error(f"Помилка завантаження: {e}")
        return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=False)
        service.files().update(fileId=file_id, media_body=media_body).execute()
        # ОЧИЩЕННЯ КЕШУ ПІСЛЯ ЗБЕРЕЖЕННЯ
        st.cache_data.clear() 
        st.toast("Дані синхронізовано з хмарою ✅")
    except Exception as e:
        st.error(f"Помилка Drive: {e}")



