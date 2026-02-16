import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

# --- 1. ДОПОМІЖНА ФУНКЦІЯ ДЛЯ ПОШУКУ ID КОЛОНКИ ---
def get_id_column_name(df):
    """Шукає назву колонки ID у датафреймі"""
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

# --- 2. ФУНКЦІЯ ОНОВЛЕННЯ СТАТУСУ (ШВИДКА) ---
def update_order_status(order_id, new_status):
    """Оновлює тільки статус замовлення"""
    df = load_csv(ORDERS_CSV_ID)
    id_col = get_id_column_name(df)
    
    idx = df.index[df[id_col].astype(str) == str(order_id)].tolist()
    if idx:
        if df.at[idx[0], 'status'] != new_status:
            df.at[idx[0], 'status'] = new_status
            save_csv(ORDERS_CSV_ID, df)
            st.toast(f"✅ Статус №{order_id} змінено на {new_status}")

# --- 3. РЕНДЕР КАРТКИ ЗАМОВЛЕННЯ ---
def render_order_card(order):
    """Створює картку з полями редагування"""
    # Отримуємо ID для поточного рендеру
    id_col_current = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col_current, '0'))
    
    with st.container(border=True):
        # Заголовок
        h1, h2 = st.columns([3, 1])
        h1.subheader(f"📦 Замовлення №{oid}")
        
        # Статус (оновлюється миттєво)
        status_options = ["Новий", "В роботі", "Готово", "Видано", "Скасовано"]
        current_status = order.get('status', 'Новий')
        new_status = h2.selectbox(
            "Статус", 
            status_options, 
            index=status_options.index(current_status) if current_status in status_options else 0,
            key=f"status_sel_{oid}"
        )
        if new_status != current_status:
            update_order_status(oid, new_status)

        st.divider()

        # Редагування текстових даних
        c1, c2, c3 = st.columns(3)
        f_name = c1.text_input("Клієнт", value=str(order.get('client_name', '')), key=f"name_{oid}")
        f_phone = c2.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"phone_{oid}")
        f_addr = c3.text_input("Адреса", value=str(order.get('address', '')), key=f"addr_{oid}")

        t1, t2, t3 = st.columns([2, 1, 1])
        f_prod = t1.text_input("Товар", value=str(order.get('product', '')), key=f"prod_{oid}")
        f_sku = t2.text_input("Артикул", value=str(order.get('sku', '')), key=f"sku_{oid}")
        f_qty = t3.number_input("К-сть", value=int(order.get('qty', 1)), key=f"qty_{oid}")

        st.divider()

        # Фінанси
        m1, m2, m3 = st.columns(3)
        f_total = m1.number_input("Сума (грн)", value=float(order.get('total', 0)), key=f"tot_{oid}")
        f_pre = m2.number_input("Аванс (грн)", value=float(order.get('prepayment', 0)), key=f"pre_{oid}")
        
        balance = f_total - f_pre
        m3.metric("Залишок до сплати", f"{balance} грн", delta_color="inverse" if balance > 0 else "normal")

        # КНОПКА ЗБЕРЕЖЕННЯ (Вирішення проблеми з NameError: id_col)
        if st.button("💾 Зберегти зміни", key=f"btn_save_{oid}", use_container_width=True):
            df = load_csv(ORDERS_CSV_ID)
            
            # Визначаємо id_col безпосередньо в момент збереження
            id_col_save = get_id_column_name(df)
            
            # Пошук індексу рядка за ID
            indices = df.index[df[id_col_save].astype(str) == oid].tolist()
            
            if indices:
                idx = indices[0]
                # Оновлюємо значення в DataFrame
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
                st.success(f"Замовлення №{oid} успішно оновлено!")
                st.rerun()
            else:
                st.error("Помилка: Замовлення не знайдено в базі для оновлення.")

# --- 4. ГОЛОВНА ФУНКЦІЯ ПЕРЕГЛЯДУ ---
def show_order_cards():
    """Відображає список замовлень"""
    df = load_csv(ORDERS_CSV_ID)
    
    if df.empty:
        st.info("Журнал замовлень порожній.")
        return

    # Налаштування сортування (нові зверху)
    id_col = get_id_column_name(df)
    if id_col in df.columns:
        df[id_col] = pd.to_numeric(df[id_col], errors='coerce')
        df = df.sort_values(by=id_col, ascending=False)

    # Рядок пошуку
    search_query = st.text_input("🔍 Пошук замовлення", placeholder="Ім'я, телефон, товар або номер...")
    
    if search_query:
        # Шукаємо збіг по всіх колонках
        mask = df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
        df = df[mask]

    # Вивід карток через цикл
    for _, row in df.iterrows():
        render_order_card(row)
