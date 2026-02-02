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
COLS = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")

# --- ДОПОМІЖНІ ФУНКЦІЇ (Drive) ---
def safe_float(v):
    try: return float(str(v).replace(',', '.'))
    except: return 0.0

def safe_int(v):
    try: return int(float(v))
    except: return 1

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
        st.toast("Збережено на Drive ✅")
    except: st.error("Помилка синхронізації")

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
    with st.form("login"):
        e = st.text_input("Логін").strip()
        p = st.text_input("Пароль", type="password").strip()
        if st.form_submit_button("Увійти"):
            if e == "maksvel.fabb@gmail.com" and p == "1234":
                st.session_state.auth = {'email': e, 'role': 'Супер Адмін'}
                st.rerun()
            u_df = load_csv(USERS_CSV_ID, ['email', 'password', 'role'])
            user = u_df[(u_df['email'] == e) & (u_df['password'] == str(p))]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("❌ Доступ обмежено")
    st.stop()

# --- SIDEBAR МЕНЮ ---
with st.sidebar:
    st.title("🏢 МЕНЮ")
    menu = st.radio("Навігація:", 
        ["📋 Замовлення", "⚙️ Налаштування", "📐 Каталог креслень", "🏗️ Матеріали"],
        index=0)
    st.divider()
    st.caption(f"Увійшов: {st.session_state.auth['email']}")
    st.caption(f"Роль: {st.session_state.auth['role']}")
    if st.button("🚪 Вихід"):
        del st.session_state.auth
        st.rerun()

# --- ЛОГІКА СТОРІНОК ---

if menu == "📋 Замовлення":
    st.header("Журнал замовлень")
    df = load_csv(ORDERS_CSV_ID, COLS)
    role = st.session_state.auth['role']
    can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

    if can_edit:
        with st.expander("➕ НОВЕ ЗАМОВЛЕННЯ"):
            numeric_ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
            next_id = int(numeric_ids.max() + 1) if not numeric_ids.empty else 1001
            with st.form("new_order", clear_on_submit=True):
                c1, c2, c3 = st.columns([1, 2, 2])
                f_id = c1.text_input("№*", value=str(next_id))
                f_cl, f_ph = c2.text_input("Клієнт*"), c3.text_input("Телефон")
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
        
        client_info = f"{row['Клієнт']} | {row['Телефон']} | {row['Місто']}"
        st.markdown(f'<div style="{style} padding: 10px 15px; border-radius: 8px; color: #000; margin-bottom: 5px;"><b>№{row["ID"]} | {client_info} {f"| 📦 {row.get("ТТН","")}" if row.get("ТТН","") else ""}</b></div>', unsafe_allow_html=True)

        with st.container(border=True):
            c_info, c_status = st.columns([4, 1.2])
            with c_info:
                total_sum = 0
                for it in items:
                    st.markdown(f"🔹 **{it.get('назва')}** ({it.get('арт')}) — {it.get('к-ть')} шт × {it.get('ціна')} = **{it.get('сума')}**")
                    total_sum += safe_float(it.get('сума'))
                if row['Коментар']: st.caption(f"💬 {row['Коментар']}")
                st.write(f"**Разом: {total_sum} грн** | Аванс: {row['Аванс']}")
            
            with c_status:
                opts = ["В черзі", "В роботі", "Готовий до відправлення", "Відправлений"]
                new_st = st.selectbox("Статус", opts, index=opts.index(status) if status in opts else 0, key=f"st_{idx}")
                if new_st != status:
                    df.loc[df['ID'] == row['ID'], 'Готовність'] = new_st
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

            if can_edit:
                with st.expander("📂 Розгорнути"):
                    with st.form(f"f_edit_{idx}"):
                        st.write("👤 **Клієнт**")
                        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
                        e_cl, e_ph = r1c1.text_input("Клієнт", row['Клієнт']), r1c2.text_input("Телефон", row['Телефон'])
                        e_ct, e_tt = r1c3.text_input("Місто", row['Місто']), r1c4.text_input("ТТН", row['ТТН'])
                        
                        st.write("📦 **Товари**")
                        curr_items = []
                        for i, it in enumerate(items):
                            col1, col2, col3, col4, col5 = st.columns([2.5, 1, 1, 1, 1])
                            u_n = col1.text_input("Назва", it.get('назва'), key=f"n_{idx}_{i}")
                            u_a = col2.text_input("Арт", it.get('арт'), key=f"a_{idx}_{i}")
                            u_q = col3.number_input("К-ть", value=safe_int(it.get('к-ть')), step=1, key=f"q_{idx}_{i}")
                            u_p = col4.number_input("Ціна", value=safe_float(it.get('ціна')), key=f"p_{idx}_{i}")
                            u_s = col5.number_input("Сума", value=safe_float(it.get('сума')), key=f"s_{idx}_{i}")
                            
                            old_s = safe_float(it.get('сума'))
                            if round(u_s, 2) != round(old_s, 2):
                                f_p, f_s = round(u_s / u_q, 2) if u_q > 0 else 0.0, u_s
                            else:
                                f_p, f_s = u_p, round(u_q * u_p, 2)
                            
                            if not st.checkbox(f"Видалити №{i+1}", key=f"del_{idx}_{i}"):
                                curr_items.append({"назва": u_n, "арт": u_a, "к-ть": int(u_q), "ціна": float(f_p), "сума": float(f_s)})

                        if st.form_submit_button("➕ Додати товар"):
                            curr_items.append({"назва": "", "арт": "", "к-ть": 1, "ціна": 0.0, "сума": 0.0})
                            df.loc[df['ID'] == row['ID'], 'Товари_JSON'] = json.dumps(curr_items, ensure_ascii=False)
                            save_csv(ORDERS_CSV_ID, df); st.rerun()

                        e_cm = st.text_area("Коментар", row['Коментар'])
                        e_av = st.number_input("Аванс", value=safe_float(row['Аванс']))
                        
                        if st.form_submit_button("💾 Зберегти зміни"):
                            mask = df['ID'] == row['ID']
                            df.loc[mask, ['Клієнт', 'Телефон', 'Місто', 'ТТН', 'Коментар', 'Аванс']] = [e_cl, e_ph, e_ct, e_tt, e_cm, str(e_av)]
                            df.loc[mask, 'Товари_JSON'] = json.dumps(curr_items, ensure_ascii=False)
                            save_csv(ORDERS_CSV_ID, df); st.rerun()

elif menu == "⚙️ Налаштування":
    st.header("Налаштування профілю")
    u_df = load_csv(USERS_CSV_ID, ['email', 'password', 'role'])
    my_email = st.session_state.auth['email']
    
    with st.container(border=True):
        st.write(f"**Ваш логін:** {my_email}")
        st.write(f"**Ваша роль:** {st.session_state.auth['role']}")
        
        new_pass = st.text_input("Новий пароль", type="password")
        if st.button("Оновити пароль"):
            if new_pass:
                u_df.loc[u_df['email'] == my_email, 'password'] = new_pass
                save_csv(USERS_CSV_ID, u_df)
                st.success("Пароль успішно змінено!")
            else: st.warning("Введіть пароль")

elif menu == "📐 Каталог креслень":
    st.info("🚧 Цей розділ знаходиться у розробці")

elif menu == "🏗️ Матеріали":
    st.info("🚧 Цей розділ знаходиться у розробці")
