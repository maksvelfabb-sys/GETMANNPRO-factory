import streamlit as st
import pandas as pd
import json
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID, get_file_link_by_name

def get_id_column_name(df):
    """Визначає назву колонки ID"""
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

def render_order_card(order):
    """Відображає окрему картку замовлення"""
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    with st.container(border=True):
        # Заголовок картки
        c1, c2, c3, c4 = st.columns([0.6, 1, 2, 1])
        c1.markdown(f"### №{oid}")
        c2.caption(f"📅 {order.get('date', '---')}")
        c3.markdown(f"👤 **{order.get('client_name', '---')}**")
        c4.markdown(f"💰 **{order.get('total', 0)} грн**")

        with st.expander("📝 Редагувати та креслення"):
            col_n, col_p = st.columns(2)
            f_name = col_n.text_input("ПІБ", value=str(order.get('client_name', '')), key=f"n_{oid}")
            f_phone = col_p.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"p_{oid}")
            f_addr = st.text_input("Адреса", value=str(order.get('address', '')), key=f"a_{oid}")
            
            st.divider()

            # Склад замовлення
            raw_items = order.get('items_json', '[]')
            try:
                items_data = json.loads(raw_items) if isinstance(raw_items, str) and raw_items.startswith('[') else []
            except:
                items_data = []
                
            if not items_data:
                items_data = [{"Товар": str(order.get('product', '')), "Артикул": str(order.get('sku', '')), "К-сть": 1, "Ціна": float(order.get('total', 0))}]

            df_items = pd.DataFrame(items_data)
            
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
            calc_total = (edited_df["Ціна"] * edited_df["К-сть"]).sum() if not edited_df.empty else 0.0
            st.markdown(f"**Підсумок: `{calc_total} грн`**")

            # Креслення
            st.markdown("##### 📐 Креслення")
            skus = [s for s in edited_df["Артикул"].dropna().unique() if str(s).strip()]
            if skus:
                cols = st.columns(4)
                for i, sku in enumerate(skus):
                    link = get_file_link_by_name(sku)
                    with cols[i % 4]:
                        if link:
                            st.link_button(f"📄 {sku}", link, width="stretch")
                        else:
                            st.caption(f"❌ {sku}")

            st.divider()
            f_status = st.selectbox("Статус", ["НОВИЙ", "В РОБОТІ", "ГОТОВО", "ВИДАНО"], 
                                     index=["НОВИЙ", "В РОБОТІ", "ГОТОВО", "ВИДАНО"].index(order.get('status', 'НОВИЙ')),
                                     key=f"st_{oid}")

            if st.button("💾 Зберегти", key=f"sv_{oid}", type="primary", width="stretch"):
                # Логіка збереження
                df_all = load_csv(ORDERS_CSV_ID)
                for col in ['client_name', 'client_phone', 'address', 'status']:
                    if col in df_all.columns:
                        df_all[col] = df_all[col].astype(str)
                
                idx = df_all.index[df_all[id_col].astype(str) == oid].tolist()
                if idx:
                    i = idx[0]
                    df_all.at[i, 'client_name'] = f_name
                    df_all.at[i, 'client_phone'] = str(f_phone)
                    df_all.at[i, 'address'] = f_addr
                    df_all.at[i, 'status'] = f_status
                    df_all.at[i, 'total'] = calc_total
                    df_all.at[i, 'items_json'] = edited_df.to_json(orient='records', force_ascii=False)
                    save_csv(ORDERS_CSV_ID, df_all)
                    st.success("Оновлено!")
                    st.rerun()

# ОСНОВНА ФУНКЦІЯ, ЯКУ ШУКАЄ APP.PY
def show_order_cards():
    """Відображає всі картки замовлень"""
    df = load_csv(ORDERS_CSV_ID)
    if not df.empty:
        # Прибираємо порожні рядки
        df = df.dropna(subset=['client_name'], how='all')
        for _, row in df.iterrows():
            try:
                render_order_card(row)
            except Exception as e:
                st.error(f"Помилка в замовленні: {e}")
    else:
        st.info("Замовлення не знайдені.")
