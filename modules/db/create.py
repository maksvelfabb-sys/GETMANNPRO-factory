import streamlit as st
import pandas as pd
from datetime import datetime
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def show_create_order():
    with st.container(border=True):
        st.markdown("### 🆕 Створення замовлення")
        form_key = f"new_order_form_{datetime.now().strftime('%H%M%S')}"
        
        with st.form(key=form_key, clear_on_submit=True):
        
        with st.form(key="new_order_creation_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            f_name = col1.text_input("Клієнт (ПІБ)")
            f_phone = col2.text_input("Телефон")
            f_addr = col3.text_input("Адреса")
            
            col4, col5, col6 = st.columns([2, 1, 1])
            f_prod = col4.text_input("Назва товару")
            f_sku = col5.text_input("Артикул")
                        f_qty = col6.number_input("Кількість", min_value=1, value=1, step=1)
            
            col7, col8 = st.columns(2)
            f_total = col7.number_input("Сума (грн)", min_value=0.0, step=100.0)
            f_pre = col8.number_input("Аванс (грн)", min_value=0.0, step=100.0)
            
            btn_save, btn_cancel = st.columns(2)
            
            # Кнопка збереження
            if btn_save.form_submit_button("✅ ЗБЕРЕГТИ", use_container_width=True):
                # Перевірка на заповнення обов'язкових полів
                if not f_name or not f_prod:
                    st.error("Поля 'Клієнт' та 'Товар' обов'язкові для заповнення!")
                    return

                df = load_csv(ORDERS_CSV_ID)
                
                # Пошук колонки для ID
                id_col = next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')
                
                # ЛОГІКА ID: перетворюємо на числа, щоб уникнути помилок сортування
                if not df.empty:
                    try:
                        max_id = pd.to_numeric(df[id_col]).max()
                        new_id = int(max_id + 1)
                    except:
                        new_id = 1001
                else:
                    new_id = 1001
                
                # Створення нового рядка (ключі повинні збігатися з колонками у CSV)
                new_row = {
                    id_col: new_id, 
                    'client_name': f_name, 
                    'client_phone': f_phone, 
                    'address': f_addr,
                    'product': f_prod, 
                    'sku': f_sku, 
                    'qty': f_qty, 
                    'total': f_total, 
                    'prepayment': f_pre, 
                    'status': 'Новий', 
                    'date': datetime.now().strftime("%d.%m.%Y")
                }
                
                # Додавання в DataFrame
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
                # Збереження
                save_csv(ORDERS_CSV_ID, df)
                
                # Оновлення стану
                st.session_state.creating_now = False
                st.toast("✅ Замовлення успішно додано!")
                st.rerun()
            
            # Кнопка скасування (тепер працює коректно всередині форми)
            if btn_cancel.form_submit_button("❌ СКАСУВАТИ", use_container_width=True):
                st.session_state.creating_now = False
                st.rerun()
