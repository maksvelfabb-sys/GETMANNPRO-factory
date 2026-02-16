import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

# --- 1. ФУНКЦІЯ ОНОВЛЕННЯ ДАНИХ ---
def update_order_field(order_id, field_name, new_value):
    """Оновлює конкретне поле в CSV на Google Drive"""
    df = load_csv(ORDERS_CSV_ID)
    
    # Визначаємо колонку ID
    id_col = next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')
    
    # Знаходимо індекс рядка
    idx = df.index[df[id_col].astype(str) == str(order_id)].tolist()
    
    if idx:
        # Перевіряємо, чи змінилося значення
        if str(df.at[idx[0], field_name]) != str(new_value):
            df.at[idx[0], field_name] = new_value
            save_csv(ORDERS_CSV_ID, df)
            st.toast(f"✅ {field_name} збережено!")

# --- 2. РЕНДЕР КАРТКИ ЗАМОВЛЕННЯ ---
def render_order_card(order):
    """Створює візуальну картку замовлення з можливістю редагування"""
    oid = str(order.get('order_id') or order.get('ID') or '0')
    
    # Кольорове позначення в залежності від статусу (опціонально через CSS)
    with st.container(border=True):
        # Шапка картки
        col_title, col_status = st.columns([3, 1])
        col_title.subheader(f"📦 Замовлення №{oid}")
        
        status_options = ["Новий", "В роботі", "Готово", "Видано", "Скасовано"]
        current_status = order.get('status', 'Новий')
        
        # Вибір статусу
        new_status = col_status.selectbox(
            "Статус", 
            status_options, 
            index=status_options.index(current_status) if current_status in status_options else 0,
            key=f"st_{oid}"
        )
        if new_status != current_status:
            update_order_field(oid, 'status', new_status)

        st.divider()

        # Дані клієнта
        c1, c2, c3 = st.columns(3)
        f_name = c1.text_input("Клієнт", value=str(order.get('client_name', '')), key=f"n_{oid}")
        f_phone = c2.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"ph_{oid}")
        f_addr = c3.text_input("Адреса", value=str(order.get('address', '')), key=f"ad_{oid}")

        # Дані товару
        t1, t2, t3 = st.columns([2, 1, 1])
        f_prod = t1.text_input("Товар", value=str(order.get('product', '')), key=f"p_{oid}")
        f_sku = t2.text_input("Артикул", value=str(order.get('sku', '')), key=f"s_{oid}")
        f_qty = t3.number_input("К-сть", value=int(order.get('qty', 1)), key=f"q_{oid}")

        # Фінанси
        st.divider()
        m1, m2, m3 = st.columns(3)
        f_total = m1.number_input("Сума (грн)", value=float(order.get('total', 0)), key=f"tot_{oid}")
        f_pre = m2.number_input("Аванс (грн)", value=float(order.get('prepayment', 0)), key=f"pre_{oid}")
        
        balance = f_total - f_pre
        m3.metric("Залишок до сплати", f"{balance} грн", delta_color="inverse" if balance > 0 else "normal")

        # Кнопка збереження змін в текстових полях
        if st.button("💾 Зберегти зміни", key=f"save_{oid}", use_container_width=True):
            # Оновлюємо всі поля при натисканні (якщо вони були змінені)
            df = load_csv(ORDERS_CSV_ID)
            idx = df.index[df[id_col].astype(str) == oid].tolist()[0]
            
            df.at[idx, 'client_name'] = f_name
            df.at[idx, 'client_phone'] = f_phone
            df.at[idx, 'address'] = f_addr
            df.at[idx, 'product'] = f_prod
            df.at[idx, 'sku'] = f_sku
            df.at[idx, 'qty'] = f_qty
            df.at[idx, 'total'] = f_total
            df.at[idx, 'prepayment'] = f_pre
            
            save_csv(ORDERS_CSV_ID, df)
            st.success("Дані оновлено!")
            st.rerun()

# --- 3. ГОЛОВНА ФУНКЦІЯ МОДУЛЯ ---
def show_order_cards():
    """Відображає список замовлень"""
    # Завантаження даних
    df = load_csv(ORDERS_CSV_ID)
    
    if df.empty:
        st.info("Журнал замовлень порожній.")
        return

    # Пошук та фільтрація
    search_query = st.text_input("🔍 Швидкий пошук", placeholder="ПІБ, телефон або номер замовлення...")
    
    # Визначаємо колонку ID для сортування
    id_col = next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), None)
    
    if id_col:
        df[id_col] = pd.to_numeric(df[id_col], errors='coerce')
        df = df.sort_values(by=id_col, ascending=False) # Нові зверху

    # Логіка пошуку
    if search_query:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
        df = df[mask]

    # Рендеринг карток
    for _, row in df.iterrows():
        render_order_card(row)
