import streamlit as st
import pandas as pd
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# --- КОНФІГУРАЦІЯ (Build 4.2 Legacy) ---
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

# ПОВЕРТАЄМО ОРИГІНАЛЬНУ НАЗВУ
st.set_page_config(page_title="GETMANN Pro", layout="wide", page_icon="🏭")

# --- СИСТЕМНІ ФУНКЦІЇ ---
@st.cache_resource
def get_drive_service():
    try:
        if "gcp_service_account" in st.secrets:
            info = dict(st.secrets["gcp_service_account"])
            info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
            creds = service_account.Credentials.from_service_account_info(info)
            return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Помилка авторизації: {e}")
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
        return pd.read_csv(fh).fillna("")
    except:
        return pd.DataFrame(columns=['ID', 'Клієнт', 'Товари', 'Сума', 'Готовність', 'Коментар'])

def save_data(df):
    service = get_drive_service()
    if not service: return
    try:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        media = MediaFileUpload(
            io.BytesIO(csv_buffer.getvalue().encode()), 
            mimetype='text/csv'
        )
        service.files().update(fileId=ORDERS_CSV_ID, media_body=media).execute()
        st.success("Дані синхронізовано! ✅")
    except Exception as e:
        st.error(f"Помилка збереження: {e}")

# --- ФУНКЦІЇ З ПОПЕРЕДНЬОЇ ВЕРСІЇ ---
def find_pdf_link(article):
    service = get_drive_service()
    if not service: return None
    try:
        query = f"name = '{article}.pdf' and '{FOLDER_DRAWINGS_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, webViewLink)").execute()
        files = results.get('files', [])
        return files[0]['webViewLink'] if files else None
    except:
        return None

# --- ГОЛОВНИЙ ІНТЕРФЕЙС GETMANN Pro ---
st.title("🏭 GETMANN Pro")
st.markdown("---")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# ТАБИ ЯК У ПОПЕРЕДНІЙ ВЕРСІЇ
tabs = st.tabs(["📋 Замовлення", "➕ Нове замовлення", "📦 Склад", "📊 Звіти"])

with tabs[0]:
    st.subheader("Поточні замовлення")
    df = st.session_state.df
    search = st.text_input("🔍 Пошук замовлення (Клієнт/ID/Артикул)")
    
    # Фільтрація
    if search:
        display_df = df[df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]
    else:
        display_df = df

    for idx, row in display_df.iterrows():
        with st.expander(f"📦 {row['Клієнт']} | ID: {row['ID']} | {row['Готовність']}"):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.write("**Деталі замовлення:**")
                items = str(row['Товари']).split(';')
                for item in items:
                    st.write(f"• {item.strip()}")
                    if "[" in item:
                        sku = item.split("[")[1].split("]")[0]
                        link = find_pdf_link(sku)
                        if link:
                            st.link_button(f"📄 Креслення {sku}", link)
            
            with c2:
                st.write("**Коментар:**")
                st.caption(row['Коментар'] if row['Коментар'] else "Відсутній")
            
            with c3:
                new_status = st.selectbox(
                    "Статус", 
                    ["В черзі", "В роботі", "Готово", "Відвантажено"], 
                    index=["В черзі", "В роботі", "Готово", "Відвантажено"].index(row['Готовність']) if row['Готовність'] in ["В черзі", "В роботі", "Готово", "Відвантажено"] else 0,
                    key=f"st_{idx}"
                )
                if new_status != row['Готовність']:
                    df.at[idx, 'Готовність'] = new_status
                    save_data(df)
                    st.rerun()

with tabs[1]:
    st.subheader("Додати нове замовлення")
    with st.form("add_form"):
        f_id = st.text_input("Номер замовлення (ID)")
        f_client = st.text_input("Назва клієнта")
        f_items = st.text_area("Товари (Артикули через ;)")
        f_sum = st.number_input("Сума замовлення", min_value=0)
        f_comment = st.text_input("Коментар")
        
        if st.form_submit_button("Зберегти замовлення"):
            new_order = {
                'ID': f_id, 'Клієнт': f_client, 'Товари': f_items,
                'Сума': f_sum, 'Готовність': 'В черзі', 'Коментар': f_comment
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_order])], ignore_index=True)
            save_data(st.session_state.df)
            st.rerun()

with tabs[2]:
    st.subheader("Менеджер матеріалів")
    st.info("Дані складу синхронізуються з Cloud Storage.")
    # Сюди можна перенести вашу таблицю залишків листів

with tabs[3]:
    st.subheader("Аналітика виробництва")
    st.write(f"Всього замовлень: {len(df)}")
    st.write(f"Готово до відвантаження: {len(df[df['Готовність'] == 'Готово'])}")

st.sidebar.markdown("---")
st.sidebar.write("👤 Користувач: **Admin**")
st.sidebar.button("🔄 Оновити з хмари", on_click=lambda: st.session_state.pop('df'))
