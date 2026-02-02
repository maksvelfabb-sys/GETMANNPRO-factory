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
    .order-header {
        padding: 12px; border-radius: 8px; color: white; font-weight: bold;
        margin-bottom: 5px; display: flex; justify-content: space-between;
    }
    .header-work { background-color: #007bff; }
    .header-done { background-color: #28a745; }
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
        
        # Перевірка наявності необхідних колонок
        required = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']
        for col in required:
            if col not in df.columns: df[col] = ""
            
        return df
    except Exception as e:
        st.error(f"Помилка завантаження: {e}")
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

tab_j, tab_n = st.tabs(["📋 Журнал", "➕ Нове замовлення"])

with tab_j:
    df = st.session_state.df
    search = st.text_input("🔍 Пошук...")
    display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)] if search else df

    for idx, row in display_df.iterrows():
        status = str(row.get('Готовність', 'В черзі'))
        h_color = "header-work" if status == "В роботі" else "header-done" if status == "Готово" else "header-queue"
        
        st.markdown(f'<div class="order-header {h_color}"><span>⌛ №{row["ID"]} | {row["Клієнт"]}</span><span>{status}</span></div>', unsafe_allow_html=True)
        
        with st.expander("Деталі"):
            # Статуси
            c1, c2, _ = st.columns([1, 1, 2])
            is_w = c1.checkbox("🏗️ Робота", value=(status == "В роботі"), key=f"sw_{idx}")
            is_d = c2.checkbox("✅ Готово", value=(status == "Готово"), key=f"sd_{idx}")
            
            new_st = "Готово" if is_d else "В роботі" if is_w else "В черзі"
            if new_st != status:
                df.at[idx, 'Готовність'] = new_st
                save_data(df); st.rerun()

            st.divider()

            # ТОВАРИ ТА МАТЕМАТИКА
            try:
                raw_json = row.get('Товари_JSON', '[]')
                items = json.loads(raw_json) if raw_json and "[" in raw_json else []
            except: items = []

            if not items:
                items = [{"назва": "Товар", "арт": "", "к-ть": 1, "ціна": 0.0}]

            new_items = []
            total = 0.0

            h1, h2, h3, h4, h5, h6 = st.columns([3, 2, 1, 1.5, 1.5, 0.5])
            h1.caption("Назва"); h2.caption("Арт"); h3.caption("К-ть"); h4.caption("Ціна"); h5.caption("Сума")

            for i, item in enumerate(items):
                col_n, col_a, col_q, col_p, col_s, col_pdf = st.columns([3, 2, 1, 1.5, 1.5, 0.5])
                
                n = col_n.text_input("N", value=item.get('назва', ''), key=f"n_{idx}_{i}", label_visibility="collapsed")
                a = col_a.text_input("A", value=item.get('арт', ''), key=f"a_{idx}_{i}", label_visibility="collapsed")
                q = col_q.number_input("Q", value=int(item.get('к-ть', 1)), step=1, key=f"q_{idx}_{i}", label_visibility="collapsed")
                p = col_p.number_input("P", value=float(item.get('ціна', 0.0)), key=f"p_{idx}_{i}", label_visibility="collapsed")
                
                s = q * p
                total += s
                col_s.write(f"**{s}**")
                
                if a:
                    link = find_pdf_link(a)
                    if link: col_pdf.link_button("📄", link)
                
                new_items.append({"назва": n, "арт": a, "к-ть": q, "ціна": p})

            if st.button("➕ Додати товар", key=f"add_{idx}"):
                new_items.append({"назва": "", "арт": "", "к-ть": 1, "ціна": 0.0})
                df.at[idx, 'Товари_JSON'] = json.dumps(new_items)
                save_data(df); st.rerun()

            st.divider()

            # ФІНАНСИ
            f1, f2, f3 = st.columns(3)
            f1.metric("Сума", f"{total} грн")
            avans = f2.number_input("Аванс", value=float(row.get('Аванс', 0.0)), key=f"av_{idx}")
            f3.metric("Залишок", f"{total - avans} грн")

            # ЗБЕРЕЖЕННЯ
            if st.button("💾 ЗБЕРЕГТИ ВСЕ", key=f"btn_{idx}", use_container_width=True, type="primary"):
                df.at[idx, 'Товари_JSON'] = json.dumps(new_items)
                df.at[idx, 'Аванс'] = avans
                df.at[idx, 'Телефон'] = st.session_state.get(f"ph_{idx}", row.get('Телефон'))
                df.at[idx, 'Місто'] = st.session_state.get(f"ct_{idx}", row.get('Місто'))
                save_data(df); st.rerun()

with tab_n:
    with st.form("new"):
        n_id = st.text_input("№")
        n_cl = st.text_input("Клієнт")
        if st.form_submit_button("Створити"):
            new_r = {'ID': n_id, 'Дата': datetime.now().strftime("%d.%m.%Y"), 'Клієнт': n_cl, 'Готовність': 'В черзі', 'Товари_JSON': '[]', 'Аванс': 0.0}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_r])], ignore_index=True)
            save_data(st.session_state.df); st.rerun()
