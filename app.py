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

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")

def safe_float(value):
    try:
        if isinstance(value, str): value = value.replace(',', '.')
        return float(value)
    except: return 0.0

def safe_int(value):
    try: return int(float(value))
    except: return 1

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
        df = pd.read_csv(fh, dtype=str).fillna("")
        for c in cols:
            if c not in df.columns: df[c] = ""
        return df
    except: return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=False)
        service.files().update(fileId=file_id, media_body=media_body).execute()
        st.toast("Дані оновлено ✅")
    except: st.error("Помилка Drive")

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
                st.session_state.auth = {'email': e, 'role': 'Супер Адмін', 'name': 'Максим'}
                st.rerun()
            u_df = load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name'])
            user = u_df[(u_df['email'] == e) & (u_df['password'] == str(p))]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("❌ Помилка входу")
    st.stop()

df = load_csv(ORDERS_CSV_ID, COLS)
role = st.session_state.auth['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

tabs = st.tabs(["📋 Журнал", "⚙️ Адмін"])

with tabs[0]:
    search = st.text_input("🔍 Пошук...", label_visibility="collapsed")
    df_v = df.copy().iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        status = row.get('Готовність', 'В черзі')
        style = get_card_style(status)
        
        st.markdown(f'<div style="{style} padding: 8px 15px; border-radius: 6px; color: #000;"><b>№{row["ID"]} | {row["Клієнт"]}</b></div>', unsafe_allow_html=True)

        with st.container(border=True):
            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            
            it = items[0] if items else {"назва": "Товар", "к-ть": 1, "ціна": 0, "сума": 0}
            
            c1, c2 = st.columns([4, 1.2])
            with c1:
                st.markdown(f"🔹 {it.get('назва')}: **{it.get('к-ть')} шт** × {it.get('ціна')} грн = **{it.get('сума')} грн**")
            
            with c2:
                opts = ["В черзі", "В роботі", "Готовий до відправлення", "Відправлений"]
                new_st = st.selectbox("Статус", opts, index=opts.index(status) if status in opts else 0, key=f"st_{idx}", label_visibility="collapsed")
                if new_st != status:
                    df.loc[df['ID'] == row['ID'], 'Готовність'] = new_st
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

            if can_edit:
                with st.expander("✏️ Редагувати фінанси"):
                    with st.form(f"fm_{idx}"):
                        # Поточні значення для порівняння
                        cur_q = safe_int(it.get('к-ть'))
                        cur_p = safe_float(it.get('ціна'))
                        cur_s = safe_float(it.get('сума'))
                        
                        col_q, col_p, col_s = st.columns(3)
                        new_q = col_q.number_input("Кількість (шт)", value=cur_q, step=1)
                        new_p = col_p.number_input("Ціна за од. (грн)", value=cur_p)
                        new_s = col_s.number_input("Загальна сума (грн)", value=cur_s)
                        
                        e_av = st.number_input("Аванс (грн)", value=safe_float(row['Аванс']))
                        
                        if st.form_submit_button("💾 Оновити"):
                            # ЛОГІКА ПЕРЕРАХУНКУ:
                            # 1. Якщо змінилася сума (відрізняється від поточної в базі)
                            if round(new_s, 2) != round(cur_s, 2):
                                final_s = new_s
                                final_p = round(new_s / new_q, 2) if new_q > 0 else 0
                            # 2. Якщо сума не мінялася, але змінилася кількість або ціна
                            else:
                                final_p = new_p
                                final_s = round(new_q * new_p, 2)
                            
                            new_items = [{"назва": it.get('назва'), "к-ть": int(new_q), "ціна": float(final_p), "сума": float(final_s)}]
                            
                            mask = df['ID'] == row['ID']
                            df.loc[mask, 'Аванс'] = str(e_av)
                            df.loc[mask, 'Товари_JSON'] = json.dumps(new_items, ensure_ascii=False)
                            save_csv(ORDERS_CSV_ID, df); st.rerun()
