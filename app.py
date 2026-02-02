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
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas" # ПОВЕРНУТО ✅
COLS = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']

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
        df = pd.read_csv(fh, dtype=str).fillna("")
        df.columns = df.columns.str.strip()
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
        st.toast("Синхронізовано ✅")
    except Exception as e:
        st.error(f"Помилка Drive: {e}")

# --- ФУНКЦІЯ ДЛЯ ПОШУКУ КРЕСЛЕНЬ ---
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
        p = st.text_input("Пароль", type="password", help="Введіть ваш пароль").strip()
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

# --- ОСНОВНІ ДАНІ ---
df = load_csv(ORDERS_CSV_ID, COLS)

tabs = st.tabs(["📋 Журнал", "⚙️ Адмін"])

with tabs[0]:
    if can_edit:
        with st.expander("➕ НОВЕ ЗАМОВЛЕННЯ"):
            numeric_ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
            next_id = int(numeric_ids.max() + 1) if not numeric_ids.empty else 1001
            with st.form("new_order", clear_on_submit=True):
                c1, c2 = st.columns(2)
                f_id = c1.text_input("№ Замовлення*", value=str(next_id))
                f_cl = c2.text_input("Клієнт*")
                f_ph = c1.text_input("Телефон")
                f_ct = c2.text_input("Місто")
                st.write("📦 **Товари:**")
                tc1, tc2, tc3, tc4 = st.columns([3, 1, 1, 1])
                t_n, t_a = tc1.text_input("Назва"), tc2.text_input("Арт")
                t_q = tc3.number_input("К-ть", min_value=1, value=1)
                t_p = tc4.number_input("Ціна", min_value=0.0)
                f_cm = st.text_area("Коментар")
                f_av = st.number_input("Аванс", min_value=0.0)
                if st.form_submit_button("🚀 Створити"):
                    items = [{"назва": t_n, "арт": t_a, "к-ть": t_q, "ціна": t_p, "сума": round(t_q * t_p, 2)}]
                    new_row = {'ID': str(f_id), 'Дата': datetime.now().strftime("%d.%m.%Y"), 'Клієнт': f_cl, 'Телефон': str(f_ph), 'Місто': f_ct, 'Аванс': str(f_av), 'Готовність': 'В черзі', 'Товари_JSON': json.dumps(items, ensure_ascii=False), 'Коментар': f_cm}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

    st.divider()
    search = st.text_input("🔍 Швидкий пошук...")
    df_v = df.copy().iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        with st.container(border=True):
            ci, cs = st.columns([4, 1])
            ci.markdown(f"### №{row['ID']} — {row['Клієнт']}")
            ci.write(f"📞 {row['Телефон']} | 📍 {row['Місто']}")
            
            # Статуси
            opts = ["В черзі", "В роботі", "Готово"]
            curr_st = row.get('Готовність', 'В черзі')
            new_st = cs.selectbox("Статус", opts, index=opts.index(curr_st) if curr_st in opts else 0, key=f"st_{row['ID']}_{idx}")
            
            if new_st != curr_st:
                df.loc[df['ID'] == row['ID'], 'Готовність'] = new_st
                save_csv(ORDERS_CSV_ID, df); st.rerun()

            # Відображення товарів
            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            
            total = 0.0
            for it in items:
                q, p = float(it.get('к-ть', 0)), float(it.get('ціна', 0))
                total += (q * p)
                st.write(f"🔹 {it.get('назва')} — {q} шт.")

            # ВІДОБРАЖЕННЯ КРЕСЛЕНЬ (Drawings logic)
            drawings = get_drawings(row['ID'])
            if drawings:
                with st.expander(f"📎 Креслення ({len(drawings)})"):
                    for d in drawings:
                        st.markdown(f"🔗 [{d['name']}]({d['webViewLink']})")

            # Фінанси
            if role != "Токар":
                try: avans = float(str(row['Аванс']).replace(',', '.')) if row['Аванс'] else 0.0
                except: avans = 0.0
                c1, c2, c3 = st.columns(3)
                c1.metric("Сума", f"{round(total, 2)} грн")
                c2.metric("Аванс", f"{avans} грн")
                c3.metric("Залишок", f"{round(total - avans, 2)} грн")

            # Редагування
            if can_edit:
                with st.expander("✏️ Редагувати"):
                    with st.form(f"edit_{row['ID']}"):
                        e_cl = st.text_input("Клієнт", value=row['Клієнт'])
                        e_ph = st.text_input("Телефон", value=row['Телефон'])
                        e_ct = st.text_input("Місто", value=row['Місто'])
                        e_it = st.data_editor(pd.DataFrame(items), num_rows="dynamic")
                        e_av = st.number_input("Аванс", value=float(avans) if 'avans' in locals() else 0.0)
                        e_cm = st.text_area("Коментар", value=row['Коментар'])
                        
                        if st.form_submit_button("💾 Зберегти"):
                            new_items = e_it.to_dict('records')
                            for item in new_items:
                                try: item['сума'] = round(float(item['к-ть']) * float(item['ціна']), 2)
                                except: item['сума'] = 0
                            
                            mask = df['ID'] == row['ID']
                            df.loc[mask, 'Клієнт'] = e_cl
                            df.loc[mask, 'Телефон'] = e_ph
                            df.loc[mask, 'Місто'] = e_ct
                            df.loc[mask, 'Аванс'] = str(e_av)
                            df.loc[mask, 'Коментар'] = e_cm
                            df.loc[mask, 'Товари_JSON'] = json.dumps(new_items, ensure_ascii=False)
                            save_csv(ORDERS_CSV_ID, df); st.rerun()

with tabs[1]:
    if role == "Супер Адмін":
        st.subheader("Налаштування користувачів")
        ed_u = st.data_editor(load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name']), num_rows="dynamic")
        if st.button("💾 Зберегти користувачів"): save_csv(USERS_CSV_ID, ed_u)
        st.divider()
        st.subheader("Системні ID")
        st.write(f"📁 Папка креслень: `{FOLDER_DRAWINGS_ID}`")
        if st.checkbox("Активувати видалення"):
            if st.button("ОЧИСТИТИ ВСІ ЗАМОВЛЕННЯ"):
                save_csv(ORDERS_CSV_ID, pd.DataFrame(columns=COLS)); st.rerun()

st.sidebar.button("🚪 Вихід", on_click=lambda: st.session_state.clear())
