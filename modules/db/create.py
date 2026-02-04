import streamlit as st
from datetime import datetime
from .core import get_next_order_id, save_full_order

def show_create_order():
    st.subheader("🆕 Створення нового замовлення")
    
    # Визначаємо, хто саме створює замовлення
    user_info = st.session_state.get('auth', {})
    manager_name = user_info.get('login') or user_info.get('email', 'Користувач')
    
    if 'temp_items' not in st.session_state:
        st.session_state.temp_items = []

    # --- ФОРМА ЗАМОВЛЕННЯ ---
    with st.form("main_order_form", clear_on_submit=True):
        next_id = get_next_order_id()
        st.info(f"Замовлення №{next_id} | Автор: {manager_name}")
        
        c1, c2 = st.columns(2)
        client = c1.text_input("👤 Клієнт (ПІБ)")
        phone = c2.text_input("📞 Телефон")
        city = c1.text_input("📍 Місто та відділення")
        ttn = c2.text_input("🚚 Номер ТТН")
        comment = st.text_area("💬 Коментар")
        
        submit = st.form_submit_button("✅ Зберегти замовлення та всі товари")

    # --- ДОДАВАННЯ ТОВАРІВ У ТИМЧАСОВИЙ СПИСОК ---
    st.divider()
    st.markdown("### 📦 Товари в кошику")
    
    with st.container(border=True):
        it_c1, it_c2, it_c3 = st.columns([3, 2, 1])
        it_name = it_c1.text_input("Назва товару", key="new_it_name")
        it_art = it_c2.text_input("Артикул", key="new_it_art")
        it_qty = it_c3.number_input("К-ть", min_value=1, value=1, key="new_it_qty")
        
        if st.button("➕ Додати до списку"):
            if it_name and it_art:
                st.session_state.temp_items.append({
                    'order_id': str(next_id),
                    'назва': it_name,
                    'арт': it_art,
                    'к-ть': str(it_qty)
                })
                st.rerun()
            else:
                st.warning("Заповніть назву та артикул товару")

    if st.session_state.temp_items:
        st.table(pd.DataFrame(st.session_state.temp_items)[['назва', 'арт', 'к-ть']])
        if st.button("🗑️ Очистити список"):
            st.session_state.temp_items = []
            st.rerun()

    # Збереження в базу
    if submit:
        if not client:
            st.error("Вкажіть ім'я клієнта!")
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
            save_full_order(header, st.session_state.temp_items)
            st.session_state.temp_items = [] 
            st.success(f"Замовлення №{next_id} успішно створено!")
            st.rerun()
