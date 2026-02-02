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
        df = pd.read_csv(fh).fillna("")
        df.columns = df.columns.str.strip()
        # Переконаємось, що всі необхідні колонки є
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
        st.toast("Дані успішно оновлено ✅")
    except: st.error("Помилка синхронізації з Drive")

# --- АВТОРИЗАЦІЯ ---
if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP")
    with st.form("login_form"):
        e = st.text_input("Email").strip()
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
            else: st.error("Доступ заборонено")
    st.stop()

me = st.session_state.auth
role = me['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

# --- ДАНІ ЗАМОВЛЕНЬ ---
df = load_csv(ORDERS_CSV_ID, COLS)

tabs = st.tabs(["📋 Журнал замовлень", "⚙️ Адмін панель"])

with tabs[0]:
    if can_edit:
        with st.expander("➕ СТВОРИТИ НОВЕ ЗАМОВЛЕННЯ"):
            ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
            next_id = int(ids.max() + 1) if not ids.empty else 1001
            with st.form("new_order", clear_on_submit=True):
                c1, c2 = st.columns(2)
                f_id = c1.text_input("№ Замовлення*", value=str(next_id))
                f_cl = c2.text_input("ПІБ Клієнта*")
                f_ph, f_ct = c1.text_input("Телефон"), c2.text_input("Місто / Відділення")
                
                st.write("📦 **Товарна позиція:**")
                tc1, tc2, tc3, tc4 = st.columns([3, 1, 1, 1])
                t_n, t_a = tc1.text_input("Найменування"), tc2.text_input("Артикул")
                t_q = tc3.number_input("Кількість", min_value=1, value=1)
                t_p = tc4.number_input("Ціна за од.", min_value=0.0)
                
                f_cm = st.text_area("Коментар до замовлення")
                f_av = st.number_input("Сума авансу", min_value=0.0)
                
                if st.form_submit_button("🚀 Створити замовлення"):
                    items = [{"назва": t_n, "арт": t_a, "к-ть": t_q, "ціна": t_p, "сума": round(t_q * t_p, 2)}]
                    new_row = {'ID': str(f_id), 'Дата': datetime.now().strftime("%d.%m.%Y"), 'Клієнт': f_cl, 'Телефон': f_ph, 'Місто': f_ct, 'Аванс': f_av, 'Готовність': 'В черзі', 'Товари_JSON': json.dumps(items, ensure_ascii=False), 'Коментар': f_cm}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, df); st.rerun()

    st.divider()
    search = st.text_input("🔍 Швидкий пошук (Клієнт, №, телефон)...")
    df_display = df.copy().iloc[::-1]
    if search:
        df_display = df_display[df_display.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    for idx, row in df_display.iterrows():
        # Знаходимо оригінальний індекс в основному df
        orig_idx = df.index[df['ID'] == row['ID']][0]
        
        with st.container(border=True):
            col_info, col_stat = st.columns([4, 1])
            
            # Відображення клієнта
            col_info.markdown(f"### №{row['ID']} — {row['Клієнт']}")
            col_info.write(f"📞 **Телефон:** {row['Телефон']} | 📍 **Адреса:** {row['Місто']}")
            
            # Статус замовлення
            opts = ["В черзі", "В роботі", "Готово"]
            curr_st = row.get('Готовність', 'В черзі')
            new_st = col_stat.selectbox("Статус", opts, index=opts.index(curr_st) if curr_st in opts else 0, key=f"st_{idx}")
            if new_st != curr_st:
                df.at[orig_idx, 'Готовність'] = new_st
                save_csv(ORDERS_CSV_ID, df); st.rerun()

            # Товари
            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            
            total_sum = 0
            for it in items:
                q, p = float(it.get('к-ть', 0)), float(it.get('ціна', 0))
                s = round(q * p, 2)
                total_sum += s
                st.write(f"🔹 {it.get('назва')} ({it.get('арт')}) — {q} шт. x {p} грн = **{s} грн**")
            
            try: avans = float(str(row['Аванс']).replace(',', '.')) if row['Аванс'] else 0.0
            except: avans = 0.0

            if role != "Токар":
                c_m1, c_m2, c_m3 = st.columns(3)
                c_m1.metric("Сума замовлення", f"{round(total_sum, 2)} грн")
                c_m2.metric("Аванс", f"{avans} грн")
                c_m3.metric("Залишок", f"{round(total_sum - avans, 2)} грн")

            if row['Коментар']:
                st.info(f"💬 {row['Коментар']}")

            # РЕДАГУВАННЯ КАРТКИ
            if can_edit:
                with st.expander("✏️ РЕДАГУВАТИ ДАНІ ТА СКЛАД"):
                    st.subheader("👤 Дані клієнта")
                    ec1, ec2 = st.columns(2)
                    new_client = ec1.text_input("ПІБ Клієнта", value=row['Клієнт'], key=f"cl_{idx}")
                    new_phone = ec2.text_input("Телефон", value=row['Телефон'], key=f"ph_{idx}")
                    new_city = st.text_input("Місто / Відділення", value=row['Місто'], key=f"ct_{idx}")
                    
                    st.subheader("📦 Склад замовлення")
                    edited_items_df = st.data_editor(pd.DataFrame(items), num_rows="dynamic", key=f"it_{idx}")
                    
                    st.subheader("💰 Фінанси та коментар")
                    new_a = st.number_input("Аванс", value=avans, key=f"av_{idx}")
                    new_comm = st.text_area("Коментар", value=row['Коментар'], key=f"cm_{idx}")
                    
                    if st.button("💾 Зберегти зміни в картку", key=f"btn_{idx}"):
                        # Перерахунок сум у товарах
                        for i, r_it in edited_items_df.iterrows():
                            try: edited_items_df.at[i, 'сума'] = round(float(r_it['к-ть']) * float(r_it['ціна']), 2)
                            except: pass
                        
                        # Оновлення основного DataFrame
                        df.at[orig_idx, 'Клієнт'] = new_client
                        df.at[orig_idx, 'Телефон'] = new_phone
                        df.at[orig_idx, 'Місто'] = new_city
                        df.at[orig_idx, 'Аванс'] = new_a
                        df.at[orig_idx, 'Коментар'] = new_comm
                        df.at[orig_idx, 'Товари_JSON'] = edited_items_df.to_json(orient='records', force_ascii=False)
                        
                        save_csv(ORDERS_CSV_ID, df); st.rerun()

# --- АДМІН ПАНЕЛЬ ---
with tabs[1]:
    if role == "Супер Адмін":
        st.subheader("👥 Користувачі")
        u_df = load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name'])
        ed_u = st.data_editor(u_df, num_rows="dynamic")
        if st.button("💾 Зберегти користувачів"): save_csv(USERS_CSV_ID, ed_u)
        
        st.divider()
        st.subheader("⚠️ Очищення бази")
        if st.checkbox("Підтверджую видалення всіх замовлень"):
            if st.button("🔥 ОЧИСТИТИ ВСЕ", type="primary"):
                save_csv(ORDERS_CSV_ID, pd.DataFrame(columns=COLS)); st.rerun()
