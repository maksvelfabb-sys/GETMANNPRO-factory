import streamlit as st
import pandas as pd
import io, json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

# --- КОНФІГУРАЦІЯ ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

st.set_page_config(page_title="GETMANN Pro", layout="wide", page_icon="🏭")

# --- СТИЛІЗАЦІЯ ПІД ВЕРСІЮ 3.0 ---
st.markdown("""
    <style>
    .order-header {
        padding: 15px; border-radius: 8px; color: white; font-weight: bold;
        margin-bottom: 5px; display: flex; justify-content: space-between;
        font-size: 1.1em;
    }
    .header-work { background-color: #007bff; box-shadow: 0 4px 6px rgba(0,123,255,0.2); }
    .header-done { background-color: #28a745; box-shadow: 0 4px 6px rgba(40,167,69,0.2); }
    .header-queue { background-color: #444; }
    
    div[data-testid="stExpander"] { border: 1px solid #444; border-radius: 8px; background: #1e1e1e; }
    </style>
""", unsafe_allow_html=True)

# --- СЕРВІСНІ ФУНКЦІЇ ---
@st.cache_resource
def get_drive_service():
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
        creds = service_account.Credentials.from_service_account_info(info)
        return build('drive', 'v3', credentials=creds)
    return None

def load_data():
    service = get_drive_service()
    if not service: return pd.DataFrame()
    try:
        request = service.files().get_media(fileId=ORDERS_CSV_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh).fillna("")
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame(columns=['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар'])

def save_data(df):
    service = get_drive_service()
    if not service: return
    try:
        csv_data = df.to_csv(index=False).encode('utf-8')
        media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv', resumable=True)
        service.files().update(fileId=ORDERS_CSV_ID, media_body=media_body).execute()
        st.toast("Синхронізовано ✅")
    except Exception as e:
        st.error(f"Помилка Google Drive: {e}")

def find_pdf_link(article):
    service = get_drive_service()
    if not service: return None
    try:
        query = f"name = '{article}.pdf' and '{FOLDER_DRAWINGS_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, webViewLink)").execute()
        files = results.get('files', [])
        return files[0]['webViewLink'] if files else None
    except: return None

# --- ГОЛОВНИЙ ІНТЕРФЕЙС ---
st.title("🏭 GETMANN Pro System")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

tab_journal, tab_new = st.tabs(["📋 Журнал замовлень", "➕ Створити замовлення"])

with tab_journal:
    df = st.session_state.df
    search = st.text_input("🔍 Швидкий пошук (ID, Клієнт, Товар)...")
    display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df

    for idx, row in display_df.iterrows():
        status = row.get('Готовність', 'В черзі')
        h_color = "header-work" if status == "В роботі" else "header-done" if status == "Готово" else "header-queue"
        
        # МАЛЮЄМО КОЛЬОРОВУ ШАПКУ
        st.markdown(f'''
            <div class="order-header {h_color}">
                <span>⌛ №{row["ID"]} | {row["Дата"]} | 👤 {row["Клієнт"]}</span>
                <span>{status}</span>
            </div>
        ''', unsafe_allow_html=True)
        
        with st.expander("Розгорнути замовлення"):
            # Статус чекбоксами
            c1, c2, _ = st.columns([1, 1, 2])
            is_w = c1.checkbox("🏗️ У виробництво", value=(status == "В роботі"), key=f"sw_{idx}")
            is_d = c2.checkbox("✅ Виконано", value=(status == "Готово"), key=f"sd_{idx}")
            
            new_st = "Готово" if is_d else "В роботі" if is_w else "В черзі"
            if new_st != status:
                df.at[idx, 'Готовність'] = new_st
                save_data(df); st.rerun()

            st.divider()

            # ТОВАРИ
            st.markdown("#### 📦 Товари та ціни")
            try:
                raw_json = row.get('Товари_JSON', '[]')
                items = json.loads(raw_json) if raw_json and raw_json != "[]" else []
            except:
                items = []

            if not items: # Якщо JSON порожній, додаємо один пустий рядок
                items = [{"назва": "", "арт": "", "к-ть": 1, "ціна": 0.0}]

            new_items_state = []
            current_total = 0.0

            # Заголовки таблиці
            t1, t2, t3, t4, t5, t6 = st.columns([3, 2, 1, 1.5, 1.5, 0.5])
            t1.caption("Найменування"); t2.caption("Артикул"); t3.caption("К-ть"); t4.caption("Ціна"); t5.caption("Сума")

            for i, item in enumerate(items):
                col_n, col_a, col_q, col_p, col_s, col_pdf = st.columns([3, 2, 1, 1.5, 1.5, 0.5])
                
                name = col_n.text_input("N", value=item.get('назва', ''), key=f"n_{idx}_{i}", label_visibility="collapsed")
                art = col_a.text_input("A", value=item.get('арт', ''), key=f"a_{idx}_{i}", label_visibility="collapsed")
                qty = col_q.number_input("Q", value=int(item.get('к-ть', 1)), step=1, key=f"q_{idx}_{i}", label_visibility="collapsed")
                price = col_p.number_input("P", value=float(item.get('ціна', 0.0)), key=f"p_{idx}_{i}", label_visibility="collapsed")
                
                # МАТЕМАТИКА
                row_sum = qty * price
                current_total += row_sum
                col_s.write(f"**{row_sum}**")
                
                if art:
                    link = find_pdf_link(art)
                    if link: col_pdf.link_button("📄", link)
                
                new_items_state.append({"назва": name, "арт": art, "к-ть": qty, "ціна": price})

            if st.button("➕ Додати товар", key=f"add_{idx}"):
                new_items_state.append({"назва": "", "арт": "", "к-ть": 1, "ціна": 0.0})
                df.at[idx, 'Товари_JSON'] = json.dumps(new_items_state)
                save_data(df); st.rerun()

            st.divider()

            # ФІНАНСОВИЙ ПІДСУМОК
            f1, f2, f3 = st.columns(3)
            f1.metric("Загальна сума", f"{current_total} грн")
            avans = f2.number_input("Аванс", value=float(row.get('Аванс', 0.0)), key=f"av_{idx}")
            debt = current_total - avans
            f3.metric("Залишок до оплати", f"{debt} грн", delta=-avans, delta_color="inverse")

            # КОНТАКТИ ТА КОМЕНТАР
            c_ph, c_ct = st.columns(2)
            u_phone = c_ph.text_input("📞 Телефон", value=str(row.get('Телефон', '')), key=f"ph_{idx}")
            u_city = c_ct.text_input("📍 Місто / Відділення", value=str(row.get('Місто', '')), key=f"ct_{idx}")
            u_comm = st.text_area("📝 Коментар до замовлення", value=str(row.get('Коментар', '')), key=f"co_{idx}")

            if st.button("💾 ЗБЕРЕГТИ ЗМІНИ", key=f"btn_{idx}", use_container_width=True, type="primary"):
                df.at[idx, 'Товари_JSON'] = json.dumps(new_items_state)
                df.at[idx, 'Аванс'] = avans
                df.at[idx, 'Телефон'] = u_phone
                df.at[idx, 'Місто'] = u_city
                df.at[idx, 'Коментар'] = u_comm
                save_data(df); st.rerun()

with tab_new:
    st.subheader("📝 Реєстрація нового замовлення")
    with st.form("new_form"):
        n_id = st.text_input("ID замовлення (№)")
        n_cl = st.text_input("ПІБ Клієнта")
        n_ph = st.text_input("Номер телефону")
        n_av = st.number_input("Початковий аванс", min_value=0.0)
        if st.form_submit_button("Створити запис"):
            new_entry = {
                'ID': n_id, 'Дата': datetime.now().strftime("%d.%m.%Y"),
                'Клієнт': n_cl, 'Телефон': n_ph, 'Аванс': n_av,
                'Готовність': 'В черзі', 'Товари_JSON': json.dumps([{"назва": "", "арт": "", "к-ть": 1, "ціна": 0.0}])
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_entry])], ignore_index=True)
            save_data(st.session_state.df); st.rerun()

st.sidebar.button("🔄 Оновити дані", on_click=lambda: st.session_state.pop('df'))
