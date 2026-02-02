import streamlit as st
import pandas as pd
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# --- КОНФІГУРАЦІЯ (Ваші ID) ---
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"  # Папка з PDF
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"      # Файл orders.csv

st.set_page_config(
    page_title="Factory CRM | Build 4.0",
    page_icon="🏭",
    layout="wide"
)

# --- ПІДКЛЮЧЕННЯ ДО GOOGLE DRIVE ---
@st.cache_resource
def get_drive_service():
    """Авторизація: примусове лікування PEM-файлу ключа"""
    try:
        if "gcp_service_account" in st.secrets:
            # Створюємо словник із налаштувань Secrets
            info = dict(st.secrets["gcp_service_account"])
            
            # ВИПРАВЛЕННЯ КЛЮЧА (PEM format fix):
            # Видаляємо зайві пробіли та виправляємо екрановані переноси рядків
            key = info["private_key"].strip().replace("\\n", "\n")
            
            # Якщо ключ випадково обгорнутий у зайві лапки після копіювання
            if key.startswith('"') and key.endswith('"'):
                key = key[1:-1]
                
            info["private_key"] = key
            
            creds = service_account.Credentials.from_service_account_info(info)
            return build('drive', 'v3', credentials=creds)
        else:
            st.error("Ключі авторизації не знайдено в Streamlit Secrets!")
            return None
    except Exception as e:
        st.error(f"Помилка авторизації Google: {e}")
        return None

def load_data():
    """Завантаження бази замовлень CSV з Google Drive"""
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
        # Спробуємо прочитати CSV, ігноруючи можливі помилки форматування рядків
        df = pd.read_csv(fh, on_bad_lines='skip')
        
        if 'Дата' in df.columns:
            df['Дата'] = pd.to_datetime(df['Дата'], errors='coerce').dt.date
        return df
    except Exception as e:
        st.error(f"Не вдалося зчитати CSV: {e}")
        return pd.DataFrame()

def find_pdf_link(article):
    """Пошук посилання на PDF у папці креслень"""
    service = get_drive_service()
    if not service: return None
    
    try:
        query = f"name = '{article}.pdf' and '{FOLDER_DRAWINGS_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, webViewLink)").execute()
        files = results.get('files', [])
        return files[0]['webViewLink'] if files else None
    except:
        return None

# --- ЛОГІКА РОЗШИФРОВКИ АРТИКУЛА ---
def decode_sku(sku):
    """Парсинг: 40(товщина)WSF(тип).FA6(матеріал)"""
    try:
        sku = str(sku).strip()
        thickness = sku[:2]
        type_code = sku[2:5]
        
        material = "Стандарт"
        if "FA6" in sku:
            material = "Алюміній (FA6)"
        elif "ST" in sku:
            material = "Сталь"
            
        return f"📏 {thickness}мм | 🏗️ {type_code} | 🧪 {material}"
    except:
        return "⚙️ Параметри не визначено"

# --- ІНТЕРФЕЙС ---
st.title("🏭 Factory CRM — Build 4.0")

# Перевірка та завантаження даних
if 'orders_df' not in st.session_state:
    st.session_state.orders_df = load_data()

# Кнопка оновлення
if st.button("🔄 Оновити дані з Google Диску"):
    st.session_state.orders_df = load_data()
    st.rerun()

df = st.session_state.orders_df

if df.empty:
    st.info("База замовлень порожня або очікує підключення...")
else:
    # Пошук
    search = st.text_input("🔍 Швидкий пошук (Клієнт або Артикул)", "")
    
    # Спрощена фільтрація
    if search:
        mask = df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)
        display_df = df[mask]
    else:
        display_df = df

    for idx, row in display_df.iterrows():
        client = row.get('Клієнт', 'Невідомо')
        order_id = row.get('ID', idx)
        
        with st.expander(f"📦 Замовлення №{order_id} — {client}"):
            c1, c2 = st.columns([3, 1])
            
            with c1:
                st.write(f"**Коментар:** {row.get('Коментар', '—')}")
                st.write("**Товари:**")
                
                # Парсинг товарів із рядка (розділювач ;)
                items = str(row.get('Товари', '')).split(';')
                for item in items:
                    item = item.strip()
                    if "[" in item and "]" in item:
                        try:
                            sku = item.split("[")[1].split("]")[0]
                            st.markdown(f"✅ **{item}**")
                            st.caption(decode_sku(sku))
                            
                            link = find_pdf_link(sku)
                            if link:
                                st.link_button(f"📄 Відкрити креслення {sku}", link)
                            else:
                                st.caption("📂 Креслення в папці не знайдено")
                        except:
                            st.write(f"• {item}")
                    elif item:
                        st.write(f"• {item}")
            
            with c2:
                st.metric("Сума", f"{row.get('Сума', 0)} грн")
                st.info(f"Статус: {row.get('Готовність', 'В черзі')}")

st.sidebar.markdown(f"**Версія:** 4.0 Stable")
st.sidebar.write("Підключено до Google Drive ✅")
