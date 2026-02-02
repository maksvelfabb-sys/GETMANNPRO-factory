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
        return df
    except Exception as e:
        # Якщо файл не знайдено (404), повертаємо порожню таблицю без "падіння" всієї програми
        return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: 
        st.error("Помилка: Сервіс Drive не підключений")
        return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=False)
        service.files().update(fileId=file_id, media_body=media_body).execute()
        st.toast("Збережено в хмару ✅")
    except Exception as e:
        st.error(f"❌ Помилка запису (Access 404): Надайте email сервісного акаунта права 'Редактор' для файлу {file_id}")

# --- АВТОРИЗАЦІЯ ---
if 'users_df' not in st.session_state:
    st.session_state.users_df = load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name'])

if 'auth' not in st.session_state:
    st.title("🏭 GETMANN Factory")
    with st.form("login"):
        e_in = st.text_input("Логін (Email)").strip()
        p_in = st.text_input("Пароль", type="password").strip()
        if st.form_submit_button("Увійти"):
            # Пріоритетний вхід для вас (навіть якщо Drive видає 404)
            if e_in == "maksvel.fabb@gmail.com" and p_in == "1234":
                st.session_state.auth = {'email': e_in, 'role': 'Супер Адмін', 'name': 'Максим'}
                st.rerun()
            
            u_df = st.session_state.users_df
            user = u_df[(u_df['email'] == e_in) & (u_df['password'] == str(p_in))]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("❌ Невірні дані")
    st.stop()

me = st.session_state.auth
role = me['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

# --- ДАНІ ЗАМОВЛЕНЬ ---
if 'df' not in st.session_state:
    st.session_state.df = load_csv(ORDERS_CSV_ID, ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])
df = st.session_state.df

# --- ІНТЕРФЕЙС ЖУРНАЛУ ---
tabs = st.tabs(["📋 Журнал замовлень", "⚙️ Адмін"])

with tabs[0]:
    if can_edit:
        with st.expander("➕ НОВЕ ЗАМОВЛЕННЯ"):
            # Розрахунок ID
            ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
            next_id = int(ids.max() + 1) if not ids.empty else 1001
            
            with st.form("new_order", clear_on_submit=True):
                c1, c2 = st.columns(2)
                f_id = c1.text_input("ID*", value=str(next_id))
                f_cl = c2.text_input("Клієнт*")
                f_ph, f_ct = c1.text_input("Телефон"), c2.text_input("Місто")
                
                tc1, tc2, tc3, tc4 = st.columns([3, 1, 1, 1])
                t_n, t_a = tc1.text_input("Товар"), tc2.text_input("Арт")
                t_q = tc3.number_input("К-ть", min_value=1, value=1)
                t_p = tc4.number_input("Ціна", min_value=0.0)
                
                f_cm = st.text_area("Коментар")
                f_av = st.number_input("Аванс", min_value=0.0)
                
                if st.form_submit_button("🚀 Створити замовлення"):
                    items = [{"назва": t_n, "арт": t_a, "к-ть": t_q, "ціна": t_p, "сума": t_q * t_p}]
                    new_row = {
                        'ID': str(f_id), 'Дата': datetime.now().strftime("%d.%m.%Y"),
                        'Клієнт': f_cl, 'Телефон': f_ph, 'Місто': f_ct,
                        'Аванс': f_av, 'Готовність': 'В черзі',
                        'Товари_JSON': json.dumps(items, ensure_ascii=False), 'Коментар': f_cm
                    }
                    st.session_state.df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, st.session_state.df)
                    st.rerun()

    st.divider()
    search = st.text_input("🔍 Пошук...")
    df_v = df.copy().iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        with st.container(border=True):
            c_h, c_s = st.columns([4, 1])
            c_h.markdown(f"### №{row['ID']} | {row['Клієнт']}")
            
            # Статус
            opts = ["В черзі", "В роботі", "Готово"]
            curr_st = row.get('Готовність', 'В черзі')
            if curr_st not in opts: curr_st = "В черзі"
            new_st = c_s.selectbox("Статус", opts, index=opts.index(curr_st), key=f"s_{idx}")
            if new_st != curr_st:
                df.at[idx, 'Готовність'] = new_st
                save_csv(ORDERS_CSV_ID, df); st.rerun()

            st.write(f"📅 {row['Дата']} | 📍 {row['Місто']}")
            
            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            
            total = 0
            for it in items:
                q, p = float(it.get('к-ть', 1)), float(it.get('ціна', 0))
                sub = q * p
                total += sub
                st.write(f"📦 **{it.get('назва')}** — {q} шт. x {p} = {sub} грн")
            
            try: avans = float(str(row['Аванс']).replace(',', '.')) if row['Аванс'] else 0.0
            except: avans = 0.0

            if role != "Токар":
                st.write(f"💰 **Разом:** {total} | **Залишок:** {total - avans}")

            if can_edit:
                with st.expander("✏️ Швидке редагування"):
                    ed_it = st.data_editor(pd.DataFrame(items), num_rows="dynamic", key=f"e_{idx}")
                    new_c = st.text_area("Коментар", value=row['Коментар'], key=f"c_{idx}")
                    new_a = st.number_input("Аванс", value=avans, key=f"a_{idx}")
                    if st.button("💾 Зберегти", key=f"b_{idx}"):
                        df.at[idx, 'Товари_JSON'] = ed_it.to_json(orient='records', force_ascii=False)
                        df.at[idx, 'Коментар'] = new_c
                        df.at[idx, 'Аванс'] = new_a
                        save_csv(ORDERS_CSV_ID, df); st.rerun()

with tabs[1]:
    if role == "Супер Адмін":
        st.subheader("Керування доступом")
        st.write("Сервісний Email для доступу в Drive:")
        st.code(dict(st.secrets["gcp_service_account"])["client_email"])
        ed_u = st.data_editor(st.session_state.users_df, num_rows="dynamic")
        if st.button("💾 Зберегти базу користувачів"): save_csv(USERS_CSV_ID, ed_u)

