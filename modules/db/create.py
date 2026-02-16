import streamlit as st
import pandas as pd
from datetime import datetime
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def show_create_order():  # Назва має бути точно такою
    st.markdown("### 🆕 Створення нового замовлення")
        with st.form("new_order_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            f_name = col1.text_input("Клієнт (ПІБ)")
            f_phone = col2.text_input("Телефон")
            f_addr = col3.text_input("Адреса доставки")
            
            col4, col5, col6 = st.columns([2, 1, 1])
            f_prod = col4.text_input("Назва товару")
            f_sku = col5.text_input("Артикул")
            f_qty = col6.number_input("Кількість", min_value=1, value=1)
            
            col7, col8 = st.columns(2)
            f_total = col7.number_input("Загальна сума (грн)", min_value=0.0)
            f_pre = col8.number_input("Аванс (грн)", min_value=0.0)
            
            btn_save, btn_cancel = st.columns(2)

                   submitted = st.form_submit_button("✅ ДОДАТИ")
        if submitted:
            # Логіка збереження...
            st.session_state.creating_now = False
            st.rerun()
            
            if btn_save.form_submit_button("✅ ЗБЕРЕГТИ ТА ДОДАТИ", use_container_width=True):
                if not f_name or not f_prod:
                    st.error("Будь ласка, заповніть ПІБ клієнта та назву товару!")
                    return

                df = load_csv(ORDERS_CSV_ID)
                
                # Визначаємо колонку ID та новий номер
                id_col = next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')
                new_id = int(df[id_col].max() + 1) if not df.empty else 1001
                
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
                    'date': datetime.now().strftime("%d.%m.%Y %H:%M")
                }
                
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_csv(ORDERS_CSV_ID, df)
                
                st.session_state.creating_now = False # Закриваємо форму
                st.success(f"Замовлення №{new_id} успішно створено!")
                st.rerun()
            
            if btn_cancel.form_submit_button("❌ СКАСУВАТИ", use_container_width=True):
                st.session_state.creating_now = False
                st.rerun()
