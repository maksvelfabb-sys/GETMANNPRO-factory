import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

# 1. Функція для пошуку назви колонки ID
def get_id_column_name(df):
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

# 2. Рендер однієї картки (експандера)
def render_order_card(order):
    # Визначаємо ID
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    # Визначаємо колір для статусу
    status_colors = {
        "Новий": "background-color: #3e9084; color: white;",
        "В роботі": "background-color: #f0ad4e; color: white;",
        "Готово": "background-color: #5cb85c; color: white;",
        "Видано": "background-color: #5bc0de; color: white;",
        "Скасовано": "background-color: #d9534f; color: white;"
    }
    status = str(order.get('status', 'Новий'))
    current_style = status_colors.get(status, "background-color: #6c757d; color: white;")

    # Заголовок для експандера
    header_label = f"📦 №{oid} | {order.get('product', '---')} | {order.get('date', '---')} | {order.get('client_name', '---')} | {order.get('total', 0)} грн"

    with st.expander(header_label):
        st.markdown(f"<span style='{current_style} padding: 2px 10px; border-radius: 5px; font-weight: bold;'>{status.upper()}</span>", unsafe_allow_html=True)
        st.divider()
        
        # Поля редагування
        c1, c2, c3 = st.columns(3)
        f_name = c1.text_input("Клієнт", value=str(order.get('client_name', '')), key=f"n_{oid}")
        f_phone = c2.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"ph_{oid}")
        f_addr = c3.text_input("Адреса", value=str(order.get('address', '')), key=f"ad_{oid}")

        t1, t2, t3 = st.columns([2, 1, 1])
        f_prod = t1.text_input("Товар", value=str(order.get('product', '')), key=f"p_{oid}")
        f_sku = t2.text_input("Артикул", value=str(order.get('sku', '')), key=f"s_{oid}")
        f_qty = t3.number_input("К-сть", value=int(order.get('qty', 1)), key=f"q_{oid}")

        m1, m2, m3 = st.columns(3)
        f_total = m1.number_input("Сума", value=float(order.get('total', 0)), key=f"tot_{oid}")
        f_pre = m2.number_input("Аванс", value=float(order.get('prepayment', 0)), key=f"pre_{oid}")
        
        status_options = ["Новий", "В роботі", "Готово", "Видано", "Скасовано"]
        new_status = m3.selectbox("Статус", status_options, 
                                  index=status_options.index(status) if status in status_options else 0,
                                  key=f"st_sel_{oid}")

        # Кнопка збереження
        if st.button("💾 Зберегти зміни", key=f"save_btn_{oid}", use_container_width=True, type="primary"):
            df = load_csv(ORDERS_CSV_ID)
            id_col_save = get_id_column_name(df)
            
            # Шукаємо індекс рядка
            indices = df.index[df[id_col_save].astype(str) == oid].tolist()
            
            if indices:
                idx = indices[0]
                df.at[idx, 'client_name'] = f_name
                df.at[idx, 'client_phone'] = f_phone
                df.at[idx, 'address'] = f_addr
                df.at[idx, 'product'] = f_prod
                df.at[idx, 'sku'] = f_sku
                df.at[idx, 'qty'] = f_qty
                df.at[idx, 'total'] = f_total
                df.at[idx, 'prepayment'] = f_pre
                df.at[idx, 'status'] = new_status
                
                save_csv(ORDERS_CSV_ID, df)
                st.success(f"Замовлення №{oid} оновлено!")
                st.rerun()
            else:
                st.error("Помилка: замовлення не знайдено в базі.")

# 3. Головна функція для відображення всього журналу
def show_order_cards():
    df = load_csv(ORDERS_CSV_ID)
    
    if df.empty:
        st.info("📦 Журнал замовлень порожній.")
        return

    # Панель пошуку
    search = st.text_input("🔍 Швидкий пошук (ПІБ, телефон, товар)")
    
    # Сортування (нові зверху)
    id_col = get_id_column_name(df)
    if id_col in df.columns:
        df[id_col] = pd.to_numeric(df[id_col], errors='coerce')
        df = df.sort_values(by=id_col, ascending=False)

    # Фільтрація пошуку
    if search:
        mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        df = df[mask]

    # Вивід карток
    for _, row in df.iterrows():
        render_order_card(row)
