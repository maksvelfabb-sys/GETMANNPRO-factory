import streamlit as st
import pandas as pd
import json
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID, get_file_link_by_name

def get_id_column_name(df):
    """Визначає назву колонки ID у таблиці"""
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

def render_order_card(order):
    """Рендерить одну картку замовлення"""
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    # Створюємо контейнер для картки
    card = st.container(border=True)
    
    # Заголовок (Колонка 1: №, 2: Дата, 3: Клієнт, 4: Сума)
    head_cols = card.columns([0.6, 1, 2, 1])
    head_cols[0].markdown(f"### №{oid}")
    head_cols[1].caption(f"📅 {order.get('date', '---')}")
    head_cols[2].markdown(f"👤 **{order.get('client_name', '---')}**")
    head_cols[3].markdown(f"💰 **{order.get('total', 0)} грн**")

    with card.expander("📝 Деталі замовлення та Креслення"):
        # Поля редагування основної інформації
        c1, c2 = st.columns(2)
        f_name = c1.text_input("ПІБ Клієнта", value=str(order.get('client_name', '')), key=f"name_{oid}")
        f_phone = c2.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"phone_{oid}")
        f_addr = st.text_input("Адреса доставки", value=str(order.get('address', '')), key=f"addr_{oid}")
        
        st.divider()

        # Робота зі списком товарів (JSON)
        st.markdown("##### 📦 Склад замовлення")
        raw_items = order.get('items_json', '[]')
        try:
            items_list = json.loads(raw_items) if isinstance(raw_items, str) and raw_items.startswith('[') else []
        except:
            items_list = []
            
        if not items_list:
            items_list = [{"Товар": str(order.get
