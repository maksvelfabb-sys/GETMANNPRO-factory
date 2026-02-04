import streamlit as st
import pandas as pd
from datetime import datetime
from .core import get_next_order_id, save_full_order

def show_create_order():
    st.header("🆕 Прийняти нове замовлення")
    
    # Ініціалізація тимчасового списку товарів (кошика)
    if 'temp_items' not in st.session_state:
        st.session_state.temp_items = []

    user_info = st.session_state.get('auth', {})
    manager_name = user_info.get('login') or user_info.get('email', 'Користувач')

    # --- 1. ОСНОВНІ ДАНІ ЗАМОВЛЕННЯ ---
    with st.container(border=True):
        st.subheader("👤 Дані клієнта та доставки")
        c1, c2 = st.columns(2)
        
        client = c1.text_input("Клієнт (ПІБ)")
        phone = c2.text_input("Телефон")
        city = c1.text_input("Місто та відділення НП") # Ось ваше місто
        ttn = c2.text_input("ТТН (якщо є)")
        
        comment = st.text_area("Коментар")

    # --- 2. ДОДАВАННЯ ТОВАРІВ (Поза межами форми для динамічності) ---
    with st.container(border=True):
        st.subheader("📦 Додати товари")
        it1, it2, it3, it4 = st.columns([3, 2, 1, 1])
        
        name = it1.text_input("Назва товару", key="in_name")
        art = it2.text_input("Артикул", key="in_art")
        price = it3.number_input("Ціна (грн)", min_value=0, value=0, key="in_price")
        qty = it4.number_input("К-ть", min_value=1, value=1, key="in_qty")
        
        if st.button("➕ Додати до замовлення", use_container_width=True):
            if name and art:
                total = price * qty
                st.session_state.temp_items.append({
                    'назва': name,
                    'арт': art,
                    'ціна': price,
                    'к-ть': qty,
                    'сума': total
                })
                st.rerun()
            else:
                st.warning("Введіть назву та артикул")

    # --- 3. ВІДОБРАЖЕННЯ КОШИКА ---
    if st.session_state.temp_items:
        st.write("### Склад замовлення:")
        temp_df = pd.DataFrame(st.session_state.temp_items)
        st.table(temp_df)
        
        total_sum = temp_df['сума'].sum()
        st.markdown(f"#### 💰 Загальна сума: **{total_sum} грн**")
        
        if st.button("🗑️ Очистити кошик"):
            st.session_state.temp_items = []
            st.rerun()

    st.write("---")

    # --- 4. ФІНАЛЬНА КНОПКА ЗБЕРЕЖЕННЯ ---
    if st.button("🚀 ВІДПРАВИТИ ЗАМОВЛЕННЯ В БАЗУ", type="primary", use_container_width=True):
        if not client or not city:
            st.error("Поля 'Клієнт' та 'Місто' є обов'язковими!")
        elif not st.session_state.temp_items:
            st.error("Додайте хоча б один товар у замовлення!")
        else:
            next_id = get_next_order_id()
            header = {
                'ID': str(next_id),
                'Дата': datetime.now().strftime("%d.%m.%Y"),
                'Менеджер': manager_name,
                'Клієнт': client,
                'Телефон': phone,
                'Місто': city,
                'ТТН': ttn,
                'Сума': str(temp_df['сума'].sum()),
                'Готовність': 'В черзі',
                'Коментар': comment
            }
            
            # Підготовка товарів для бази (додаємо ID замовлення до кожного товару)
            final_items = []
            for item in st.session_state.temp_items:
                item['order_id'] = str(next_id)
                final_items.append(item)
                
            save_full_order(header, final_items)
            st.session_state.temp_items = [] # Чистимо кошик
            st.success(f"Замовлення №{next_id} збережено!")
            st.balloons()
