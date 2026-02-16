import streamlit as st
import pandas as pd
import json
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID, get_file_link_by_name

def get_id_column_name(df):
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

def render_order_card(order):
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    container = st.container(border=True)
    
    # Заголовок картки
    c1, c2, c3, c4 = container.columns([0.5, 1, 2, 1])
    c1.markdown(f"**№{oid}**")
    c2.caption(str(order.get('date', '---')))
    c3.markdown(f"👤 **{order.get('client_name', '---')}**")
    c4.markdown(f"**{order.get('total', 0)} грн**")

    with container.expander("🛠 Товари та Креслення"):
        col_n, col_p = st.columns(2)
        # Перетворюємо телефон на рядок відразу, щоб Pandas не сварився
        f_name = col_n.text_input("ПІБ", value=str(order.get('client_name', '')), key=f"n_{oid}")
        f_phone = col_p.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"p_{oid}")
        f_addr = st.text_input("Адреса", value=str(order.get('address', '')), key=f"a_{oid}")
        
        st.divider()

        st.markdown("##### 📦 Склад замовлення")
        raw_items = order.get('items_json', '[]')
        try:
            items_data = json.loads(raw_items) if isinstance(raw_items, str) and raw_items.startswith('[') else []
        except:
            items_data = []
            
        if not items_data:
            items_data = [{"Товар": str(order.get('product', '')), "Артикул": str(order.get('sku', '')), "К-сть": 1, "Ціна": float(order.get('total', 0))}]

        df_items = pd.DataFrame(items_data)
        
        # ОНОВЛЕНО: використовуємо width="stretch" замість use_container_width
        edited_df = st.data_editor(
            df_items,
            num_rows="dynamic",
            column_config={
                "Товар": st.column_config.TextColumn("Назва", width="large"),
                "Артикул": st.column_config.TextColumn("SKU"),
                "К-сть": st.column_config.NumberColumn("К-сть", min_value=1, default=1),
                "Ціна": st.column_config.NumberColumn("Ціна за од.", format="%d грн"),
            },
            key=f"ed_{oid}",
            width="stretch" 
        )

        # Розрахунок суми
        if not edited_df.empty:
            calc_total = (edited_df["Ціна"] * edited_df["К-сть"]).sum()
        else:
            calc_total = 0.0
            
        st.markdown(f"### 💰 Разом: `{calc_total} грн`")

        st.markdown("##### 📐 Креслення")
        skus = edited_df["Артикул"].dropna().unique()
        if any(skus):
            cols = st.columns(4)
            for i, sku in enumerate([s for s in skus if str(s).strip()]):
                link = get_file_link_by_name(sku)
                with cols[i % 4]:
                    if link:
                        st.link_button(f"📄 {sku}", link, width="stretch")
                    else:
                        st.caption(f"❌ {sku}")

        st.divider()
        f_status = st.selectbox("Статус", ["НОВИЙ", "В РОБОТІ", "ГОТОВО", "ВИДАНО"], key=f"st_{oid}")

        if st.button("💾 Зберегти", key=f"sv_{oid}", type="primary", width="stretch"):
            df = load_csv(ORDERS_CSV_ID)
            # ПРИМУСОВО перетворюємо колонки на об'єкти (рядки), щоб не було помилок dtype
            df['client_phone'] = df['client_phone'].astype(str)
            df['client_name'] = df['client_name'].astype(str)
            
            id_col_db = get_id_column_name(df)
            idx = df.index[df[id_col_db].astype(str) == oid].tolist()
            
            if idx:
                curr_idx = idx[0]
                df.at[curr_idx, 'client_name'] = f_name
                df.at[curr_idx, 'client_phone'] = str(f_phone) # Явне перетворення
                df.at[curr_idx, 'address'] = f_addr
                df.at[curr_idx, 'status'] = f_status
                df.at[curr_idx, 'total'] = calc_total
                df.at[curr_idx, 'items_json'] = edited_df.to_json(orient='records', force_ascii=False)
                
                save_csv(ORDERS_CSV_ID, df)
                st.success("Дані збережено!")
                st.rerun()

def show_order_cards():
    df = load_csv(ORDERS_CSV_ID)
    if not df.empty:
        # Видаляємо порожні рядки, щоб не було помилок при рендері
        df = df.dropna(subset=['client_name'], how='all')
        for _, row in df.iterrows():
            render_order_card(row)
