import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def get_id_column_name(df):
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

def render_order_card(order):
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    # Кольори статусів як на скріншоті
    status_colors = {
        "Новий": "#3e9084",
        "ПЕРЕДАНО В ДОСТАВКУ": "#5a5a8a",
        "В ДОРОЗІ": "#5a5a8a",
        "Готово": "#5cb85c"
    }
    st_val = str(order.get('status', 'Новий')).upper()
    st_color = status_colors.get(st_val, "#6c757d")

    # Формуємо складний HTML-заголовок для імітації табличного рядка
    # Використовуємо іконки та колонки
    header_html = f"""
    <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; font-size: 14px; color: white;">
        <div style="flex: 0.5;"><b>{oid}</b></div>
        <div style="flex: 1; color: #44c2f1;">🛒 adaptex.ua</div>
        <div style="flex: 1; font-size: 12px; color: #aaa;">{order.get('date', 'Сьогодні')}</div>
        <div style="flex: 1;"><span style="background-color: {st_color}; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;">{st_val}</span></div>
        <div style="flex: 1.5; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">👤 {order.get('client_name', '---')}</div>
        <div style="flex: 1.5; color: #44c2f1;">{order.get('product', '---')}</div>
        <div style="flex: 1; text-align: right; font-weight: bold;">{order.get('total', 0)} грн</div>
    </div>
    """

    with st.expander(header_html, expanded=False):
        # Внутрішня частина (деталі замовлення як на image_9a108c.png)
        st.markdown(f"### 📦 Деталі замовлення №{oid}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Покупець**")
            f_name = st.text_input("ПІБ", value=str(order.get('client_name', '')), key=f"n_{oid}")
            f_phone = st.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"p_{oid}")
            st.button("📞 Подзвонити", key=f"call_{oid}", use_container_width=True)

        with col2:
            st.write("**Доставка**")
            f_addr = st.text_area("Адреса доставки", value=str(order.get('address', '')), key=f"ad_{oid}", height=68)
            f_sku = st.text_input("Артикул товару", value=str(order.get('sku', '')), key=f"sk_{oid}")

        with col3:
            st.write("**Оплата та Статус**")
            f_total = st.number_input("Сума замовлення", value=float(order.get('total', 0)), key=f"t_{oid}")
            status_options = ["Новий", "ПЕРЕДАНО В ДОСТАВКУ", "В ДОРОЗІ", "Готово", "Скасовано"]
            f_status = st.selectbox("Статус замовлення", status_options, 
                                   index=status_options.index(st_val) if st_val in status_options else 0,
                                   key=f"st_{oid}")

        st.divider()
        
        # Кнопка збереження змін
        if st.button("💾 Зберегти зміни в базі", key=f"save_{oid}", use_container_width=True, type="primary"):
            df = load_csv(ORDERS_CSV_ID)
            id_col_db = get_id_column_name(df)
            idx_list = df.index[df[id_col_db].astype(str) == oid].tolist()
            
            if idx_list:
                idx = idx_list[0]
                df.at[idx, 'client_name'] = f_name
                df.at[idx, 'client_phone'] = f_phone
                df.at[idx, 'address'] = f_addr
                df.at[idx, 'sku'] = f_sku
                df.at[idx, 'total'] = f_total
                df.at[idx, 'status'] = f_status
                save_csv(ORDERS_CSV_ID, df)
                st.success("Дані оновлено!")
                st.rerun()

def show_order_cards():
    df = load_csv(ORDERS_CSV_ID)
    if df.empty:
        st.info("Журнал замовлень порожній")
        return

    # Швидкий пошук у стилі CRM
    search_q = st.text_input("🔍 Швидкий пошук замовлень...", placeholder="Введіть ПІБ, номер або товар")
    
    # Сортування
    id_col = get_id_column_name(df)
    df[id_col] = pd.to_numeric(df[id_col], errors='coerce')
    df = df.sort_values(by=id_col, ascending=False)

    if search_q:
        mask = df.astype(str).apply(lambda x: x.str.contains(search_q, case=False)).any(axis=1)
        df = df[mask]

    # Рендер карток
    for _, row in df.iterrows():
        render_order_card(row)
