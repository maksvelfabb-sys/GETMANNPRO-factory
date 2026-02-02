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
        # Читаємо ID та Телефон примусово як ТЕКСТ (str)
        df = pd.read_csv(fh, dtype={'ID': str, 'Телефон': str}).fillna("")
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
        st.toast("Збережено ✅")
    except Exception as e:
        st.error(f"Помилка Drive: {e}")

# --- АВТОРИЗАЦІЯ ---
if 'auth' not in st.session_state:
    st.title("🏭 Вхід у GETMANN ERP")
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
            else: st.error("❌ Доступ обмежено")
    st.stop()

me = st.session_state.auth
role = me['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

# --- ДАНІ ---
df = load_csv(ORDERS_CSV_ID, COLS)

tabs = st.tabs(["📋 Журнал", "⚙️ Адмін"])

with tabs[0]:
    if can_edit:
        with st.expander("➕ НОВЕ ЗАМОВЛЕННЯ"):
            # Коректний розрахунок наступного ID
            numeric_ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
            next_id = int(numeric_ids.max() + 1) if not numeric_ids.empty else 1001
            
            with st.form("new_order", clear_on_submit=True):
                c1, c2 = st.columns(2)
                f_id = c1.text_input("№ Замовлення*", value=str(next_id))
                f_cl = c2.text_input("Клієнт*")
                f_ph = c1.text_input("Телефон (текст)")
                f_ct = c2.text_input("Місто")
                
                st.write("📦 **Товар:**")
                tc1, tc2, tc3, tc4 = st.columns([3, 1, 1, 1])
                t_n, t_a = tc1.text_input("Назва"), tc2.text_input("Арт")
                t_q = tc3.number_input("К-ть", min_value=1, value=1)
                t_p = tc4.number_input("Ціна за од.", min_value=0.0)
                
                f_cm = st.text_area("Коментар")
                f_av = st.number_input("Аванс", min_value=0.0)
                
                if st.form_submit_button("🚀 Створити"):
                    items = [{"назва": t_n, "арт": t_a, "к-ть": t_q, "ціна": t_p, "сума": round(t_q * t_p, 2)}]
                    new_row = {
                        'ID': str(f_id), 'Дата': datetime.now().strftime("%d.%m.%Y"),
                        'Клієнт': f_cl, 'Телефон': str(f_ph), 'Місто': f_ct,
                        'Аванс': f_av, 'Готовність': 'В черзі',
                        'Товари_JSON': json.dumps(items, ensure_ascii=False), 'Коментар': f_cm
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

    st.divider()
    search = st.text_input("🔍 Пошук (Клієнт, Номер, Телефон)...")
    df_v = df.copy().iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        # ПОКРАЩЕНА ЛОГІКА ПОШУКУ РЯДКА (Safe Search)
        # Знаходимо індекс рядка в оригінальному df за унікальним ID
        try:
            target_matches = df.index[df['ID'].astype(str) == str(row['ID'])].tolist()
            if not target_matches: continue
            orig_idx = target_matches[0]
        except: continue

        with st.container(border=True):
            ci, cs = st.columns([4, 1])
            ci.markdown(f"### №{row['ID']} — {row['Клієнт']}")
            ci.write(f"📞 **Телефон:** {row['Телефон']} | 📍 **Місто:** {row['Місто']}")
            
            opts = ["В черзі", "В роботі", "Готово"]
            curr_st = row.get('Готовність', 'В черзі')
            # Безпечна зміна статусу
            new_st = cs.selectbox("Статус", opts, index=opts.index(curr_st) if curr_st in opts else 0, key=f"st_{row['ID']}_{idx}")
            if new_st != curr_st:
                df.at[orig_idx, 'Готовність'] = new_st
                save_csv(ORDERS_CSV_ID, df); st.rerun()

            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            
            total = 0
            for it in items:
                q, p = float(it.get('к-ть', 0)), float(it.get('ціна', 0))
                total += (q * p)
                st.write(f"🔹 {it.get('назва')} — {q} шт. x {p} грн")
            
            if role != "Токар":
                try: avans = float(str(row['Аванс']).replace(',', '.')) if row['Аванс'] else 0.0
                except: avans = 0.0
                c1, c2, c3 = st.columns(3)
                c1.metric("Разом", f"{round(total, 2)} грн")
                c2.metric("Аванс", f"{avans} грн")
                c3.metric("Залишок", f"{round(total - avans, 2)} грн")

            if can_edit:
                with st.expander("✏️ Редагувати замовлення"):
                    ec1, ec2 = st.columns(2)
                    new_cl = ec1.text_input("Клієнт", value=str(row['Клієнт']), key=f"cl_{idx}")
                    new_ph = ec2.text_input("Телефон", value=str(row['Телефон']), key=f"ph_{idx}")
                    new_ct = st.text_input("Місто", value=str(row['Місто']), key=f"ct_{idx}")
                    
                    ed_it = st.data_editor(pd.DataFrame(items), num_rows="dynamic", key=f"it_{idx}")
                    new_a = st.number_input("Аванс", value=float(avans), key=f"av_{idx}")
                    new_cm = st.text_area("Коментар", value=str(row['Коментар']), key=f"cm_{idx}")
                    
                    if st.button("💾 Зберегти зміни", key=f"btn_{idx}"):
                        for i, r in ed_it.iterrows():
                            try: ed_it.at[i, 'сума'] = round(float(r['к-ть']) * float(r['ціна']), 2)
                            except: pass
                        df.at[orig_idx, 'Клієнт'] = new_client
                        df.at[orig_idx, 'Телефон'] = str(new_ph)
                        df.at[orig_idx, 'Місто'] = new_city
                        df.at[orig_idx, 'Аванс'] = new_a
                        df.at[orig_idx, 'Коментар'] = new_comm
                        df.at[orig_idx, 'Товари_JSON'] = ed_it.to_json(orient='records', force_ascii=False)
                        save_csv(ORDERS_CSV_ID, df); st.rerun()

with tabs[1]:
    if role == "Супер Адмін":
        ed_u = st.data_editor(load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name']), num_rows="dynamic")
        if st.button("💾 Зберегти користувачів"): save_csv(USERS_CSV_ID, ed_u)
        st.divider()
        if st.checkbox("🔥 Активувати видалення бази"):
            if st.button("ОЧИСТИТИ ВСІ ЗАМОВЛЕННЯ", type="primary"):
                save_csv(ORDERS_CSV_ID, pd.DataFrame(columns=COLS)); st.rerun()

st.sidebar.button("🚪 Вихід", on_click=lambda: st.session_state.clear())
