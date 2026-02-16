import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def get_id_column_name(df):
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

def render_order_card(order):
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    # 🎨 Кольорова схема статусів (можна налаштувати під себе)
    status_map = {
        "НОВИЙ": "#3e9084",
        "В РОБОТІ": "#f0ad4e",
        "ГОТОВО": "#5cb85c",
        "ВИДАНО": "#6c757d",
        "СКАСОВАНО": "#d9534f"
    }
    current_status = str(order.get('status', 'Новий')).upper()
    st_color = status_map.get(current_status, "#6c757d")

    # 📋 ВАШ HTML-ЗАГОЛОВОК (з динамічними даними)
    header_html = f"""
    <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; font-size: 14px; color: white;">
        <div style="flex: 0.5;"><b>{oid}</b></div>
        <div style="flex: 1; color: #44c2f1;">🛒 adaptex.ua</div>
        <div style="flex: 1; font-size: 12px; color: #aaa;">{order.get('date', '---')}</div>
        <div style="flex: 1;"><span style="background-color: {st_color}; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;">{current_status}</span></div>
        <div style="flex: 1.5; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">👤 {order.get('client_name', '---')}</div>
        <div style="flex: 1.5; color: #44c2f1;">{order.get('product', '---')}</div>
        <div style="flex: 1; text-align: right; font-weight: bold;">{order.get('total', 0)} грн</div>
    </div>
    """

    with st.expander(header_html):
        st.markdown(f"#### ✏️ Редагування замовлення №{oid}")
        
        # Блок редагування
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.caption("👤 Клієнт")
            f_name = st.text_input("ПІБ", value=str(order.get('client_name', '')), key=f"n_{oid}")
            f_phone = st.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"p_{oid}")

        with col2:
            st.caption("📦 Товар та Доставка")
            f_prod = st.text_input("Назва товару", value=str(order.get('product', '')), key=f"pr_{oid}")
            f_addr = st.text_area("Адреса", value=str(order.get('address', '')), key=f"ad_{oid}", height=68)

        with col3:
            st.caption("💰 Фінанси та Статус")
            f_total = st.number_input("Сума", value=float(order.get('total', 0)), key=f"t_{oid}")
            status_options = ["НОВИЙ", "В РОБОТІ", "ГОТОВО", "ВИДАНО", "СКАСОВАНО"]
            f_status = st.selectbox("Статус", status_options, 
                                   index=status_options.index(current_status) if current_status in status_options else 0,
                                   key=f"st_{oid}")

        # Кнопка збереження
        if st.button("💾 Оновити замовлення", key=f"save_{oid}", use_container_width=True, type="primary"):
            df = load_csv(ORDERS_CSV_ID)
            id_col_db = get_id_column_name(df)
            indices = df.index[df[id_col_db].astype(str) == oid].tolist()
            
            if indices:
                idx = indices[0]
                df.at[idx, 'client_name'] = f_name
                df.at[idx, 'client_phone'] = f_phone
                df.at[idx, 'product'] = f_prod
                df.at[idx, 'address'] = f_addr
                df.at[idx, 'total'] = f_total
                df.at[idx, 'status'] = f_status
                
                save_csv(ORDERS_CSV_ID, df)
                st.success("Дані успішно збережені!")
                st.rerun()

def show_order_cards():
    df = load_csv(ORDERS_CSV_ID)
    if df.empty:
        st.info("Журнал замовлень порожній")
        return

    # Пошук
    search = st.text_input("🔍 Швидкий пошук", placeholder="Пошук за іменем, номером або товаром...")
    
    # Сортування (нові зверху)
    id_col = get_id_column_name(df)
    df[id_col] = pd.to_numeric(df[id_col], errors='coerce')
    df = df.sort_values(by=id_col, ascending=False)

    if search:
        mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        df = df[mask]

    # Вивід списку
    for _, row in df.iterrows():
        render_order_card(row)
