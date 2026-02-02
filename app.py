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
        st.toast("Хмара оновлена ✅")
    except Exception as e:
        st.error(f"Помилка Drive: {e}")

# --- АВТОРИЗАЦІЯ ТА СУПЕР АДМІН ---
if 'users_df' not in st.session_state:
    st.session_state.users_df = load_csv(USERS_CSV_ID, ['email', 'password', 'role', 'name'])

u_df = st.session_state.users_df

# Спеціальна перевірка для Максима (якщо профілю ще немає в CSV)
if u_df[u_df['email'] == 'maksvel.fabb@gmail.com'].empty:
    st.info("Виявлено вхід власника. Потрібна активація профілю Супер Адміна.")
    if st.button("🔥 АКТИВУВАТИ МАКСИМА (Супер Адмін)"):
        new_boss = pd.DataFrame([{
            'email': 'maksvel.fabb@gmail.com', 
            'password': '1234', 
            'role': 'Супер Адмін', 
            'name': 'Максим'
        }])
        st.session_state.users_df = pd.concat([u_df, new_boss], ignore_index=True)
        save_csv(USERS_CSV_ID, st.session_state.users_df)
        st.success("Профіль створено! Увійдіть з паролем 1234")
        st.rerun()

if 'auth' not in st.session_state:
    st.title("🏭 GETMANN Factory Login")
    with st.form("login_form"):
        e_in = st.text_input("Логін (Email)")
        p_in = st.text_input("Пароль", type="password")
        if st.form_submit_button("Увійти"):
            # Пошук у завантаженій базі
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

# Дані поточного користувача
me = st.session_state.auth
role = me['role']
can_edit = role in ["Супер Адмін", "Адмін", "Менеджер"]

# --- ДАНІ ЗАМОВЛЕНЬ ---
if 'df' not in st.session_state:
    st.session_state.df = load_csv(ORDERS_CSV_ID, ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])
df = st.session_state.df

# --- ІНТЕРФЕЙС ТА НАВІГАЦІЯ ---
st.sidebar.title(f"👤 {me['name']}")
st.sidebar.write(f"🏷️ Роль: **{role}**")

tabs_list = ["📋 Журнал замовлень"]
if can_edit: tabs_list.append("📝 Редактор товарів")
if role in ["Супер Адмін", "Адмін"]: tabs_list.append("⚙️ Адмін")

tabs = st.tabs(tabs_list)

# --- ТАБ 1: ЖУРНАЛ + СТВОРЕННЯ ---
with tabs[0]:
    if can_edit:
        with st.expander("➕ СТВОРИТИ НОВЕ ЗАМОВЛЕННЯ", expanded=False):
            with st.form("new_order", clear_on_submit=True):
                c1, c2 = st.columns(2)
                f_id = c1.text_input("Номер замовлення (ID)*")
                f_cl = c2.text_input("ПІБ Клієнта*")
                f_ph = c1.text_input("Телефон")
                f_ct = c2.text_input("Місто та відділення")
                st.write("📦 **Товар:**")
                tc1, tc2, tc3 = st.columns([3, 1, 1])
                t_n = tc1.text_input("Назва")
                t_a = tc2.text_input("Артикул")
                t_q = tc3.number_input("К-ть", min_value=1, value=1)
                f_cm = st.text_area("Коментар менеджера")
                f_av = st.number_input("Аванс (грн)", min_value=0.0)
                
                if st.form_submit_button("✅ Зберегти замовлення"):
                    if f_id and f_cl:
                        items = [{"назва": t_n, "арт": t_a, "к-ть": t_q}]
                        new_row = {
                            'ID': f_id, 'Дата': datetime.now().strftime("%d.%m.%Y"),
                            'Клієнт': f_cl, 'Телефон': f_ph, 'Місто': f_ct,
                            'Аванс': f_av, 'Готовність': 'В черзі',
                            'Товари_JSON': json.dumps(items, ensure_ascii=False),
                            'Коментар': f_cm
                        }
                        st.session_state.df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        save_csv(ORDERS_CSV_ID, st.session_state.df)
                        st.rerun()
                    else: st.error("ID та Клієнт обов'язкові!")

    st.divider()
    search = st.text_input("🔍 Пошук (ID, Ім'я, Артикул)...")
    # Сортування: нові замовлення зверху
    df_v = df.iloc[::-1]
    if search:
        df_v = df_v[df_v.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]
    
    for idx, row in df_v.iterrows():
        with st.container(border=True):
            c_h, c_s = st.columns([4, 1])
            c_h.markdown(f"### №{row['ID']} | {row['Клієнт']}")
            status = row.get('Готовність', 'В черзі')
            new_stat = c_s.selectbox("Статус", ["В черзі", "В роботі", "Готово"], 
                                     index=["В черзі", "В роботі", "Готово"].index(status), key=f"st_{idx}")
            if new_stat != status:
                df.at[idx, 'Готовність'] = new_stat
                save_csv(ORDERS_CSV_ID, df)
                st.rerun()
            st.write(f"📅 {row['Дата']} | 📍 {row['Місто']} | 📞 {row['Телефон']}")
            
            # Товари
            try: items = json.loads(row['Товари_JSON'])
            except: items = []
            for it in items:
                st.write(f"📦 **{it.get('назва')}** (Арт: {it.get('арт')}) — {it.get('к-ть')} шт.")
            if row['Коментар']: st.info(f"💬 {row['Коментар']}")

# --- ТАБ 2: РЕДАКТОР ---
if can_edit:
    with tabs[tabs_list.index("📝 Редактор товарів")]:
        s_id = st.selectbox("Оберіть замовлення для правки", df['ID'].tolist())
        if s_id:
            idx = df[df['ID'] == s_id].index[0]
            items_l = json.loads(df.at[idx, 'Товари_JSON'])
            st.write(f"Редагування складу №{s_id}")
            new_items = st.data_editor(pd.DataFrame(items_l), num_rows="dynamic")
            new_c = st.text_area("Коментар", value=df.at[idx, 'Коментар'])
            if st.button("💾 Зберегти зміни"):
                df.at[idx, 'Товари_JSON'] = new_items.to_json(orient='records', force_ascii=False)
                df.at[idx, 'Коментар'] = new_c
                save_csv(ORDERS_CSV_ID, df)
                st.success("Оновлено!")

# --- ТАБ 3: АДМІН ---
if "⚙️ Адмін" in tabs_list:
    with tabs[-1]:
        st.subheader("👥 Керування персоналом")
        ed_u = st.data_editor(st.session_state.users_df, num_rows="dynamic")
        if st.button("💾 Зберегти користувачів"):
            save_csv(USERS_CSV_ID, ed_u)

if st.sidebar.button("🚪 Вийти"):
    del st.session_state.auth
    st.rerun()
