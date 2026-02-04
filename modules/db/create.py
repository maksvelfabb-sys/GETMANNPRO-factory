import streamlit as st
from datetime import datetime
from .core import get_next_order_id, save_full_order

def show_create_order():
    st.subheader("🆕 Створення замовлення")
    
    # Визначаємо менеджера з даних авторизації
    user_info = st.session_state.get('auth', {})
    manager_name = user_info.get('login') or user_info.get('email', 'Unknown')
    
    with st.form("new_order_form", clear_on_submit=True):
        next_id = get_next_order_id()
        st.info(f"Замовлення №{next_id} | Менеджер: {manager_name}")
        
        c1, c2 = st.columns(2)
        client = c1.text_input("👤 Клієнт (ПІБ)")
        phone = c2.text_input("📞 Телефон")
        city = c1.text_input("📍 Місто та відділення")
        ttn = c2.text_input("🚚 Номер ТТН (якщо є)")
        
        comment = st.text_area("💬 Коментар до замовлення")
        
        if st.form_submit_button("✅ Зареєструвати замовлення"):
            if not client:
                st.error("Будь ласка, вкажіть ім'я клієнта")
                return

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
            
            save_full_order(header, []) # Створюємо поки без товарів
            st.success(f"Замовлення №{next_id} успішно додано!")
            st.balloons()
