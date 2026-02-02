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
COLS = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")

# --- СТИЛІЗАЦІЯ ВСІЄЇ КАРТКИ ---
def get_card_style(status):
    # Повертає кольори фону та рамки залежно від статусу
    if status == "В роботі":
        return "background-color: #FFF9C4; border: 2px solid #FBC02D;" # Жовтий
    elif status == "Готовий до відправлення":
        return "background-color: #E1F5FE; border: 2px solid #0288D1;" # Блакитний
    elif status == "Відправлений":
        return "background-color: #C8E6C9; border: 2px solid #388E3C;" # Зелений
    else:
        return "background-color: #F5F5F5; border: 2px solid #BDBDBD;" # Сірий (Черга)

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
        st.toast("Статус оновлено ✅")
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

# --- ДАНІ ---
df = load_csv(ORDERS_CSV_ID, COLS)

tabs = st.tabs(["📋 Журнал замовлень", "⚙️ Адмін"])

with tabs[0]:
    if can_edit:
        with st.expander("➕ НОВЕ ЗАМОВЛЕННЯ"):
            numeric_ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
            next_id = int(numeric_ids.max() + 1) if not numeric_ids.empty else 1001
            with st.form("new_order", clear_on_submit=True):
                c1, c2 = st.columns(2)
                f_id = c1.text_input("№*", value=str(next_id))
                f_cl = c2.text_input("Клієнт*")
                f_ph, f_ct = c1.text_input("Телефон"), c2.text_input("Місто")
                st.write("📦 **Товари:**")
                tc1, tc2, tc3, tc4 = st.columns([3, 1, 1, 1])
                t_n, t_a = tc1.text_input("Назва"), tc2.text_input("Арт")
                t_q = tc3.number_input("К-ть", min_value=1, value=1)
                t_p = tc4.number_input("Ціна за од.", min_value=0.0)
                f_cm, f_av = st.text_area("Коментар"), st.number_input("Аванс", min_value=0.0)
                if st.form_submit_button("🚀 Створити"):
                    items = [{"назва": t_n, "арт": t_a, "к-ть": t_q, "ціна": t_p, "сума": round(t_q * t_p, 2)}]
                    new_row = {'ID': str(f_id), 'Дата': datetime.now().strftime("%d.%m.%Y"), 'Клієнт': f_cl, 'Телефон': str(f_ph), 'Місто': f_ct, 'Аванс': str(f_av), 'Готовність': 'В черзі', 'Товари_JSON': json.dumps(items, ensure_ascii=False), 'Коментар': f_cm}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

    st.divider()
    search = st.text_input("🔍 Пошук...")
    df_v = df.copy().iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        status = row.get('Готовність', 'В черзі')
        style = get_card_style(status)
        
        # ЄДИНИЙ КОЛЬОРОВИЙ КОНТЕЙНЕР ДЛЯ ВСІЄЇ КАРТКИ
        st.markdown(f"""
            <div style="{style} padding: 20px; border-radius: 12px; margin-bottom: 15px; color: #000000;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(0,0,0,0.1); padding-bottom: 10px; margin-bottom: 10px;">
                    <span style="font-size: 22px; font-weight: bold;">№{row['ID']} — {row['Клієнт']}</span>
                    <span style="font-weight: 700; background: rgba(255,255,255,0.5); padding: 3px 12px; border-radius: 6px;">{status.upper()}</span>
                </div>
                <div style="font-size: 16px; margin-bottom: 10px;">
                    📞 <b>{row['Телефон']}</b> | 📍 {row['Місто']} | 📅 {row['Дата']}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Контент всередині (товари, статус, фінанси)
        with st.container():
            # Робимо відступи, щоб візуально контент був "всередині" кольорового поля
            inner_col, _ = st.columns([10, 0.1])
            with inner_col:
                c_st1, c_st2 = st.columns([3, 1])
                
                # Товари
                try: items = json.loads(row['Товари_JSON'])
                except: items = []
                
                total = 0.0
                for it in items:
                    q, p = float(it.get('к-ть', 0)), float(it.get('ціна', 0))
                    total += (q * p)
                    st.write(f"🔹 **{it.get('назва')}** — {q} шт.")

                # Статус (змінюємо прямо тут)
                opts = ["В черзі", "В роботі", "Готовий до відправлення", "Відправлений"]
                new_st = c_st2.selectbox("Змінити статус", opts, index=opts.index(status) if status in opts else 0, key=f"st_{row['ID']}_{idx}")
                if new_st != status:
                    df.loc[df['ID'] == row['ID'], 'Готовність'] = new_st
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

                # Креслення
                drawings = get_drawings(row['ID'])
                if drawings:
                    with st.expander(f"📎 Креслення ({len(drawings)})"):
                        for d in drawings: st.markdown(f"🔗 [{d['name']}]({d['webViewLink']})")

                # Фінанси
                if role != "Токар":
                    try: avans = float(str(row['Аванс']).replace(',', '.')) if row['Аванс'] else 0.0
                    except: avans = 0.0
                    f1, f2, f3 = st.columns(3)
                    f1.metric("До сплати", f"{round(total, 2)} грн")
                    f2.metric("Аванс", f"{avans} грн")
                    f3.metric("Залишок", f"{round(total - avans, 2)} грн")

                if can_edit:
                    with st.expander("✏️ Редагувати"):
                        with st.form(f"f_{row['ID']}"):
                            e_cl = st.text_input("Клієнт", value=row['Клієнт'])
                            e_ph = st.text_input("Телефон", value=row['Телефон'])
                            e_ct = st.text_input("Місто", value=row['Місто'])
                            e_it = st.data_editor(pd.DataFrame(items), num_rows="dynamic")
                            e_av = st.number_input("Аванс", value=float(avans))
                            e_cm = st.text_area("Коментар", value=row['Коментар'])
                            if st.form_submit_button("💾 Зберегти"):
                                mask = df['ID'] == row['ID']
                                df.loc[mask, 'Клієнт'], df.loc[mask, 'Телефон'] = e_cl, e_ph
                                df.loc[mask, 'Місто'], df.loc[mask, 'Аванс'] = e_ct, str(e_av)
                                df.loc[mask, 'Коментар'], df.loc[mask, 'Товари_JSON'] = e_cm, json.dumps(e_it.to_dict('records'), ensure_ascii=False)
                                save_csv(ORDERS_CSV_ID, df); st.rerun()
        st.write("---") # Розділювач між картками

with tabs[1]:
    if role == "Супер Адмін":
        ed_u = st.data_editor(load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name']), num_rows="dynamic")
        if st.button("💾 Зберегти користувачів"): save_csv(USERS_CSV_ID, ed_u)
