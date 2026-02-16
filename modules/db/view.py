import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID, get_file_link_by_name

def get_id_column_name(df):
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

def render_order_card(order):
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    # Головний контейнер картки
    container = st.container(border=True)
    
    # Компактний рядок-заголовок (те, що видно завжди)
    c1, c2, c3, c4 = container.columns([0.5, 1, 2, 1])
    c1.markdown(f"**№{oid}**")
    c2.caption(order.get('date', '---'))
    c3.markdown(f"👤 **{order.get('client_name', '---')}**")
    c4.markdown(f"**{order.get('total', 0)} грн**")

    # Розгортаємо деталі
    with container.expander("📝 Редагувати дані клієнта, товари та креслення"):
        
        # --- БЛОК 1: ІНФОРМАЦІЯ ПРО КЛІЄНТА ---
        st.markdown("##### 👤 Інформація про клієнта")
        col_name, col_phone = st.columns(2)
        f_name = col_name.text_input("ПІБ Клієнта", value=str(order.get('client_name', '')), key=f"name_{oid}")
        f_phone = col_phone.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"phone_{oid}")
        f_addr = st.text_input("Адреса доставки", value=str(order.get('address', '')), key=f"addr_{oid}")
        
        st.divider()

        # --- БЛОК 2: ТОВАРИ (ТАБЛИЦЯ) ---
        st.markdown("##### 🛒 Товари в замовленні")
        # Розбиваємо рядок товарів для редактора
        raw_products = str(order.get('product', ''))
        product_list = [p.strip() for p in raw_products.split(',')] if raw_products else []
        items_df = pd.DataFrame({"Назва товару": product_list})
        
        # Редактор таблиці (можна додавати/видаляти рядки)
        edited_items = st.data_editor(
            items_df, 
            num_rows="dynamic", 
            key=f"editor_{oid}",
            use_container_width=True
        )

        st.divider()

        # --- БЛОК 3: КРЕСЛЕННЯ ТА СТАТУС ---
        col_sku, col_status = st.columns(2)
        
        with col_sku:
            st.markdown("##### 📐 Креслення")
            f_sku = st.text_input("Артикул (SKU)", value=str(order.get('sku', '')), key=f"sku_{oid}")
            if f_sku:
                file_link = get_file_link_by_name(f_sku)
                if file_link:
                    st.link_button("📂 Відкрити креслення", file_link, use_container_width=True, type="secondary")
                else:
                    st.warning("Креслення не знайдено")
        
        with col_status:
            st.markdown("##### ⚙️ Статус та Оплата")
            status_options = ["НОВИЙ", "В РОБОТІ", "ГОТОВО", "ВИДАНО", "СКАСОВАНО"]
            curr_st = str(order.get('status', 'НОВИЙ')).upper()
            f_status = st.selectbox("Змінити статус", status_options, 
                                   index=status_options.index(curr_st) if curr_st in status_options else 0,
                                   key=f"st_{oid}")
            f_total = st.number_input("Підсумкова сума", value=float(order.get('total', 0)), key=f"tot_{oid}")

        # --- КНОПКА ЗБЕРЕЖЕННЯ ---
        if st.button("💾 Зберегти всі зміни", key=f"save_{oid}", type="primary", use_container_width=True):
            df = load_csv(ORDERS_CSV_ID)
            id_col_db = get_id_column_name(df)
            indices = df.index[df[id_col_db].astype(str) == oid].tolist()
            
            if indices:
                idx = indices[0]
                # Оновлюємо клієнта
                df.at[idx, 'client_name'] = f_name
                df.at[idx, 'client_phone'] = f_phone
                df.at[idx, 'address'] = f_addr
                # Оновлюємо товари (збираємо з таблиці в рядок)
                new_products = ", ".join(edited_items["Назва товару"].tolist())
                df.at[idx, 'product'] = new_products
                # Оновлюємо інше
                df.at[idx, 'sku'] = f_sku
                df.at[idx, 'status'] = f_status
                df.at[idx, 'total'] = f_total
                
                save_csv(ORDERS_CSV_ID, df)
                st.success("Дані успішно оновлено!")
                st.rerun()

def show_order_cards():
    df = load_csv(ORDERS_CSV_ID)
    if df.empty:
        st.info("Журнал замовлень порожній")
        return

    # Пошук
    search = st.text_input("🔍 Пошук замовлення...", placeholder="Ім'я, телефон або артикул")
    
    # Сортування
    id_col = get_id_column_name(df)
    df[id_col] = pd.to_numeric(df[id_col], errors='coerce')
    df = df.sort_values(by=id_col, ascending=False)

    if search:
        mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        df = df[mask]

    for _, row in df.iterrows():
        render_order_card(row)
