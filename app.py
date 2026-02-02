import streamlit as st
import pandas as pd
import io, json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
USERS_CSV_ID = "1FDWndpOgRX21lwHk19SUoBfKyMj0K1Zc"
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

st.set_page_config(page_title="GETMANN ERP", layout="wide", page_icon="🏭")

# --- СЕРВІСНІ ФУНКЦІЇ ---
@st.cache_resource
def get_drive_service():
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
        creds = service_account.Credentials.from_service_account_info(info)
        return build('drive', 'v3', credentials=creds)
    return None

def load_csv(file_id, cols):
    service = get_drive_service()
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
    except:
        return pd.DataFrame(columns=cols)

def save_csv(file_id, df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=False)
        service.files().update(fileId=file_id, media_body=media_body).execute()
        st.toast("Синхронізація успішна ✅")
    except Exception as e:
        st.error(f"Помилка Drive: {e}")

# --- СИСТЕМА АВТОРИЗАЦІЇ (З ВИПРАВЛЕННЯМ) ---
if 'users_df' not in st.session_state:
    st.session_state.users_df = load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name'])

if 'auth' not in st.session_state:
    st.title("🏭 GETMANN ERP Вхід")
    with st.form("login_form"):
        e_in = st.text_input("Логін (Email)").strip()
        p_in = st.text_input("Пароль", type="password").strip()
        
        if st.form_submit_button("Увійти"):
            # 1. ПЕРЕВІРКА НА СУПЕР АДМІНА (Жорстко в коді)
            if e_in == "maksvel.fabb@gmail.com" and p_in == "1234":
                admin_data = {'email': e_in, 'password': p_in, 'role': 'Супер Адмін', 'name': 'Максим'}
                st.session_state.auth = admin_data
                
                # Додаємо в базу, якщо там ще немає
                u_df = st.session_state.users_df
                if u_df[u_df['email'] == e_in].empty:
                    u_df = pd.concat([u_df, pd.DataFrame([admin_data])], ignore_index=True)
                    save_csv(USERS_CSV_ID, u_df)
                st.rerun()
            
            # 2. Звичайна перевірка через CSV
            user = st.session_state.users_df[
                (st.session_state.users_df['email'] == e_in) & 
                (st.session_state.users_df['password'] == str(p_in))
            ]
            if not user.empty:
                st.session_state.auth = user.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("❌ Невірний логін або пароль")
    st.stop()

# --- ПІСЛЯ ВХОДУ ---
me = st.session_state.auth
role = me['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

if 'df' not in st.session_state:
    st.session_state.df = load_csv(ORDERS_CSV_ID, ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])
df = st.session_state.df

def get_next_id(current_df):
    try:
        ids = pd.to_numeric(current_df['ID'], errors='coerce').dropna()
        return int(ids.max() + 1) if not ids.empty else 1001
    except: return 1001

tabs = st.tabs(["📋 Журнал замовлень", "⚙️ Адмін"])

# --- ЖУРНАЛ ---
with tabs[0]:
    if can_edit:
        with st.expander("➕ СТВОРИТИ НОВЕ ЗАМОВЛЕННЯ"):
            next_id = get_next_id(df)
            with st.form("new_order", clear_on_submit=True):
                c1, c2 = st.columns(2)
                f_id = c1.text_input("Номер замовлення*", value=str(next_id))
                f_cl = c2.text_input("Клієнт*")
                f_ph = c1.text_input("Телефон")
                f_ct = c2.text_input("Місто/Відділення")
                st.write("📦 **Товар:**")
                tc1, tc2, tc3, tc4 = st.columns([3, 1, 1, 1])
                t_n = tc1.text_input("Назва")
                t_a = tc2.text_input("Артикул")
                t_q = tc3.number_input("К-ть", min_value=1, value=1)
                t_p = tc4.number_input("Ціна", min_value=0.0)
                f_cm = st.text_area("Коментар")
                f_av = st.number_input("Аванс", min_value=0.0)
                if st.form_submit_button("✅ Зберегти"):
                    if f_id and f_cl:
                        items = [{"назва": t_n, "арт": t_a, "к-ть": t_q, "ціна": t_p, "сума": t_q * t_p}]
                        new_row = {'ID': str(f_id), 'Дата': datetime.now().strftime("%d.%m.%Y"), 'Клієнт': f_cl, 'Телефон': f_ph, 'Місто': f_ct, 'Аванс': f_av, 'Готовність': 'В черзі', 'Товари_JSON': json.dumps(items, ensure_ascii=False), 'Коментар': f_cm}
                        st.session_state.df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        save_csv(ORDERS_CSV_ID, st.session_state.df)
                        st.rerun()

    st.divider()
    search = st.text_input("🔍 Пошук...")
    df_display = df.copy().iloc[::-1]
    if search:
        df_display = df_display[df_display.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    status_options = ["В черзі", "В роботі", "Готово"]
    for idx, row in df_display.iterrows():
        with st.container(border=True):
            c_h, c_s = st.columns([4, 1])
            c_h.markdown(f"### №{row['ID']} | {row['Клієнт']}")
            curr_stat = row.get('Готовність', 'В черзі')
            if curr_stat not in status_options: curr_stat = "В черзі"
            
            new_stat = c_s.selectbox("Статус", status_options, index=status_options.index(curr_stat), key=f"st_{idx}")
            if new_stat != curr_stat:
                df.at[idx, 'Готовність'] = new_stat
                save_csv(ORDERS_CSV_ID, df)
                st.rerun()
            
            st.write(f"📅 {row['Дата']} | 📞 {row['Телефон']} | 📍 {row['Місто']}")
            
            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            
            total_sum = 0
            for it in items:
                q, p = it.get('к-ть', 1), it.get('ціна', 0.0)
                sub = q * p
                total_sum += sub
                st.write(f"📦 **{it.get('назва')}** ({it.get('арт')}) — {q} шт. x {p} = {sub} грн")
            
            if role != "Токар":
                st.write(f"💰 **Сума:** {total_sum} | **Аванс:** {row['Аванс']} | **Залишок:** {total_sum - float(row['Аванс'])}")

            if can_edit:
                with st.expander("✏️ Редагувати"):
                    ed_it = st.data_editor(pd.DataFrame(items), num_rows="dynamic", key=f"ed_{idx}")
                    new_c = st.text_area("Коментар", value=row['Коментар'], key=f"c_{idx}")
                    new_a = st.number_input("Аванс", value=float(row['Аванс']), key=f"a_{idx}")
                    if st.button("💾 Зберегти", key=f"b_{idx}"):
                        for i, r_i in ed_it.iterrows():
                            ed_it.at[i, 'сума'] = float(r_i['к-ть']) * float(r_i['ціна'])
                        df.at[idx, 'Товари_JSON'] = ed_it.to_json(orient='records', force_ascii=False)
                        df.at[idx, 'Коментар'] = new_c
                        df.at[idx, 'Аванс'] = new_a
                        save_csv(ORDERS_CSV_ID, df)
                        st.rerun()

# --- АДМІН ---
with tabs[1]:
    if role in ["Супер Адмін", "Адмін"]:
        ed_u = st.data_editor(st.session_state.users_df, num_rows="dynamic")
        if st.button("💾 Зберегти користувачів"):
            save_csv(USERS_CSV_ID, ed_u)

st.sidebar.button("🚪 Вийти", on_click=lambda: st.session_state.clear())
