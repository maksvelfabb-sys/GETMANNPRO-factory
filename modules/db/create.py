import streamlit as st
from datetime import datetime
from .core import get_next_order_id, save_full_order

def show_create_order():
    st.subheader("🆕 Створення нового замовлення")
    
    # Ініціалізація тимчасового списку товарів у сесії
    if 'temp_items' not in st.session_state:
        st.session_state.temp_items = []

    user_info = st.session_state.get('auth', {})
    manager_name = user_info.get('login') or user_info.get('email', 'Unknown')
    
    # --- БЛОК 1: ДАНІ КЛІЄНТА ---
    with st.form("client_form"):
        next_id = get_next_order_id()
        st.info(f"Замовлення №{next_id} | Менеджер: {manager_name}")
        
        c1, c2 = st.columns(2)
        client = c1.text_input("👤 Клієнт (ПІБ)")
        phone = c2.text_input("📞 Телефон")
        city = c1.text_input("📍 Місто та відділення")
        ttn = c2.text_input("🚚 Номер ТТН")
        comment = st.text_area("💬 Коментар")
        
        submit_order = st.form_submit_button("✅ Зберегти замовлення та товари")

    # --- БЛОК 2: ДОДАВАННЯ ТОВАРІВ ---
    st.write("---")
    st.subheader("📦 Товари у замовленні")
    
    with st.expander("Додати товар до списку", expanded=True):
        it_c1, it_c2, it_c3 = st.columns([3, 2, 1])
        it_name = it_c1.text_input("Назва товару (напр. Проставки 20мм)")
        it_art = it_c2.text_input("Артикул (для PDF)")
        it_qty = it_c3.number_input("К-ть", min_value=1, value=1)
        
        if st.button("➕ Додати в список"):
            if it_name and it_art:
                st.session_state.temp_items.append({
                    'order_id': str(next_id),
                    'назва': it_name,
                    'арт': it_art,
                    'к-ть': str(it_qty)
                })
            else:
                st.warning("Введіть назву та артикул")

    # Відображення поточної черги товарів
    if st.session_state.temp_items:
        st.table(st.session_state.temp_items)
        if st.button("🗑️ Очистити список товарів"):
            st.session_state.temp_items = []
            st.rerun()

    # --- ЛОГІКА ЗБЕРЕЖЕННЯ ---
    if submit_order:
        if not client:
            st.error("Вкажіть клієнта!")
        else:
            header = {
                'ID': str(next_id),
                'Дата': datetime.now().strftime("%d.%m.%Y"),
                'Менеджер': manager_name,
                'Клієнт': client,
                'Телефон': phone,
                'Місто': city,
                'ТТН': ttn,
                'Готовність': 'В черзі',
                'Коментар': comment
            }
            # Зберігаємо все разом
            save_full_order(header, st.session_state.temp_items)
            st.session_state.temp_items = [] # Очищуємо кошик
            st.success("Замовлення та товари успішно збережені!")
            st.rerun()
