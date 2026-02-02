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
    except: st.error("Помилка синхронізації з Drive")

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
            else: st.error("❌ Невірні дані")
    st.stop()

me = st.session_state.auth
role = me['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

df = load_csv(ORDERS_CSV_ID, COLS)

tabs = st.tabs(["📋 Журнал", "⚙️ Адмін"])

with tabs[0]:
    if can_edit:
        with st.expander("➕ СТВОРИТИ ЗАМОВЛЕННЯ"):
            with st.form("new_order", clear_on_submit=True):
                c1, c2, c3 = st.columns([1, 2, 2])
                f_id = c1.text_input("№")
                f_cl = c2.text_input("Клієнт")
                f_ph = c3.text_input("Телефон")
                
                st.write("📦 **Товар:**")
                tc1, tc2, tc3 = st.columns([3, 1, 1])
                t_n = tc1.text_input("Назва")
                t_q = tc2.number_input("Кількість", min_value=1, step=1)
                t_p = tc3.number_input("Ціна за од. (грн)", min_value=0.0)
                
                if st.form_submit_button("🚀 Додати в базу"):
                    calc_sum = round(t_q * t_p, 2)
                    items = [{"назва": t_n, "к-ть": int(t_q), "ціна": float(t_p), "сума": calc_sum}]
                    new_row = {'ID': f_id, 'Дата': datetime.now().strftime("%d.%m.%Y"), 'Клієнт': f_cl, 'Телефон': f_ph, 'Аванс': "0", 'Готовність': 'В черзі', 'Товари_JSON': json.dumps(items, ensure_ascii=False)}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

    search = st.text_input("🔍 Пошук...", label_visibility="collapsed")
    df_v = df.copy().iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        status = row.get('Готовність', 'В черзі')
        style = get_card_style(status)
        
        st.markdown(f"""
            <div style="{style} padding: 8px 15px; border-radius: 6px; color: #000;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 15px; font-weight: bold;">№{row['ID']} | {row['Клієнт']}</span>
                    <span style="font-size: 10px; font-weight: bold; background: rgba(255,255,255,0.4); padding: 2px 6px; border-radius: 4px;">{status.upper()}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            
            c_info, c_status = st.columns([4, 1.2])
            with c_info:
                for it in items:
                    st.markdown(f"🔹 {it.get('назва')} — **{it.get('к-ть')} шт** × {it.get('ціна')} грн = **{it.get('сума')} грн**")
            
            with c_status:
                opts = ["В черзі", "В роботі", "Готовий до відправлення", "Відправлений"]
                new_st = st.selectbox("Статус", opts, index=opts.index(status) if status in opts else 0, key=f"s_{row['ID']}_{idx}", label_visibility="collapsed")
                if new_st != status:
                    df.loc[df['ID'] == row['ID'], 'Готовність'] = new_st
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

            if role != "Токар":
                total_order = sum(safe_float(it.get('сума', 0)) for it in items)
                avans = safe_float(row['Аванс'])
                f1, f2, f3 = st.columns(3)
                f1.write(f"<small>Разом:</small><br><b>{total_order} грн</b>", unsafe_allow_html=True)
                f2.write(f"<small>Аванс:</small><br><b>{avans} грн</b>", unsafe_allow_html=True)
                f3.write(f"<small>Залишок:</small><br><b style='color:red;'>{round(total_order - avans, 2)} грн</b>", unsafe_allow_html=True)

            if can_edit:
                with st.expander("✏️ Редагувати замовлення"):
                    with st.form(f"edit_f_{row['ID']}"):
                        e1, e2, e3 = st.columns([2, 1.5, 1.5])
                        e_cl = e1.text_input("Клієнт", value=row['Клієнт'])
                        e_ttn = e2.text_input("ТТН", value=row.get('ТТН', ''))
                        e_av = e3.number_input("Аванс (грн)", value=safe_float(row['Аванс']))
                        
                        st.write("📦 **Товари:**")
                        it = items[0] if items else {"назва": "", "к-ть": 1, "ціна": 0, "сума": 0}
                        
                        col_n, col_q, col_p, col_s = st.columns([2.5, 1, 1.5, 1.5])
                        edit_n = col_n.text_input("Назва товару", value=it.get('назва'))
                        edit_q = col_q.number_input("Кількість", value=safe_int(it.get('к-ть')), step=1)
                        edit_p = col_p.number_input("Ціна за од. (грн)", value=safe_float(it.get('ціна')))
                        
                        # Користувач може вручну ввести суму (наприклад, для знижки),
                        # але за замовчуванням ми підказуємо результат p * q
                        current_sum = safe_float(it.get('сума'))
                        edit_s = col_s.number_input("Сума (грн)", value=current_sum if current_sum > 0 else round(edit_q * edit_p, 2))
                        
                        if st.form_submit_button("💾 Зберегти"):
                            # ЛОГІКА: Кількість змінює СУМУ
                            # Якщо користувач не чіпав поле Суми, вона просто перерахується.
                            # Якщо він змінив кількість — сума = q * p.
                            final_sum = round(edit_q * edit_p, 2)
                            
                            new_items = [{"назва": edit_n, "к-ть": int(edit_q), "ціна": float(edit_p), "сума": final_sum}]
                            
                            mask = df['ID'] == row['ID']
                            df.loc[mask, 'Клієнт'], df.loc[mask, 'ТТН'] = e_cl, e_ttn
                            df.loc[mask, 'Аванс'], df.loc[mask, 'Товари_JSON'] = str(e_av), json.dumps(new_items, ensure_ascii=False)
                            save_csv(ORDERS_CSV_ID, df); st.rerun()
