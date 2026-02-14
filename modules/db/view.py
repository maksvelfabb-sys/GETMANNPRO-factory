import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, ORDERS_CSV_ID

def render_order_card(order):
    """Функція для малювання однієї картки замовлення"""
    # Створюємо контейнер з рамкою для кожної картки
    with st.container(border=True):
        # Шапка картки: Номер та Статус
        col_head1, col_head2 = st.columns([3, 1])
        with col_head1:
            st.markdown(f"### 📦 Замовлення №{order.get('order_id', '---')}")
        with col_head2:
            status = order.get('status', 'Новий')
            st.info(f"**{status}**")

        st.divider()

        # Основний контент: Клієнт та Товар
        col_main1, col_main2 = st.columns(2)
        
        with col_main1:
            st.markdown("**👤 ДАНІ КЛІЄНТА**")
            st.write(f"**ПІБ:** {order.get('client_name', '---')}")
            st.write(f"**Тел:** {order.get('client_phone', '---')}")
            if order.get('client_address'):
                st.write(f"**Адреса:** {order.get('client_address', '---')}")
            
        with col_main2:
            st.markdown("**🛠 ДЕТАЛІ ТОВАРУ**")
            st.write(f"**Товар:** {order.get('product_name', '---')}")
            st.write(f"**Артикул:** `{order.get('sku', '---')}`")
            st.write(f"**К-сть:** {order.get('quantity', '1')}")

        st.divider()

        # Фінансова частина
        col_fin1, col_fin2, col_fin3 = st.columns(3)
        
        # Конвертуємо в числа для розрахунків
        try:
            total = float(order.get('total_amount', 0))
            prepayment = float(order.get('prepayment', 0))
            balance = total - prepayment
        except (ValueError, TypeError):
            total, prepayment, balance = 0.0, 0.0, 0.0

        with col_fin1:
            st.metric("Загальна сума", f"{total} грн")
        with col_fin2:
            st.metric("Аванс", f"{prepayment} грн")
        with col_fin3:
            # Виділяємо залишок червоним, якщо він більше 0
            color = "normal" if balance <= 0 else "inverse"
            st.metric("Залишок (доплата)", f"{balance} грн", delta=f"-{prepayment}", delta_color=color)

        # Коментарі та примітки
        if order.get('comment'):
            with st.expander("📝 Переглянути коментар"):
                st.write(order['comment'])

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
