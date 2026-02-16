import streamlit as st
import pandas as pd
import os
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

# Шлях до папки з кресленнями (якщо вони на Drive, треба буде підключити drive_tools)
# Поки що припустимо, що ми шукаємо посилання або локальний шлях
DRAWINGS_PATH = "drawings/" 

def get_id_column_name(df):
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

def render_order_card(order):
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    status_map = {
        "НОВИЙ": "#3e9084",
        "В РОБОТІ": "#f0ad4e",
        "ГОТОВО": "#5cb85c",
        "ВИДАНО": "#6c757d"
    }
    st_val = str(order.get('status', 'НОВИЙ')).upper()
    st_color = status_map.get(st_val, "#6c757d")

    # ВІЗУАЛЬНИЙ РЯДОК (Без джерела)
    container = st.container(border=True)
    col_id, col_date, col_status, col_name, col_prod, col_total = container.columns([0.5, 1, 1, 2, 2, 1])
    
    col_id.markdown(f"**{oid}**")
    col_date.markdown(f"<span style='font-size: 12px; color: #aaa;'>{order.get('date', '---')}</span>", unsafe_allow_html=True)
    col_status.markdown(f"<span style='background-color: {st_color}; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 10px; color: white;'>{st_val}</span>", unsafe_allow_html=True)
    col_name.markdown(f"👤 {order.get('client_name', '---')}")
    col_prod.markdown(f"<span style='color: #44c2f1;'>{order.get('product', '---')}</span>", unsafe_allow_html=True)
    col_total.markdown(f"**{order.get('total', 0)} грн**")

    show_details = container.checkbox("Деталі та Креслення", key=f"chk_{oid}")

    if show_details:
        st.divider()
        
        tab1, tab2 = st.tabs(["📋 Дані замовлення", "📐 Креслення та Товари"])
        
        with tab1:
            c1, c2, c3 = st.columns(3)
            with c1:
                f_name = st.text_input("Клієнт", value=str(order.get('client_name', '')), key=f"n_{oid}")
                f_phone = st.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"p_{oid}")
            with c2:
                f_addr = st.text_area("Адреса", value=str(order.get('address', '')), key=f"ad_{oid}", height=68)
            with c3:
                f_total = st.number_input("Сума", value=float(order.get('total', 0)), key=f"t_{oid}")
                f_status = st.selectbox("Статус", list(status_map.keys()), 
                                       index=list(status_map.keys()).index(st_val) if st_val in status_map else 0,
                                       key=f"st_{oid}")

        with tab2:
            st.markdown("##### 📦 Товари в замовленні")
            # Можливість редагувати товар та артикул
            f_prod = st.text_input("Товар", value=str(order.get('product', '')), key=f"pr_{oid}")
            f_sku = st.text_input("Артикул (SKU)", value=str(order.get('sku', '')), key=f"sk_{oid}")
            
            # ЛОГІКА КРЕСЛЕНЬ
            if f_sku:
                st.markdown(f"**Пошук креслення для артикулу: `{f_sku}`**")
                # Тут ми імітуємо пошук файлу. Якщо у вас креслення в Google Drive, 
                # ми використаємо drive_tools.search_file(f_sku)
                drawing_url = f"https://your-storage.com/drawings/{f_sku}.pdf" # Приклад
                
                col_btn, col_info = st.columns([1, 2])
                with col_btn:
                    st.button("👁 Переглянути креслення", key=f"draw_{oid}")
                with col_info:
                    st.info("Креслення знайдено в базі")
            else:
                st.warning("Введіть артикул для завантаження креслення")

        if st.button("💾 Зберегти зміни", key=f"save_{oid}", use_container_width=True, type="primary"):
            # Логіка збереження (як була раніше)
            df = load_csv(ORDERS_CSV_ID)
            id_col_db = get_id_column_name(df)
            indices = df.index[df[id_col_db].astype(str) == oid].tolist()
            if indices:
                idx = indices[0]
                df.at[idx, 'client_name'] = f_name
                df.at[idx, 'client_phone'] = f_phone
                df.at[idx, 'address'] = f_addr
                df.at[idx, 'product'] = f_prod
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

    # Шапка таблиці без джерела
    st.markdown("""
    <div style="display: flex; font-weight: bold; border-bottom: 1px solid #444; padding-bottom: 5px; margin-bottom: 10px; font-size: 13px; color: #888;">
        <div style="flex: 0.5;">ID</div>
        <div style="flex: 1;">Дата</div>
        <div style="flex: 1;">Статус</div>
        <div style="flex: 2;">Клієнт</div>
        <div style="flex: 2;">Товар</div>
        <div style="flex: 1; text-align: right;">Сума</div>
    </div>
    """, unsafe_allow_html=True)

    for _, row in df.iterrows():
        render_order_card(row)
