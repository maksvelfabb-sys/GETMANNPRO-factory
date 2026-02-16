import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID, get_drive_service

# --- Допоміжні функції для "живого" редагування ---
def update_order_field(order_id, field_name, new_value):
    df = load_csv(ORDERS_CSV_ID)
    id_col = next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')
    
    # Знаходимо потрібний рядок
    idx = df.index[df[id_col].astype(str) == str(order_id)].tolist()
    if idx:
        # Перевіряємо, чи змінилося значення, щоб не перезаписувати диск дарма
        if str(df.at[idx[0], field_name]) != str(new_value):
            df.at[idx[0], field_name] = new_value
            save_csv(ORDERS_CSV_ID, df)
            st.toast(f"💾 {field_name} оновлено")

def render_order_card(order):
    """Малює індивідуальну картку замовлення"""
    oid = str(order.get('order_id') or order.get('ID') or '0')
    
    with st.container(border=True):
        # Заголовок та статус
        h1, h2 = st.columns([3, 1])
        h1.subheader(f"📦 Замовлення №{oid}")
        
        status_options = ["Новий", "В роботі", "Готово", "Видано", "Скасовано"]
        current_status = order.get('status', 'Новий')
        
        new_status = h2.selectbox(
            "Статус", 
            status_options, 
            index=status_options.index(current_status) if current_status in status_options else 0,
            key=f"status_{oid}"
        )
        if new_status != current_status:
            update_order_field(oid, 'status', new_status)

        st.divider()

        # Блок клієнта
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Клієнт", value=str(order.get('client_name', '')), key=f"n_{oid}")
        phone = c2.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"ph_{oid}")
        addr = c3.text_input("Адреса", value=str(order.get('address', '')), key=f"ad_{oid}")
        
        if name != order.get('client_name'): update_order_field(oid, 'client_name', name)
        if phone != order.get('client_phone'): update_order_field(oid, 'client_phone', phone)
        if addr != order.get('address'): update_order_field(oid, 'address', addr)

        # Блок товару
        t1, t2, t3 = st.columns([2, 1, 1])
        prod = t1.text_input("Товар", value=str(order.get('product', '')), key=f"p_{oid}")
        sku = t2.text_input("Артикул", value=str(order.get('sku', '')), key=f"s_{oid}")
        qty = t3.number_input("К-сть", value=int(order.get('qty', 1)), key=f"q_{oid}")
        
        if prod
