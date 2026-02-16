import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

# --- 1. ДОПОМІЖНА ФУНКЦІЯ ДЛЯ ПОШУКУ ID КОЛОНКИ ---
def get_id_column_name(df):
    """Шукає назву колонки ID у датафреймі"""
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

# --- 2. ФУНКЦІЯ ОНОВЛЕННЯ СТАТУСУ (ШВИДКА) ---
def update_order_status(order_id, new_status):
    """Оновлює тільки статус замовлення"""
    df = load_csv(ORDERS_CSV_ID)
    id_col = get_id_column_name(df)
    
    idx = df.index[df[id_col].astype(str) == str(order_id)].tolist()
    if idx:
        if df.at[idx[0], 'status'] != new_status:
            df.at[idx[0], 'status'] = new_status
            save_csv(ORDERS_CSV_ID, df)
            st.toast(f"✅ Статус №{order_id} змінено на {new_status}")

# --- 3. РЕНДЕР КАРТКИ ЗАМОВЛЕННЯ ---
def render_order_card(order):
    """Створює картку з полями редагування"""
    # Отримуємо ID для поточного рендеру
    id_col_current = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col_current, '0'))
    
    with st.container(border=True):
        # Заголовок
        h1, h2 = st.columns([3, 1])
        h1.subheader(f"📦 Замовлення №{oid}")
        
        # Статус (оновлюється миттєво)
        status_options = ["Новий", "В роботі", "Готово", "Видано", "Скасовано"]
        current_status = order.get('status', 'Новий')
        new_status = h2.selectbox(
