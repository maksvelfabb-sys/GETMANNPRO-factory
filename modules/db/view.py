import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID
import webbrowser
from modules.drive_tools import get_drive_service, load_csv, ORDERS_CSV_ID

def find_drawing_file(search_query):
    """Шукає файл у конкретній папці за назвою або артикулом"""
    service = get_drive_service()
    if not service or not search_query:
        return None
    
    folder_id = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"
    # Формуємо запит: шукаємо файл у папці, назва якого містить наш текст
    query = f"'{folder_id}' in parents and name contains '{search_query}' and trashed = false"
    
    try:
        results = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
        files = results.get('files', [])
        return files[0] if files else None
    except Exception:
        return None

def render_order_card(order):
    order_id = str(get_val(order, ['order_id', 'ID', '№', 'id']))
    sku = str(get_val(order, ['sku', 'Артикул']))
    product_name = str(get_val(order, ['product_name', 'Товар']))
    
    with st.container(border=True):
        # ... (верхня частина картки з даними клієнта) ...
        
        st.markdown("**📂 ТЕХНІЧНА ДОКУМЕНТАЦІЯ**")
        
        # Пріоритет пошуку: спочатку по артикулу, якщо немає - по назві
        search_term = sku if sku and sku != "---" else product_name
        drawing_file = find_drawing_file(search_term)
        
        col_d1, col_d2 = st.columns([1, 2])
        
        with col_d1:
            if drawing_file:
                # Якщо файл знайдено - кнопка веде на конкретне креслення
                st.link_button(
                    "📄 Відкрити креслення", 
                    drawing_file['webViewLink'], 
                    type="primary",
                    use_container_width=True
                )
            else:
                # Якщо не знайдено - ведемо в загальну папку
                folder_url = f"https://drive.google.com/drive/folders/1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"
                st.link_button(
                    "📁 Тека креслень", 
                    folder_url, 
                    use_container_width=True
                )
        
        with col_d2:
            if drawing_file:
                st.success(f"Знайдено файл: {drawing_file['name']}")
            else:
                st.warning(f"Файл '{search_term}' не знайдено")

def get_val(order, keys):
    for key in keys:
        if key in order and pd.notnull(order[key]):
            return order[key]
    return ""

def update_field(order_id, field_mapping, new_value):
    df = load_csv(ORDERS_CSV_ID)
    id_col = next((c for c in ['order_id', 'ID', '№', 'id'] if c in df.columns), None)
    if id_col:
        idx = df.index[df[id_col].astype(str) == str(order_id)].tolist()
        if idx:
            real_col = next((c for c in df.columns if c.lower() in [f.lower() for f in field_mapping]), None)
            if real_col:
                if str(df.at[idx[0], real_col]) != str(new_value):
                    df.at[idx[0], real_col] = new_value
                    save_csv(ORDERS_CSV_ID, df)
                    st.toast(f"✅ Оновлено: {real_col}")

def render_order_card(order):
    order_id = str(get_val(order, ['order_id', 'ID', '№', 'id']))
    drawing_link = get_val(order, ['drawing', 'Креслення', 'link'])

    with st.container(border=True):
        # --- Шапка та Статус ---
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"### 📦 Замовлення №{order_id}")
        with col_h2:
            current_status = get_val(order, ['status', 'Статус'])
            new_status = st.selectbox("Статус", ["Новий", "В роботі", "Готово", "Видано"], 
                                     index=0, key=f"st_{order_id}")
            if new_status != current_status:
                update_field(order_id, ['status', 'Статус'], new_status)

        st.divider()

        # --- Клієнт та Товар ---
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("ПІБ", value=get_val(order, ['client_name', 'ПІБ']), key=f"n_{order_id}")
            if name != get_val(order, ['client_name', 'ПІБ']):
                update_field(order_id, ['client_name', 'ПІБ'], name)
        with col2:
            product = st.text_input("Товар", value=get_val(order, ['product_name', 'Товар']), key=f"p_{order_id}")
            if product != get_val(order, ['product_name', 'Товар']):
                update_field(order_id, ['product_name', 'Товар'], product)

        st.divider()

        # --- БЛОК КРЕСЛЕННЯ ---
        st.markdown("**📂 ДОКУМЕНТАЦІЯ**")
        c_draw1, c_draw2 = st.columns([1, 2])
        
        with c_draw1:
            if drawing_link:
                # Якщо посилання є, показуємо кнопку "Відкрити"
                st.link_button("🏗️ Відкрити креслення", drawing_link, use_container_width=True)
            else:
                st.warning("Креслення відсутнє")
        
        with c_draw2:
            # Поле для додавання/редагування посилання на креслення
            new_link = st.text_input("Посилання на файл (Google Drive/Cloud)", 
                                    value=drawing_link, 
                                    placeholder="Вставте посилання тут...",
                                    key=f"link_{order_id}")
            if new_link != drawing_link:
                update_field(order_id, ['drawing', 'Креслення', 'link'], new_link)

        st.divider()

        # --- Фінанси ---
        f1, f2, f3 = st.columns(3)
        total = f1.number_input("Сума", value=float(get_val(order, ['total_amount', 'Сума']) or 0), key=f"t_{order_id}")
        pre = f2.number_input("Аванс", value=float(get_val(order, ['prepayment', 'Аванс']) or 0), key=f"pr_{order_id}")
        f3.metric("Доплата", f"{total - pre} грн")

        # Перевірка змін фінансів
        if total != float(get_val(order, ['total_amount', 'Сума']) or 0):
            update_field(order_id, ['total_amount', 'Сума'], total)
        if pre != float(get_val(order, ['prepayment', 'Аванс']) or 0):
            update_field(order_id, ['prepayment', 'Аванс'], pre)
        
        total = st.number_input("Загальна сума", value=float(get_val(order, ['total_amount', 'Сума']) or 0), key=f"total_{order_id}")
        if total != float(get_val(order, ['total_amount', 'Сума']) or 0):
            update_field(order_id, ['total_amount', 'Сума'], total)
            
        pre = st.number_input("Аванс", value=float(get_val(order, ['prepayment', 'Аванс']) or 0), key=f"pre_{order_id}")
        if pre != float(get_val(order, ['prepayment', 'Аванс']) or 0):
            update_field(order_id, ['prepayment', 'Аванс'], pre)
            
        balance = total - pre
        st.write(f"**Залишок (доплата):** :red[{balance} грн]")

def show_order_cards():
    st.title("📋 Живе редагування замовлень")
    
    # Використовуємо кешування, щоб сторінка не стрибала при кожному введенні символу
    df_orders = load_csv(ORDERS_CSV_ID)
    
    if not df_orders.empty:
        for _, row in df_orders.iterrows():
            render_order_card(row)
    else:
        st.info("Замовлень не знайдено.")
