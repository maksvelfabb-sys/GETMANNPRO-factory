import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, get_drive_service, ORDERS_CSV_ID

# Константа для папки з кресленнями
DRAWINGS_FOLDER_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

def find_drawing_file(search_query):
    """Шукає файл у конкретній папці на Google Drive за назвою або артикулом"""
    service = get_drive_service()
    if not service or not search_query or search_query == "---":
        return None
    
    # Запит: шукаємо файл у папці, назва якого містить наш текст
    query = f"'{DRAWINGS_FOLDER_ID}' in parents and name contains '{search_query}' and trashed = false"
    
    try:
        results = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
        files = results.get('files', [])
        return files[0] if files else None
    except Exception:
        return None

def get_val(order, keys):
    """Універсальний отримувач значень з рядка за списком можливих ключів"""
    for key in keys:
        if key in order and pd.notnull(order[key]):
            return order[key]
    return ""

def update_field(order_id, field_mapping, new_value):
    """Автоматичне збереження змін у Google CSV"""
    df = load_csv(ORDERS_CSV_ID)
    id_col = next((c for c in ['order_id', 'ID', '№', 'id'] if c in df.columns), None)
    
    if id_col:
        idx = df.index[df[id_col].astype(str) == str(order_id)].tolist()
        if idx:
            # Знаходимо реальну назву колонки в файлі
            real_col = next((c for c in df.columns if c.lower() in [f.lower() for f in field_mapping]), None)
            if real_col:
                # Зберігаємо лише якщо значення змінилося
                if str(df.at[idx[0], real_col]) != str(new_value):
                    df.at[idx[0], real_col] = new_value
                    save_csv(ORDERS_CSV_ID, df)
                    st.toast(f"✅ Оновлено: {real_col}")

def render_order_card(order):
    """Відображення картки замовлення з живим редагуванням та автопошуком креслень"""
    order_id = str(get_val(order, ['order_id', 'ID', '№', 'id']))
    sku = str(get_val(order, ['sku', 'Артикул']))
    product_name = str(get_val(order, ['product_name', 'Товар']))
    drawing_link = get_val(order, ['drawing', 'Креслення', 'link'])

    with st.container(border=True):
        # --- Шапка та Статус ---
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"### 📦 Замовлення №{order_id}")
        with col_h2:
            current_status = get_val(order, ['status', 'Статус'])
            statuses = ["Новий", "В роботі", "Готово", "Видано", "Скасовано"]
            try:
                st_idx = statuses.index(current_status) if current_status in statuses else 0
            except: st_idx = 0
            
            new_status = st.selectbox("Статус", statuses, index=st_idx, key=f"st_{order_id}")
            if new_status != current_status:
                update_field(order_id, ['status', 'Статус'], new_status)

        st.divider()

        # --- Клієнт та Товар ---
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**👤 КЛІЄНТ**")
            name = st.text_input("ПІБ", value=get_val(order, ['client_name', 'ПІБ']), key=f"n_{order_id}")
            if name != get_val(order, ['client_name', 'ПІБ']):
                update_field(order_id, ['client_name', 'ПІБ'], name)
                
            phone = st.text_input("Телефон", value=get_val(order, ['client_phone', 'Телефон']), key=f"ph_{order_id}")
            if phone != get_val(order, ['client_phone', 'Телефон']):
                update_field(order_id, ['client_phone', 'Телефон'], phone)
        
        with col2:
            st.markdown("**🛠 ТОВАР**")
            prod = st.text_input("Назва товару", value=product_name, key=f"p_{order_id}")
            if prod != product_name:
                update_field(order_id, ['product_name', 'Товар'], prod)
                
            current_sku = st.text_input("Артикул", value=sku, key=f"s_{order_id}")
            if current_sku != sku:
                update_field(order_id, ['sku', 'Артикул'], current_sku)

        st.divider()

        # --- БЛОК КРЕСЛЕННЯ (АВТОПОШУК) ---
        st.markdown("**📂 ТЕХНІЧНА ДОКУМЕНТАЦІЯ**")
        
        # Шукаємо файл за артикулом або назвою
        search_term = current_sku if current_sku and current_sku != "---" else prod
        found_file = find_drawing_file(search_term)
        
        c_draw1, c_draw2 = st.columns([1, 2])
        with c_draw1:
            if found_file:
                st.link_button("📄 Відкрити креслення", found_file['webViewLink'], type="primary", use_container_width=True)
            elif drawing_link:
                st.link_button("🏗️ Посилання в базі", drawing_link, use_container_width=True)
            else:
                folder_url = f"https://drive.google.com/drive/folders/{DRAWINGS_FOLDER_ID}"
                st.link_button("📁 Тека креслень", folder_url, use_container_width=True)
        
        with c_draw2:
            # Можливість вручну вставити посилання, якщо автопошук не знайшов
            new_link = st.text_input("Вставити посилання вручну", value=drawing_link, key=f"link_{order_id}", placeholder="https://drive.google.com/...")
            if new_link != drawing_link:
                update_field(order_id, ['drawing', 'Креслення', 'link'], new_link)
            if found_file:
                st.caption(f"✅ Автоматично знайдено: {found_file['name']}")

        st.divider()

        # --- ФІНАНСИ ---
        st.markdown("**💰 ФІНАНСОВИЙ ОБЛІК**")
        f1, f2, f3 = st.columns(3)
        
        current_total = float(get_val(order, ['total_amount', 'Сума']) or 0)
        current_pre = float(get_val(order, ['prepayment', 'Аванс']) or 0)
        
        total = f1.number_input("Загальна сума", value=current_total, key=f"t_{order_id}")
        pre = f2.number_input("Аванс", value=current_pre, key=f"pr_{order_id}")
        
        if total != current_total:
            update_field(order_id, ['total_amount', 'Сума'], total)
        if pre != current_pre:
            update_field(order_id, ['prepayment', 'Аванс'], pre)
            
        balance = total - pre
        f3.metric("Залишок (доплата)", f"{balance} грн", delta=f"-{pre}" if pre > 0 else None, delta_color="inverse")

def show_order_cards():
    st.title("📋 Панель управління замовленнями")
    
    df_orders = load_csv(ORDERS_CSV_ID)
    
    if not df_orders.empty:
        # Можна додати пошук по всім карткам
        search = st.text_input("🔍 Швидкий пошук (ПІБ або №)", "")
        
        for _, row in df_orders.iterrows():
            # Проста фільтрація для зручності
            if search.lower() in str(row).lower():
                render_order_card(row)
    else:
        st.info("Замовлень не знайдено.")
