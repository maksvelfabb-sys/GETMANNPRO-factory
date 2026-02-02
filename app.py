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

# --- СТИЛІЗАЦІЯ ---
st.markdown("""
    <style>
    .stExpander { border: none !important; margin-bottom: 10px !important; }
    .status-header {
        padding: 15px;
        border-radius: 8px;
        color: white;
        font-weight: bold;
        margin-bottom: 5px;
        display: flex;
        justify-content: space-between;
    }
    .header-work { background-color: #007bff; }
    .header-done { background-color: #28a745; }
    .header-queue { background-color: #444; }
    
    /* Зменшення відступів у таблиці товарів */
    div[data-testid="stColumn"] { padding: 0 5px !important; }
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
        while not done:
            _, done = downloader.next_chunk()
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
        st.toast("Дані синхронізовано ✅")
    except Exception as e:
        st.error(f"Помилка збереження: {e}")

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
st.title("🏭 Журнал GETMANN Pro")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

tabs = st.tabs(["📋 Замовлення", "➕ Створити", "⚙️ Налаштування"])

with tabs[0]:
    df = st.session_state.df
    search = st.text_input("🔍 Пошук замовлення (Клієнт, ID)...")
    display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df

    for idx, row in display_df.iterrows():
        status = row.get('Готовність', 'В черзі')
        h_color = "header-work" if status == "В роботі" else "header-done" if status == "Готово" else "header-queue"
        
        # Заголовок для експандера
        header_label = f"⌛ №{row.get('ID')} | {row.get('Клієнт')} | {row.get('Дата')}"
        
        # Створюємо кольорову плашку
        st.markdown(f'<div class="status-header {h_color}"><span>{header_label}</span><span>{status}</span></div>', unsafe_allow_html=True)
        
        with st.expander("Розгорнути деталі замовлення"):
            # 1. СТАТУСИ (Чекбокси)
            c1, c2, c3 = st.columns([1, 1, 2])
            is_work = c1.checkbox("🏗️ У виробництво", value=(status == "В роботі"), key=f"w_{idx}")
            is_done = c2.checkbox("✅ Виконано", value=(status == "Готово"), key=f"d_{idx}")
            
            new_st = "Готово" if is_done else "В роботі" if is_work else "В черзі"
            if new_st != status:
                df.at[idx, 'Готовність'] = new_st
                save_data(df); st.rerun()

            st.divider()

            # 2. ТОВАРИ (Таблиця)
            st.markdown("#### 📦 Склад замовлення")
            try:
                items_list = json.loads(row['Товари_JSON']) if row['Товари_JSON'] else []
            except:
                items_list = [{"назва": "Товар", "арт": "", "к-ть": 1, "ціна": 0}]
            
            updated_items = []
            total_sum = 0
            
            # Заголовки колонок
            h_n, h_a, h_q, h_p, h_t, h_pdf = st.columns([3, 2, 1, 1, 1, 0.5])
            h_n.caption("Назва"); h_a.caption("Артикул"); h_q.caption("К-ть"); h_p.caption("Ціна"); h_t.caption("Сума")

            for i, item in enumerate(items_list):
                col_n, col_a, col_q, col_p, col_t, col_pdf = st.columns([3, 2, 1, 1, 1, 0.5])
                
                name = col_n.text_input("N", value=item.get('назва', ''), key=f"n_{idx}_{i}", label_visibility="collapsed")
                art = col_a.text_input("A", value=item.get('арт', ''), key=f"a_{idx}_{i}", label_visibility="collapsed")
                # Кількість - ціле число
                qty = col_q.number_input("Q", value=int(item.get('к-ть', 1)), step=1, key=f"q_{idx}_{i}", label_visibility="collapsed")
                # Ціна - з можливістю зміни
                price = col_p.number_input("P", value=float(item.get('ціна', 0)), key=f"p_{idx}_{i}", label_visibility="collapsed")
                
                line_total = qty * price
                total_sum += line_total
                col_t.markdown(f"**{line_total}**")
                
                if art:
                    link = find_pdf_link(art)
                    if link: col_pdf.link_button("📄", link)
                
                updated_items.append({"назва": name, "арт": art, "к-ть": qty, "ціна": price})

            if st.button("➕ Додати товар", key=f"add_it_{idx}"):
                updated_items.append({"назва": "", "арт": "", "к-ть": 1, "ціна": 0})
                df.at[idx, 'Товари_JSON'] = json.dumps(updated_items)
                save_data(df); st.rerun()

            st.divider()

            # 3. ФІНАНСИ ТА ДАНІ КЛІЄНТА
            f1, f2, f3 = st.columns(3)
            f1.metric("Загальна сума", f"{total_sum} грн")
            avans = f2.number_input("Аванс", value=float(row.get('Аванс', 0)), key=f"av_{idx}")
            f3.metric("Залишок", f"{total_sum - avans} грн")

            col_cl1, col_cl2 = st.columns(2)
            u_phone = col_cl1.text_input("Телефон", value=str(row.get('Телефон', '')), key=f"u_ph_{idx}")
            u_city = col_cl2.text_input("Місто/Відділення", value=str(row.get('Місто', '')), key=f"u_ct_{idx}")
            
            comm = st.text_area("Коментар", value=str(row.get('Коментар', '')), key=f"co_{idx}", height=70)

            if st.button("💾 Зберегти всі зміни", key=f"save_{idx}", use_container_width=True):
                df.at[idx, 'Товари_JSON'] = json.dumps(updated_items)
                df.at[idx, 'Аванс'] = avans
                df.at[idx, 'Коментар'] = comm
                df.at[idx, 'Телефон'] = u_phone
                df.at[idx, 'Місто'] = u_city
                save_data(df); st.rerun()

with tabs[1]:
    st.subheader("📝 Нове замовлення")
    with st.form("new"):
        c_id = st.text_input("ID замовлення")
        c_cl = st.text_input("Клієнт")
        c_ph = st.text_input("Телефон")
        c_ct = st.text_input("Місто/Відділення")
        c_av = st.number_input("Аванс", min_value=0, step=100)
        if st.form_submit_button("Створити"):
            new_r = {
                'ID': c_id, 'Дата': datetime.now().strftime("%d.%m.%Y"),
                'Клієнт': c_cl, 'Телефон': c_ph, 'Місто': c_ct, 'Аванс': c_av,
                'Готовність': 'В черзі', 'Товари_JSON': json.dumps([{"назва": "", "арт": "", "к-ть": 1, "ціна": 0}])
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_r])], ignore_index=True)
            save_data(st.session_state.df); st.rerun()

st.sidebar.button("🔄 Оновити базу", on_click=lambda: st.session_state.pop('df'))
