import streamlit as st
import pandas as pd
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# --- НАЛАШТУВАННЯ (Build 4.0) ---
# Ці ID отримані з ваших посилань на Google Диск
FOLDER_DRAWINGS_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"  # Папка з PDF
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"      # Файл orders.csv

st.set_page_config(
    page_title="GETMANN Pro | Build 4.0",
    page_icon="🏭",
    layout="wide"
)

# --- ПІДКЛЮЧЕННЯ ДО GOOGLE DRIVE ---
@st.cache_resource
def get_drive_service():
    try:
        if "gcp_service_account" in st.secrets:
            # Створюємо копію словника з Secrets
            info = dict(st.secrets["gcp_service_account"])
            
            # ВИПРАВЛЕННЯ КЛЮЧА:
            # Прибираємо зайві лапки та виправляємо екрановані переноси рядків
            key = info["private_key"].replace("\\n", "\n").strip()
            # Якщо ключ загорнутий у подвійні лапки всередині рядка — прибираємо їх
            if key.startswith('"') and key.endswith('"'):
                key = key[1:-1]
            info["private_key"] = key
            
            creds = service_account.Credentials.from_service_account_info(info)
        else:
            # Для локальної розробки
            import json
            with open("service_account.json") as f:
                info = json.load(f)
            creds = service_account.Credentials.from_service_account_info(info)
            
        return build('drive', 'v3', credentials=creds)
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
        df = pd.read_csv(fh)
        
        # Базова обробка дат, якщо вони є
        if 'Дата' in df.columns:
            df['Дата'] = pd.to_datetime(df['Дата'], errors='coerce').dt.date
        return df
    except Exception as e:
        st.error(f"Не вдалося зчитати CSV: {e}")
        return pd.DataFrame()

def find_pdf_link(article):
    """Пошук прямого посилання на PDF креслення за артикулом"""
    service = get_drive_service()
    if not service: return None
    
    try:
        # Шукаємо файл, де назва дорівнює Артикул.pdf у конкретній папці
        query = f"name = '{article}.pdf' and '{FOLDER_DRAWINGS_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, webViewLink)").execute()
        files = results.get('files', [])
        return files[0]['webViewLink'] if files else None
    except:
        return None

# --- ЛОГІКА РОЗШИФРОВКИ АРТИКУЛА ---
def decode_sku(sku):
    """Парсинг за правилом: 40(товщина)WSF(тип).FA6(матеріал)"""
    try:
        sku = str(sku).strip()
        thickness = sku[:2]  # Перші дві цифри
        type_code = sku[2:5] # Наступні три літери
        
        material = "Стандарт"
        if "FA6" in sku:
            material = "Алюміній (FA6)"
        elif "ST" in sku:
            material = "Сталь"
            
        return f"📏 {thickness}мм | 🏗️ {type_code} | 🧪 {material}"
    except:
        return "⚙️ Специфікація не визначена"

# --- ОСНОВНИЙ ІНТЕРФЕЙС ---
st.title("🏭 Factory CRM — Build 4.0")
st.subheader("Система автоматичного пошуку креслень")

# Стан додатка
if 'orders_df' not in st.session_state:
    with st.spinner('Завантаження бази даних...'):
        st.session_state.orders_df = load_data()

# Кнопки керування
col_actions, _ = st.columns([1, 4])
if col_actions.button("🔄 Оновити дані з Google Диску"):
    st.session_state.orders_df = load_data()
    st.rerun()

# Відображення списку замовлень
df = st.session_state.orders_df

if df.empty:
    st.warning("База замовлень порожня або відсутній доступ до файлу CSV.")
else:
    # Пошук по таблиці
    search_query = st.text_input("🔍 Пошук за клієнтом або ID", "")
    
    # Фільтрація (спрощена)
    if search_query:
        mask = df.apply(lambda r: search_query.lower() in str(r.values).lower(), axis=1)
        display_df = df[mask]
    else:
        display_df = df

    for idx, row in display_df.iterrows():
        client_name = row.get('Клієнт', 'Невідомий клієнт')
        order_id = row.get('ID', idx)
        
        with st.expander(f"📦 Замовлення №{order_id} — {client_name}"):
            c1, c2 = st.columns([3, 1])
            
            with c1:
                st.write(f"**Коментар:** {row.get('Коментар', '—')}")
                st.write("**Товари у замовленні:**")
                
                # Розбиваємо товари (формат: Назва [АРТИКУЛ] (К-сть))
                items_list = str(row.get('Товари', '')).split(';')
                for item in items_list:
                    if "[" in item and "]" in item:
                        try:
                            item_name = item.split(" [")[0]
                            sku = item.split("[")[1].split("]")[0]
                            
                            st.markdown(f"✅ **{item_name}** `[{sku}]`")
                            st.caption(decode_sku(sku))
                            
                            # Кнопка креслення
                            link = find_pdf_link(sku)
                            if link:
                                st.link_button(f"📄 Відкрити PDF ({sku})", link)
                            else:
                                st.caption("❌ Креслення не знайдено в папці")
                        except:
                            st.write(f"• {item}")
                    else:
                        if item.strip(): st.write(f"• {item}")
            
            with c2:
                st.metric("Сума", f"{row.get('Сума', 0)} грн")
                st.info(f"Статус: {row.get('Готовність', 'В черзі')}")

# --- БОКОВА ПАНЕЛЬ ---
st.sidebar.image("https://via.placeholder.com/150?text=FACTORY", width=100)
st.sidebar.markdown("---")
st.sidebar.write("**Build 4.0 Stable**")
st.sidebar.write("Хмарна версія")



