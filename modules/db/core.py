import streamlit as st
import pandas as pd
import io
from modules.admin_module import load_csv, save_csv
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID, USERS_CSV_ID, ITEMS_CSV_ID

# ID файлів на Google Drive
ORDERS_HEADER_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i" 
ORDER_ITEMS_ID = "1knqbYIrK6q_hyj1wkrqOUzIIZfL_ils1"
ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i" \

def get_next_order_id():
    """Рахує наступний вільний ID замовлення"""
    df = load_csv(ORDERS_HEADER_ID)
    if df.empty or 'ID' not in df.columns:
        return 1
    # Перетворюємо в числа, ігноруючи помилки, та беремо максимум
    ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
    return int(ids.max() + 1) if not ids.empty else 1

def save_full_order(header_data, items_list):
    """Зберігає шапку та список товарів у різні файли"""
    # 1. Оновлення основної таблиці (Headers)
    df_h = load_csv(ORDERS_HEADER_ID)
    
    # Перевірка наявності колонки Менеджер (для старих баз)
    if 'Менеджер' not in df_h.columns:
        df_h['Менеджер'] = ""
        
    df_h = pd.concat([df_h, pd.DataFrame([header_data])], ignore_index=True)
    save_csv(ORDERS_HEADER_ID, df_h)
    
    # 2. Оновлення таблиці позицій (Items), якщо вони є
    if items_list:
        df_i = load_csv(ORDER_ITEMS_ID)
        items_df = pd.DataFrame(items_list)
        items_df['order_id'] = header_data['ID']
        df_i = pd.concat([df_i, items_df], ignore_index=True)
        save_csv(ORDER_ITEMS_ID, df_i)

def update_order_header(order_id, updated_row):
    """Оновлює дані в основній таблиці"""
    df = load_csv(ORDERS_HEADER_ID)
    idx = df[df['ID'] == str(order_id)].index
    if not idx.empty:
        for col, val in updated_row.items():
            df.at[idx[0], col] = val
        save_csv(ORDERS_HEADER_ID, df)

# Завантажуємо дані
df_orders = load_csv(ORDERS_CSV_ID)

if not df_orders.empty:
    # Сортуємо: нові зверху (якщо є колонка дати)
    for _, row in df_orders.iterrows():
        render_order_card(row)
else:
    st.warning("База замовлень порожня.")
