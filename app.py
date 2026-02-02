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

# --- СТИЛІЗАЦІЯ (Повна заливка шапки) ---
st.markdown("""
    <style>
    .order-header {
        padding: 12px;
        border-radius: 8px 8px 0px 0px;
        color: white;
        font-weight: bold;
        font-size: 1.1em;
        margin-bottom: 0px;
    }
    .header-work { background-color: #007bff; border: 1px solid #0056b3; }
    .header-done { background-color: #28a745; border: 1px solid #1e7e34; }
    .header-queue { background-color: #444; border: 1px solid #222; }
    
    .order-body {
        border: 1px solid #444;
        border-top: none;
        border-radius: 0px 0px 8px 8px;
        padding: 20px;
        background-color: #1e1e1e;
        margin-bottom: 20px;
    }
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
        st.toast("Збережено ✅")
    except Exception as e:
        st.error(f"Помилка: {e}")

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

tabs = st.tabs(["📑 Журнал", "➕ Нове замовлення", "📦 Склад"])

with tabs[0]:
    df = st.session_state.df
    search = st.text_input("🔍 Пошук замовлення...")
    display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df

    for idx, row in display_df.iterrows():
        status = row.get('Готовність', 'В черзі')
        h_class = "header-work" if status == "В роботі" else "header-done" if status == "Готово" else "header-queue"
        
        # 1. ШАПКА КАРТКИ
        st.markdown(f"""
            <div class="order-header {h_class}">
                ⌛ №{row.get('ID')} | {row.get('Дата')} | 👤 {row.get('Клієнт')}
            </div>
        """, unsafe_allow_html=True)
        
        # 2. ТІЛО КАРТКИ
        with st.container():
            st.markdown('<div class="order-body">', unsafe_allow_html=True)
            
            # Статуси чекбоксами
            c1, c2, c3 = st.columns([1, 1, 2])
            is_work = c1.checkbox("🏗️ У виробництво", value=(status == "В роботі"), key=f"w_{idx}")
            is_done = c2.checkbox("✅ Виконано", value=(status == "Готово"), key=f"d_{idx}")
            
            new_st = "Готово" if is_done else "В роботі" if is_work else "В черзі"
            if new_st != status:
                df.at[idx, 'Готовність'] = new_st
                save_data(df); st.rerun()

            st.write("---")
            
            # ТОВАРИ ЯК ТАБЛИЦЯ
            st.markdown("#### 📦 Товари та деталі")
            
            # Десеріалізація товарів
            try:
                items_list = json.loads(row['Товари_JSON']) if row['Товари_JSON'] else []
            except:
                # Конвертація старого формату в новий при першому відкритті
                items_list = [{"назва": row.get('Товари', 'Товар'), "арт": "", "к-ть": 1, "ціна": 0}]
            
            updated_items = []
            total_sum = 0
            
            for i, item in enumerate(items_list):
                col_n, col_a, col_q, col_p, col_t, col_pdf = st.columns([3, 2, 1, 1, 1, 1])
                
                name = col_n.text_input("Назва", value=item.get('назва', ''), key=f"n_{idx}_{i}")
                art = col_a.text_input("Артикул", value=item.get('арт', ''), key=f"a_{idx}_{i}")
                qty = col_q.number_input("К-ть", value=float(item.get('к-ть', 1)), key=f"q_{idx}_{i}")
                price = col_p.number_input("Ціна", value=float(item.get('ціна', 0)), key=f"p_{idx}_{i}")
                
                line_total = qty * price
                total_sum += line_total
                col_t.write(f"**{line_total}**")
                
                if art:
                    link = find_pdf_link(art)
                    if link: col_pdf.link_button("📄 PDF", link)
                
                updated_items.append({"назва": name, "арт": art, "к-ть": qty, "ціна": price})

            if st.button("➕ Додати товар", key=f"add_it_{idx}"):
                updated_items.append({"назва": "", "арт": "", "к-ть": 1, "ціна": 0})
                df.at[idx, 'Товари_JSON'] = json.dumps(updated_items)
                save_data(df); st.rerun()

            st.write("---")
            
            # ФІНАНСИ
            f1, f2, f3 = st.columns(3)
            f1.metric("Загальна сума", f"{total_sum} грн")
            avans = f2.number_input("Аванс", value=float(row.get('Аванс', 0)), key=f"av_{idx}")
            f3.metric("Залишок", f"{total_sum - avans} грн", delta_color="inverse")
            
            comm = st.text_input("Коментар", value=str(row.get('Коментар', '')), key=f"co_{idx}")

            if st.button("💾 Зберегти зміни", key=f"save_{idx}"):
                df.at[idx, 'Товари_JSON'] = json.dumps(updated_items)
                df.at[idx, 'Аванс'] = avans
                df.at[idx, 'Коментар'] = comm
                save_data(df); st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

with tabs[1]:
    st.subheader("📝 Створити нове замовлення")
    with st.form("new_order"):
        c_id = st.text_input("ID замовлення")
        c_cl = st.text_input("Клієнт")
        c_av = st.number_input("Аванс", min_value=0.0)
        if st.form_submit_button("Створити замовлення"):
            new_r = {
                'ID': c_id, 'Дата': datetime.now().strftime("%d.%m.%Y"),
                'Клієнт': c_cl, 'Аванс': c_av, 'Готовність': 'В черзі',
                'Товари_JSON': json.dumps([{"назва": "", "арт": "", "к-ть": 1, "ціна": 0}])
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_r])], ignore_index=True)
            save_data(st.session_state.df); st.rerun()
