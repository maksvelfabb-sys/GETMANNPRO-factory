import streamlit as st

def apply_custom_styles():
    st.markdown("""
    <style>
    /* Компактність карток */
    [data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"] {
        gap: 0.5rem !important;
        padding: 0.5rem !important;
    }
    
    /* Кольори статусів */
    .status-v-cherzi { border-left: 10px solid #FFA500 !important; background-color: #FFF5E6; } /* Помаранчевий */
    .status-v-roboti { border-left: 10px solid #007BFF !important; background-color: #E6F0FF; } /* Синій */
    .status-gotovo { border-left: 10px solid #28A745 !important; background-color: #EAF9EE; }   /* Зелений */
    .status-vidpravleno { border-left: 10px solid #6C757D !important; opacity: 0.8; }         /* Сірий */

    /* Стиль для тексту всередині компактної картки */
    .card-id { font-size: 1.1rem; font-weight: bold; color: #1E1E1E; }
    .card-info { font-size: 0.9rem; color: #555; }
    
    /* Кнопка PDF */
    .pdf-button {
        background-color: #FF4B4B;
        color: white !important;
        padding: 2px 8px;
        border-radius: 4px;
        text-decoration: none;
        font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

import streamlit as st

def render_order_card(order):
    # Визначаємо колір статусу для візуального акценту
    status_colors = {
        "Новий": "blue",
        "В роботі": "orange",
        "Готово": "green",
        "Скасовано": "gray"
    }
    status_color = status_colors.get(order.get('status'), "blue")

    # Створюємо контейнер картки з рамкою
    with st.container(border=True):
        # Рядок 1: Заголовок та Статус
        col_head1, col_head2 = st.columns([3, 1])
        with col_head1:
            st.markdown(f"### 📦 Замовлення №{order.get('order_id', '---')}")
        with col_head2:
            st.markdown(f":{status_color}[**{order.get('status', 'Невідомо')}**]")

        st.divider()

        # Рядок 2: Дані клієнта та Товар
        col_main1, col_main2 = st.columns(2)
        
        with col_main1:
            st.markdown("**👤 КЛІЄНТ**")
            st.write(f"**ПІБ:** {order.get('client_name', '---')}")
            st.write(f"**Тел:** {order.get('client_phone', '---')}")
            st.write(f"**Адреса:** {order.get('client_address', '---')}")
            
        with col_main2:
            st.markdown("**🛠 ТОВАР**")
            st.write(f"**Назва:** {order.get('product_name', '---')}")
            st.write(f"**Артикул:** `{order.get('sku', '---')}`")
            st.write(f"**К-сть:** {order.get('quantity', '1')}")

        st.divider()

        # Рядок 3: Фінансова частина
        col_fin1, col_fin2, col_fin3 = st.columns(3)
        
        total = float(order.get('total_amount', 0))
        prepayment = float(order.get('prepayment', 0))
        balance = total - prepayment

        with col_fin1:
            st.metric("Загальна сума", f"{total} грн")
        with col_fin2:
            st.metric("Аванс", f"{prepayment} грн", delta=None)
        with col_fin3:
            st.metric("До сплати", f"{balance} грн", delta=f"-{prepayment}", delta_color="inverse")

        # Коментар (якщо є)
        if order.get('comment'):
            with st.expander("📝 Переглянути коментар"):
                st.write(order['comment'])

        # Кнопки дій (якщо потрібно)
        if st.button("Редагувати", key=f"edit_{order['order_id']}"):
            st.session_state.editing_order = order['order_id']
