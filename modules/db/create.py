import streamlit as st
import pandas as pd
from datetime import datetime
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def show_create_order():
    """Відображає форму створення нового замовлення"""
    st.markdown("### 🆕 Створення нового замовлення")
    
    # Використовуємо унікальний ключ для форми, щоб уникнути StreamlitAPIException
    with st.form(key="global_order_creation_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        f_name = col1.text_input("Клієнт (ПІБ)")
        f_phone = col2.text_input("Телефон")
        f_addr = col3.text_input("Адреса доставки")
        
        col4, col5, col6 = st.columns([2, 1, 1])
        f_prod = col4.text_input("Назва товару")
        f_sku = col5.text_input("Артикул")
        f_qty = col6.number_input("Кількість", min_value=1, value=1, step=1)
        
        col7, col8 = st.columns(2)
        f_total = col7.number_input("Загальна сума (грн)", min_value=0.0, step=100.0)
        f_pre = col8.number_input("Аванс (грн)", min_value=0.0, step=100.0)
        
        submit_btn = st.form_submit_button("✅ ЗБЕРЕГТИ ТА ДОДАТИ У ЖУРНАЛ", use_container_width=True)
        
        if submit_btn:
            if not f_name or not f_prod:
                st.error("Поля 'Клієнт' та 'Назва товару' є обов'язковими!")
                return

            # Завантажуємо базу
            df = load_csv(ORDERS_CSV_ID)
            
            # Визначаємо назву колонки ID (гнучкий пошук)
            id_col = next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')
            
            # Розрахунок нового ID
            if not df.empty:
                try:
                    new_id = int(pd.to_numeric(df[id_col]).max() + 1)
                except:
                    new_id = 1001
            else:
                new_id = 1001

            # Формуємо новий рядок
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
            
            # Додаємо та зберігаємо
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_csv(ORDERS_CSV_ID, df)
            
            st.toast(f"✅ Замовлення №{new_id} створено!")
            st.rerun()
