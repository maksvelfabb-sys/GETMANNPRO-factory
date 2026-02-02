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

# --- ДОПОМІЖНІ ФУНКЦІЇ ---
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
        return df
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

df = load_csv(ORDERS_CSV_ID, COLS)
role = st.session_state.auth['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

# --- ЖУРНАЛ ---
search = st.text_input("🔍 Пошук замовлення...", label_visibility="collapsed")
df_v = df.copy().iloc[::-1]
if search:
    df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

for idx, row in df_v.iterrows():
    status = row.get('Готовність', 'В черзі')
    ttn_val = row.get('ТТН', '')
    style = get_card_style(status)
    
    # Компактна шапка
    st.markdown(f"""
        <div style="{style} padding: 10px 15px; border-radius: 8px; color: #000; margin-bottom: -5px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 16px; font-weight: bold;">№{row['ID']} | {row['Клієнт']} {f'| 📦 ТТН: {ttn_val}' if ttn_val else ''}</span>
                <span style="font-size: 11px; font-weight: bold; background: rgba(255,255,255,0.5); padding: 2px 8px; border-radius: 4px;">{status.upper()}</span>
            </div>
            <div style="font-size: 13px; opacity: 0.8;">📍 {row['Місто']} | 📞 {row['Телефон']} | 📅 {row['Дата']}</div>
        </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        try: items = json.loads(row['Товари_JSON'])
        except: items = []
        it = items[0] if items else {"назва": "", "арт": "", "к-ть": 1, "ціна": 0, "сума": 0}
        
        c_info, c_status = st.columns([4, 1.2])
        with c_info:
            st.markdown(f"🔹 **{it.get('назва')}** (Арт: {it.get('арт','')}) — {it.get('к-ть')} шт × {it.get('ціна')} грн = **{it.get('сума')} грн**")
            if row['Коментар']: st.caption(f"💬 {row['Коментар']}")
        
        with c_status:
            opts = ["В черзі", "В роботі", "Готовий до відправлення", "Відправлений"]
            new_st = st.selectbox("Статус", opts, index=opts.index(status) if status in opts else 0, key=f"st_{idx}", label_visibility="collapsed")
            if new_st != status:
                df.loc[df['ID'] == row['ID'], 'Готовність'] = new_st
                save_csv(ORDERS_CSV_ID, df); st.rerun()

        if can_edit:
            with st.expander("✏️ Редагувати все (Дані, Товари, Фінанси)"):
                with st.form(f"form_full_{idx}"):
                    # РЯДОК 1: ДАНІ КЛІЄНТА
                    st.write("👤 **Дані клієнта та логістика**")
                    r1c1, r1c2, r1c3, r1c4 = st.columns([2, 2, 2, 2])
                    e_cl = r1c1.text_input("Клієнт", value=row['Клієнт'])
                    e_ph = r1c2.text_input("Телефон", value=row['Телефон'])
                    e_ct = r1c3.text_input("Місто", value=row['Місто'])
                    e_tt = r1c4.text_input("ТТН", value=row['ТТН'])
                    
                    # РЯДОК 2: ТОВАР ТА АРТИКУЛ
                    st.write("📦 **Специфікація товару**")
                    r2c1, r2c2, r2c3 = st.columns([3, 1.5, 3.5])
                    e_n = r2c1.text_input("Назва товару", value=it.get('назва'))
                    e_a = r2c2.text_input("Артикул", value=it.get('арт'))
                    e_cm = r2c3.text_input("Коментар до замовлення", value=row['Коментар'])
                    
                    # РЯДОК 3: ФІНАНСОВА ЛОГІКА
                    st.write("💰 **Фінанси (з автоперерахунком)**")
                    f_q, f_p, f_s, f_av = st.columns(4)
                    new_q = f_q.number_input("К-ть (шт)", value=safe_int(it.get('к-ть')), step=1)
                    new_p = f_p.number_input("Ціна за од. (грн)", value=safe_float(it.get('ціна')))
                    new_s = f_s.number_input("СУМА (грн)", value=safe_float(it.get('сума')))
                    new_av = f_av.number_input("АВАНС (грн)", value=safe_float(row['Аванс']))
                    
                    if st.form_submit_button("💾 Зберегти всі зміни"):
                        # ЛОГІКА: Якщо сума змінена вручну — міняємо ціну за одиницю
                        if round(new_s, 2) != round(safe_float(it.get('сума')), 2):
                            final_s = new_s
                            final_p = round(new_s / new_q, 2) if new_q > 0 else 0
                        else:
                            # Інакше (змінено ціну або к-ть) — сума = q * p
                            final_p = new_p
                            final_s = round(new_q * new_p, 2)
                        
                        updated_items = [{"назва": e_n, "арт": e_a, "к-ть": int(new_q), "ціна": float(final_p), "сума": float(final_s)}]
                        
                        mask = df['ID'] == row['ID']
                        df.loc[mask, 'Клієнт'], df.loc[mask, 'Телефон'] = e_cl, e_ph
                        df.loc[mask, 'Місто'], df.loc[mask, 'ТТН'] = e_ct, e_tt
                        df.loc[mask, 'Коментар'], df.loc[mask, 'Аванс'] = e_cm, str(new_av)
                        df.loc[mask, 'Товари_JSON'] = json.dumps(updated_items, ensure_ascii=False)
                        
                        save_csv(ORDERS_CSV_ID, df); st.rerun()

    st.write("") # Розділювач
