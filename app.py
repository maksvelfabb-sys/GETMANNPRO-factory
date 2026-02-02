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

def get_card_style(status):
    if status == "В роботі":
        return "background-color: #FFF9C4; border: 1px solid #FBC02D;"
    elif status == "Готовий до відправлення":
        return "background-color: #E1F5FE; border: 1px solid #0288D1;"
    elif status == "Відправлений":
        return "background-color: #C8E6C9; border: 1px solid #388E3C;"
    else:
        return "background-color: #FAFAFA; border: 1px solid #D1D1D1;"

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
        st.toast("Збережено ✅")
    except: st.error("Помилка Drive")

def get_drawings(order_id):
    service = get_drive_service()
    if not service: return []
    try:
        query = f"'{FOLDER_DRAWINGS_ID}' in parents and name contains '{order_id}' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
        return results.get('files', [])
    except: return []

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
            else: st.error("❌ Доступ заборонено")
    st.stop()

me = st.session_state.auth
role = me['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

df = load_csv(ORDERS_CSV_ID, COLS)

tabs = st.tabs(["📋 Журнал", "⚙️ Адмін"])

with tabs[0]:
    if can_edit:
        with st.expander("➕ НОВЕ ЗАМОВЛЕННЯ"):
            numeric_ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
            next_id = int(numeric_ids.max() + 1) if not numeric_ids.empty else 1001
            with st.form("new_order", clear_on_submit=True):
                c1, c2, c3 = st.columns([1, 2, 2])
                f_id = c1.text_input("№*", value=str(next_id))
                f_cl = c2.text_input("Клієнт*")
                f_ph = c3.text_input("Телефон")
                
                c4, c5, c6 = st.columns([2, 2, 1])
                f_ct = c4.text_input("Місто")
                f_ttn = c5.text_input("ТТН")
                f_av = c6.number_input("Аванс", min_value=0.0)
                
                f_cm = st.text_area("Коментар", height=68)
                
                st.write("📦 **Товари:**")
                tc1, tc2, tc3, tc4 = st.columns([3, 1, 1, 1])
                t_n, t_a, t_q, t_p = tc1.text_input("Назва"), tc2.text_input("Арт"), tc3.number_input("К-ть", 1), tc4.number_input("Ціна", 0.0)
                
                if st.form_submit_button("🚀 Створити"):
                    items = [{"назва": t_n, "арт": t_a, "к-ть": t_q, "ціна": t_p, "сума": round(t_q * t_p, 2)}]
                    new_row = {'ID': str(f_id), 'Дата': datetime.now().strftime("%d.%m.%Y"), 'Клієнт': f_cl, 'Телефон': str(f_ph), 'Місто': f_ct, 'ТТН': f_ttn, 'Аванс': str(f_av), 'Готовність': 'В черзі', 'Товари_JSON': json.dumps(items, ensure_ascii=False), 'Коментар': f_cm}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

    search = st.text_input("🔍 Пошук...", label_visibility="collapsed")
    df_v = df.copy().iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        status = row.get('Готовність', 'В черзі')
        ttn_val = row.get('ТТН', '')
        style = get_card_style(status)
        
        st.markdown(f"""
            <div style="{style} padding: 8px 15px; border-radius: 6px; margin-bottom: 0px; color: #000;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 16px; font-weight: bold;">№{row['ID']} | {row['Клієнт']} {f'| 📦 ТТН: {ttn_val}' if ttn_val else ''}</span>
                    <span style="font-size: 11px; font-weight: 700;">{status.upper()}</span>
                </div>
                <div style="font-size: 12px; opacity: 0.8;">
                    📞 {row['Телефон']} | 📍 {row['Місто']} | 📅 {row['Дата']}
                </div>
            </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            c_main, c_side = st.columns([4, 1.2])
            with c_main:
                try: items = json.loads(row['Товари_JSON'])
                except: items = []
                total = sum(float(it.get('к-ть', 0)) * float(it.get('ціна', 0)) for it in items)
                item_list = [f"<b>{it.get('назва')}</b> ({it.get('к-ть')}шт)" for it in items]
                st.markdown(" • ".join(item_list), unsafe_allow_html=True)
                if row['Коментар']: st.markdown(f"<small style='color: #444;'>💬 {row['Коментар']}</small>", unsafe_allow_html=True)

            with c_side:
                opts = ["В черзі", "В роботі", "Готовий до відправлення", "Відправлений"]
                new_st = st.selectbox("Статус", opts, index=opts.index(status) if status in opts else 0, key=f"st_{row['ID']}_{idx}", label_visibility="collapsed")
                if new_st != status:
                    df.loc[df['ID'] == row['ID'], 'Готовність'] = new_st
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

            f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
            if role != "Токар":
                avans = float(str(row['Аванс']).replace(',', '.')) if row['Аванс'] else 0.0
                f1.caption(f"Сплачено: {avans}")
                f2.caption(f"Залишок: {round(total - avans, 2)}")
            
            draws = get_drawings(row['ID'])
            if draws: f4.markdown(f"📎 <small>Креслень: {len(draws)}</small>", unsafe_allow_html=True)

            if can_edit:
                with st.expander("✏️ Редагувати дані замовлення"):
                    with st.form(f"ed_{row['ID']}"):
                        r1c1, r1c2, r1c3 = st.columns(3)
                        e_cl = r1c1.text_input("Клієнт", value=row['Клієнт'])
                        e_ph = r1c2.text_input("Телефон", value=row['Телефон'])
                        e_ttn = r1c3.text_input("ТТН", value=row.get('ТТН', ''))
                        
                        r2c1, r2c2 = st.columns([1, 2])
                        e_ct = r2c1.text_input("Місто", value=row.get('Місто', ''))
                        e_cm = r2c2.text_input("Коментар", value=row.get('Коментар', ''))
                        
                        e_it = st.data_editor(pd.DataFrame(items), num_rows="dynamic", key=f"det_{idx}")
                        
                        if st.form_submit_button("Зберегти зміни"):
                            mask = df['ID'] == row['ID']
                            df.loc[mask, 'Клієнт'] = e_cl
                            df.loc[mask, 'Телефон'] = e_ph
                            df.loc[mask, 'Місто'] = e_ct
                            df.loc[mask, 'ТТН'] = e_ttn
                            df.loc[mask, 'Коментар'] = e_cm
                            df.loc[mask, 'Товари_JSON'] = json.dumps(e_it.to_dict('records'), ensure_ascii=False)
                            save_csv(ORDERS_CSV_ID, df); st.rerun()
