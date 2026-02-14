import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def get_val(order, keys):
    """Шукає значення в рядку за списком можливих назв колонок"""
    for key in keys:
        if key in order and pd.notnull(order[key]):
            return order[key]
    return ""

def update_field(order_id, field_mapping, new_value):
    """Автоматично оновлює одне поле в базі на Google Drive"""
    df = load_csv(ORDERS_CSV_ID)
    
    # Визначаємо колонку з ID
    id_col = next((c for c in ['order_id', 'ID', '№', 'id'] if c in df.columns), None)
    
    if id_col:
        # Знаходимо індекс рядка
        idx = df.index[df[id_col].astype(str) == str(order_id)].tolist()
        if idx:
            # Знаходимо реальну назву колонки в CSV для цього поля
            real_col = next((c for c in df.columns if c.lower() in [f.lower() for f in field_mapping]), None)
            
            if real_col:
                # Перевіряємо, чи змінилося значення, щоб не перезаписувати дарма
                if str(df.at[idx[0], real_col]) != str(new_value):
                    df.at[idx[0], real_col] = new_value
                    save_csv(ORDERS_CSV_ID, df)
                    st.toast(f"✅ Оновлено: {real_col}")

def render_order_card(order):
    order_id = str(get_val(order, ['order_id', 'ID', '№', 'id']))
    
    with st.container(border=True):
        # Шапка картки
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"### 📦 Замовлення №{order_id}")
        with col_h2:
            # Статус змінюється через selectbox з автозбереженням
            current_status = get_val(order, ['status', 'Статус'])
            statuses = ["Новий", "В роботі", "Готово", "Видано", "Скасовано"]
            try:
                idx = statuses.index(current_status)
            except ValueError:
                idx = 0
                
            new_status = st.selectbox(
                "Статус", 
                statuses, 
                index=idx, 
                key=f"status_{order_id}",
                on_change=None # Можна додати логіку через callback, але зробимо простіше
            )
            if new_status != current_status:
                update_field(order_id, ['status', 'Статус'], new_status)

        st.divider()

        # Поля для редагування (без кнопок, через text_input)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**👤 КЛІЄНТ**")
            name = st.text_input("ПІБ", value=get_val(order, ['client_name', 'ПІБ']), key=f"name_{order_id}")
            if name != get_val(order, ['client_name', 'ПІБ']):
                update_field(order_id, ['client_name', 'ПІБ'], name)
                
            phone = st.text_input("Телефон", value=get_val(order, ['client_phone', 'Телефон']), key=f"phone_{order_id}")
            if phone != get_val(order, ['client_phone', 'Телефон']):
                update_field(order_id, ['client_phone', 'Телефон'], phone)
            
        with col2:
            st.markdown("**🛠 ТОВАР**")
            product = st.text_input("Назва товару", value=get_val(order, ['product_name', 'Товар']), key=f"prod_{order_id}")
            if product != get_val(order, ['product_name', 'Товар']):
                update_field(order_id, ['product_name', 'Товар'], product)
                
            sku = st.text_input("Артикул", value=get_val(order, ['sku', 'Артикул']), key=f"sku_{order_id}")
            if sku != get_val(order, ['sku', 'Артикул']):
                update_field(order_id, ['sku', 'Артикул'], sku)

        st.divider()

        # Фінансовий блок
        col_f1, col_f2, col_f3 = st.columns(3)
        
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
