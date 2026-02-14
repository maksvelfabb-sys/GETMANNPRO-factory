import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, ORDERS_CSV_ID

def get_val(order, keys):
    """Шукає значення в рядку за декількома варіантами назв колонок"""
    for key in keys:
        if key in order and pd.notnull(order[key]):
            return order[key]
    return "---"

def render_order_card(order):
    with st.container(border=True):
        # 1. ШУКАЄМО ДАНІ (синоніми назв колонок)
        order_id = get_val(order, ['order_id', 'ID', '№', 'id'])
        client_name = get_val(order, ['client_name', 'ПІБ', 'Клієнт', 'ФИО'])
        client_phone = get_val(order, ['client_phone', 'Телефон', 'Тел'])
        product = get_val(order, ['product_name', 'Товар', 'Назва'])
        sku = get_val(order, ['sku', 'Артикул', 'sku_code'])
        total = get_val(order, ['total_amount', 'Сума', 'Ціна', 'total'])
        prepayment = get_val(order, ['prepayment', 'Аванс', 'Предоплата'])
        status = get_val(order, ['status', 'Статус'])

        # ШАПКА КАРТКИ
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"### 📦 Замовлення №{order_id}")
        with col_h2:
            st.info(f"**{status}**")

        st.divider()

        # ОСНОВНІ ДАНІ
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**👤 КЛІЄНТ**")
            st.write(f"**Ім'я:** {client_name}")
            st.write(f"**Тел:** {client_phone}")
        with col2:
            st.markdown("**🛠 ТОВАР**")
            st.write(f"**Назва:** {product}")
            st.write(f"**Артикул:** `{sku}`")

        st.divider()

        # ФІНАНСИ
        c_fin1, c_fin2, c_fin3 = st.columns(3)
        try:
            t_val = float(str(total).replace(',', '.')) if total != "---" else 0
            p_val = float(str(prepayment).replace(',', '.')) if prepayment != "---" else 0
            diff = t_val - p_val
        except:
            t_val, p_val, diff = 0, 0, 0

        with c_fin1:
            st.metric("Загальна сума", f"{t_val} грн")
        with c_fin2:
            st.metric("Аванс", f"{p_val} грн")
        with c_fin3:
            st.metric("Доплата", f"{diff} грн", delta=f"-{p_val}" if p_val > 0 else None, delta_color="inverse")

def show_order_cards():
    """Головна функція для відображення списку всіх замовлень"""
    st.title("📋 Картки замовлень")
    
    # Кнопка оновлення даних
    if st.button("🔄 Оновити дані з Google Диску"):
        st.cache_data.clear()
        st.rerun()

    # Завантажуємо дані за допомогою drive_tools
    df_orders = load_csv(ORDERS_CSV_ID)

    if df_orders.empty:
        st.warning("База замовлень порожня або файл не знайдено.")
        return

    # Якщо є пошук (опційно)
    search = st.text_input("🔍 Пошук за ПІБ клієнта або номером замовлення")
    if search:
        df_orders = df_orders[
            df_orders['client_name'].str.contains(search, case=False, na=False) |
            df_orders['order_id'].astype(str).str.contains(search, case=False, na=False)
        ]

    # Виводимо картки замовлень
    # Сортуємо: останні замовлення зазвичай мають бути зверху
    for _, row in df_orders.iterrows():
        render_order_card(row)
