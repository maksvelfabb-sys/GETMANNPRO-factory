import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def get_id_column_name(df):
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

def render_order_card(order):
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    # Визначаємо кольори статусів
    status_map = {
        "НОВИЙ": "#3e9084",
        "В РОБОТІ": "#f0ad4e",
        "ГОТОВО": "#5cb85c",
        "ВИДАНО": "#6c757d",
        "СКАСОВАНО": "#d9534f"
    }
    st_val = str(order.get('status', 'Новий')).upper()
    st_color = status_map.get(st_val, "#6c757d")

    # Створюємо кастомний "рядок таблиці" за допомогою st.container та st.columns
    # Це замінить заголовок expander, який не підтримує HTML
    
    container = st.container(border=True)
    
    # 1. Створюємо видимий рядок-заголовок
    col_id, col_src, col_date, col_status, col_name, col_prod, col_total = container.columns([0.5, 1, 1, 1, 1.5, 1.5, 1])
    
    col_id.markdown(f"**{oid}**")
    col_src.markdown(f"<span style='color: #44c2f1;'>🛒 adaptex.ua</span>", unsafe_allow_html=True)
    col_date.markdown(f"<span style='font-size: 12px; color: #aaa;'>{order.get('date', '---')}</span>", unsafe_allow_html=True)
    col_status.markdown(f"<span style='background-color: {st_color}; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 10px; color: white;'>{st_val}</span>", unsafe_allow_html=True)
    col_name.markdown(f"👤 {order.get('client_name', '---')}")
    col_prod.markdown(f"<span style='color: #44c2f1;'>{order.get('product', '---')}</span>", unsafe_allow_html=True)
    col_total.markdown(f"**{order.get('total', 0)} грн**")

    # 2. Додаємо кнопку "Деталі", яка відкриває форму всередині цього ж контейнера
    show_details = container.checkbox("Розгорнути деталі", key=f"chk_{oid}")

    if show_details:
        st.divider()
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("##### 👤 Покупець")
            f_name = st.text_input("ПІБ", value=str(order.get('client_name', '')), key=f"n_{oid}")
            f_phone = st.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"p_{oid}")
            st.button("📞 Подзвонити", key=f"call_{oid}", use_container_width=True)

        with c2:
            st.markdown("##### 📦 Доставка")
            f_addr = st.text_area("Адреса", value=str(order.get('address', '')), key=f"ad_{oid}", height=68)
            f_sku = st.text_input("Артикул", value=str(order.get('sku', '')), key=f"sk_{oid}")

        with c3:
            st.markdown("##### 💰 Оплата")
            f_total = st.number_input("Сума", value=float(order.get('total', 0)), key=f"t_{oid}")
            f_status = st.selectbox("Статус", list(status_map.keys()), 
                                   index=list(status_map.keys()).index(st_val) if st_val in status_map else 0,
                                   key=f"st_{oid}")

        if st.button("💾 Зберегти зміни", key=f"save_{oid}", use_container_width=True, type="primary"):
            df = load_csv(ORDERS_CSV_ID)
            id_col_db = get_id_column_name(df)
            indices = df.index[df[id_col_db].astype(str) == oid].tolist()
            if indices:
                idx = indices[0]
                df.at[idx, 'client_name'] = f_name
                df.at[idx, 'client_phone'] = f_phone
                df.at[idx, 'address'] = f_addr
                df.at[idx, 'sku'] = f_sku
                df.at[idx, 'total'] = f_total
                df.at[idx, 'status'] = f_status
                save_csv(ORDERS_CSV_ID, df)
                st.success("Оновлено!")
                st.rerun()

def show_order_cards():
    df = load_csv(ORDERS_CSV_ID)
    if df.empty:
        st.info("Журнал порожній")
        return

    # Заголовок таблиці (імітація)
    st.markdown("""
    <div style="display: flex; font-weight: bold; border-bottom: 1px solid #444; padding-bottom: 5px; margin-bottom: 10px; font-size: 13px; color: #888;">
        <div style="flex: 0.5;">ID</div>
        <div style="flex: 1;">Джерело</div>
        <div style="flex: 1;">Дата</div>
        <div style="flex: 1;">Статус</div>
        <div style="flex: 1.5;">Клієнт</div>
        <div style="flex: 1.5;">Товар</div>
        <div style="flex: 1; text-align: right;">Сума</div>
    </div>
    """, unsafe_allow_html=True)

    # Сортування
    id_col = get_id_column_name(df)
    df[id_col] = pd.to_numeric(df[id_col], errors='coerce')
    df = df.sort_values(by=id_col, ascending=False)

    for _, row in df.iterrows():
        render_order_card(row)
