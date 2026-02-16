import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

# --- 1. ДОПОМІЖНА ФУНКЦІЯ ДЛЯ ПОШУКУ ID КОЛОНКИ ---
def get_id_column_name(df):
    """Шукає назву колонки ID у датафреймі"""
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

# --- 2. РЕНДЕР КАРТКИ ЗАМОВЛЕННЯ (РОЗГОРТНИЙ РЯДОК) ---
def render_order_card(order):
    """Створює компактний рядок замовлення з можливістю розгортання"""
    # Визначаємо ID
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    # Дані для заголовка
    status = str(order.get('status', 'Новий'))
    product = str(order.get('product', '---'))
    client = str(order.get('client_name', 'Невідомий'))
    date = str(order.get('date', '---'))
    total = str(order.get('total', '0'))

    # Стилізація статусу для заголовка (бейджі)
    status_colors = {
        "Новий": "background-color: #3e9084; color: white;",
        "В роботі": "background-color: #f0ad4e; color: white;",
        "Готово": "background-color: #5cb85c; color: white;",
        "Видано": "background-color: #5bc0de; color: white;",
        "Скасовано": "background-color: #d9534f; color: white;"
    }
    current_style = status_colors.get(status, "background-color: #6c757d; color: white;")

    # ФОРМУЄМО ЗАГОЛОВОК (як на скріншоті)
    # 🆔 ID | 🛒 Товар | 📅 Дата | 👤 Клієнт | 💰 Сума
    header_label = f"📦 №{oid} | {product} | {date} | {client} | {total} грн"

    # 1. СТВОРЮЄМО ЕКСПАНДЕР (РОЗГОРТНИЙ РЯДОК)
    with st.expander(header_label):
        # Відображаємо кольоровий статус всередині
        st.markdown(f"""
            <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 10px;'>
                <span style='{current_style} padding: 3px 10px; border-radius: 5px; font-weight: bold; font-size: 12px;'>
                    {status.upper()}
                </span>
                <span style='color: gray; font-size: 14px;'>Редагування замовлення №{oid}</span>
            </div>
        """, unsafe_allow_html=True)
        
        # 2. ФОРМА РЕДАГУВАННЯ ВСЕРЕДИНІ ЕКСПАНДЕРА
        c1, c2, c3 = st.columns(3)
        f_name = c1.text_input("Клієнт (ПІБ)", value=client, key=f"name_{oid}")
        f_phone = c2.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"phone_{oid}")
        f_addr = c3.text_input("Адреса доставки", value=str(order.get('address', '')), key=f"addr_{oid}")

        t1, t2, t3 = st.columns([2, 1, 1])
        f_prod = t1.text_input("Назва товару", value=product, key=f"prod_{oid}")
        f_sku = t2.text_input("Артикул (SKU)", value=str(order.get('sku', '')), key=f"sku_{oid}")
        f_qty = t3.number_input("Кількість", value=int(order.get('qty', 1)), key=f"qty_{oid}")

        st.divider()

        m1, m2, m3 = st.columns(3)
        f_total = m1.number_input("Загальна сума (грн)", value=float(order.get('total', 0)), key=f"tot_{oid}")
        f_pre = m2.number_input("Аванс (грн)", value=float(order.get('prepayment', 0)), key=f"pre_{oid}")
        
        # Вибір статусу
        status_options = ["Новий", "В роботі", "Готово", "Видано", "Скасовано"]
        new_status = m3.selectbox(
            "Змінити статус", 
            status_options, 
            index=status_options.index(status) if status in status_options else 0,
            key=f"st_sel_{oid}"
        )

        # Розрахунок залишку
        balance = f_total - f_pre
        st.info(f"💰 **Залишок до сплати:** {balance} грн")

        # КНОПКА ЗБЕРЕЖЕННЯ
        if st.button("💾 ПІДТВЕРДИТИ ЗМІНИ", key=f"btn_save_{oid}", use_container_width=True, type="primary"):
            df = load_csv(ORDERS_CSV_ID)
            id_col_save = get_id_column_name(df)
            
            # Пошук рядка за ID
            indices = df.index[df[id_col_save].astype(str) == oid].tolist()
            
            if indices:
                idx = indices[0]
                # Оновлюємо всі поля
                df.at[idx, 'client_name'] = f_name
                df.at[idx, 'client_phone'] = f_phone
                df.at[idx, 'address'] = f_addr
                df.at[idx, 'product'] = f_prod
                df.at[idx, 'sku'] = f_sku
                df.at[idx, 'qty'] = f_qty
                df.at[idx, 'total'] = f_total
                df.at[idx, 'prepayment'] = f_pre
                df.at[idx, 'status'] = new_status
                
                save_csv(ORDERS_CSV_ID, df)
                st.success(f"Замовлення №{oid} оновлено!")
                st.rerun()
            else:
                st.error("Помилка: замовлення не знайдено в базі.")

# --- 3. ГОЛОВНИЙ ЕКРАН ЖУРНАЛУ ---
def show_order_cards():
    """Відображає список замовлень з фільтрацією"""
    df = load_csv(ORDERS_CSV_ID)
    
    if df.empty:
