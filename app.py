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
    .status-header {
        padding: 12px; border-radius: 8px; color: white; font-weight: bold;
        margin-bottom: 5px; display: flex; justify-content: space-between;
    }
    .header-work { background-color: #007bff; }
    .header-done { background-color: #28a745; }
    .header-queue { background-color: #444; }
    .metric-box { background-color: #262730; padding: 10px; border-radius: 5px; border: 1px solid #444; }
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
        st.toast("Дані синхронізовано ✅")
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

tabs = st.tabs(["📋 Замовлення", "➕ Створити", "⚙️ База"])

with tabs[0]:
    df = st.session_state.df
    search = st.text_input("🔍 Пошук...")
    display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df

    for idx, row in display_df.iterrows():
        status = row.get('Готовність', 'В черзі')
        h_color = "header-work" if status == "В роботі" else "header-done" if status == "Готово" else "header-queue"
        
        st.markdown(f'<div class="status-header {h_color}"><span>⌛ №{row["ID"]} | {row["Клієнт"]}</span><span>{status}</span></div>', unsafe_allow_html=True)
        
        with st.expander("Відкрити замовлення"):
            # Керування статусом
            c1, c2, _ = st.columns([1, 1, 2])
            is_work = c1.checkbox("🏗️ В роботі", value=(status == "В роботі"), key=f"st_w_{idx}")
            is_done = c2.checkbox("✅ Виконано", value=(status == "Готово"), key=f"st_d_{idx}")
            
            new_st = "Готово" if is_done else "В роботі" if is_work else "В черзі"
            if new_st != status:
                df.at[idx, 'Готовність'] = new_st
                save_data(df); st.rerun()

            st.write("---")
            
            # ТОВАРИ
            st.markdown("#### 📦 Склад замовлення")
            try:
                items = json.loads(row['Товари_JSON']) if row['Товари_JSON'] else []
            except:
                items = [{"назва": "Товар", "арт": "", "к-ть": 1, "ціна": 0}]

            updated_items = []
            total_order_sum = 0

            # Заголовки
            h1, h2, h3, h4, h5, h6 = st.columns([3, 2, 1, 1.5, 1.5, 0.5])
            h1.caption("Назва"); h2.caption("Артикул"); h3.caption("К-ть"); h4.caption("Ціна за од."); h5.caption("Сума")

            for i, item in enumerate(items):
                col_n, col_a, col_q, col_p, col_s, col_pdf = st.columns([3, 2, 1, 1.5, 1.5, 0.5])
                
                i_name = col_n.text_input("N", value=item.get('назва', ''), key=f"n_{idx}_{i}", label_visibility="collapsed")
                i_art = col_a.text_input("A", value=item.get('арт', ''), key=f"a_{idx}_{i}", label_visibility="collapsed")
                i_qty = col_q.number_input("Q", value=int(item.get('к-ть', 1)), step=1, key=f"q_{idx}_{i}", label_visibility="collapsed")
                i_price = col_p.number_input("P", value=float(item.get('ціна', 0)), key=f"p_{idx}_{i}", label_visibility="collapsed")
                
                # РОЗРАХУНОК СУМИ РЯДКА
                i_sum = i_qty * i_price
                total_order_sum += i_sum
                col_s.write(f"**{i_sum} грн**")
                
                if i_art:
                    link = find_pdf_link(i_art)
                    if link: col_pdf.link_button("📄", link)
                
                updated_items.append({"назва": i_name, "арт": i_art, "к-ть": i_qty, "ціна": i_price})

            if st.button("➕ Додати позицію", key=f"add_{idx}"):
                updated_items.append({"назва": "", "арт": "", "к-ть": 1, "ціна": 0})
                df.at[idx, 'Товари_JSON'] = json.dumps(updated_items)
                save_data(df); st.rerun()

            st.write("---")

            # ФІНАНСИ
            f1, f2, f3 = st.columns(3)
            with f1:
                st.markdown(f"**Загальна сума:** \n### {total_order_sum} грн")
            with f2:
                avans = st.number_input("Внесено аванс, грн", value=float(row.get('Аванс', 0)), key=f"av_{idx}")
            with f3:
                debt = total_order_sum - avans
                color = "green" if debt <= 0 else "red"
                st.markdown(f"**Залишок до оплати:** \n<h3 style='color:{color};'>{debt} грн</h3>", unsafe_allow_html=True)

            # ДАНІ КЛІЄНТА
            c_ph, c_ct = st.columns(2)
            u_phone = c_ph.text_input("📞 Телефон", value=str(row.get('Телефон', '')), key=f"ph_{idx}")
            u_city = c_ct.text_input("📍 Місто / Відділення", value=str(row.get('Місто', '')), key=f"ct_{idx}")
            u_comm = st.text_area("💬 Коментар", value=str(row.get('Коментар', '')), key=f"co_{idx}", height=100)

            if st.button("💾 Зберегти всі зміни замовлення", key=f"btn_{idx}", use_container_width=True, type="primary"):
                df.at[idx, 'Товари_JSON'] = json.dumps(updated_items)
                df.at[idx, 'Аванс'] = avans
                df.at[idx, 'Телефон'] = u_phone
                df.at[idx, 'Місто'] = u_city
                df.at[idx, 'Коментар'] = u_comm
                save_data(df); st.rerun()

with tabs[1]:
    st.subheader("🆕 Створення замовлення")
    with st.form("new_order"):
        n_id = st.text_input("Номер замовлення")
        n_cl = st.text_input("ПІБ Клієнта")
        n_ph = st.text_input("Телефон")
        n_av = st.number_input("Аванс", min_value=0, step=100)
        if st.form_submit_button("Створити замовлення"):
            new_r = {
                'ID': n_id, 'Дата': datetime.now().strftime("%d.%m.%Y"),
                'Клієнт': n_cl, 'Телефон': n_ph, 'Аванс': n_av, 'Готовність': 'В черзі',
                'Товари_JSON': json.dumps([{"назва": "", "арт": "", "к-ть": 1, "ціна": 0}])
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_r])], ignore_index=True)
            save_data(st.session_state.df); st.rerun()
