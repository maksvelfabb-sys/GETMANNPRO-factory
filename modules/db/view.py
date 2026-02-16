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
        # Заголовок картки (верхній рядок)
        c1, c2, c3, c4 = st.columns([0.6, 1, 2, 1])
        c1.markdown(f"### №{oid}")
        c2.caption(f"📅 {order.get('date', '---')}")
        c3.markdown(f"👤 **{order.get('client_name', '---')}**")
        c4.markdown(f"💰 **{order.get('total', 0)} грн**")

        # Розгортання деталей
        with st.expander("📝 Редагувати замовлення та Креслення"):
            col_n, col_p = st.columns(2)
            f_name = col_n.text_input("ПІБ", value=str(order.get('client_name', '')), key=f"n_{oid}")
            f_phone = col_p.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"p_{oid}")
            f_addr = st.text_input("Адреса", value=str(order.get('address', '')), key=f"a_{oid}")
            
            st.divider()

            # Обробка даних товарів (JSON)
            raw_items = order.get('items_json', '[]')
            try:
                items_data = json.loads(raw_items) if isinstance(raw_items, str) and raw_items.startswith('[') else []
            except:
                items_data = []
                
            if not items_data:
                items_data = [{
                    "Товар": str(order.get('product', '---')), 
                    "Артикул": str(order.get('sku', '')), 
                    "К-сть": 1, 
                    "Ціна": float(order.get('total', 0))
                }]

            df_items = pd.DataFrame(items_data)

            # --- ФІКС ПОМИЛКИ 'Ціна' (Case-insensitive) ---
            rename_map = {
                'ціна': 'Ціна', 'price': 'Ціна',
                'товар': 'Товар', 'product': 'Товар',
                'артикул': 'Артикул', 'sku': 'Артикул',
                'к-сть': 'К-сть', 'quantity': 'К-сть'
            }
            df_items.columns = [rename_map.get(c.lower(), c) for c in df_items.columns]
            
            # Гарантуємо наявність необхідних колонок
            if 'Ціна' not in df_items.columns: df_items['Ціна'] = 0.0
            if 'К-сть' not in df_items.columns: df_items['К-сть'] = 1

            # Редактор таблиці товарів
            edited_df = st.data_editor(
                df_items,
                num_rows="dynamic",
                column_config={
                    "Товар": st.column_config.TextColumn("Назва", width="large"),
                    "Ціна": st.column_config.NumberColumn("Ціна за од.", format="%d грн"),
                },
                key=f"ed_{oid}",
                width="stretch" 
            )

            # Розрахунок суми
            calc_total = 0.0
            if not edited_df.empty:
                p = pd.to_numeric(edited_df["Ціна"], errors='coerce').fillna(0)
                q = pd.to_numeric(edited_df["К-сть"], errors='coerce').fillna(0)
                calc_total = (p * q).sum()

            st.markdown(f"#### 💰 Разом: `{calc_total} грн`")

            # Креслення (Drive API)
            st.markdown("##### 📐 Креслення")
            skus = [s for s in edited_df["Артикул"].dropna().unique() if str(s).strip()]
            if skus:
                draw_cols = st.columns(4)
                for i, sku in enumerate(skus):
                    link = get_file_link_by_name(sku)
                    with draw_cols[i % 4]:
                        if link:
                            st.link_button(f"📄 {sku}", link, width="stretch")
                        else:
                            st.caption(f"❌ {sku}")
            else:
                st.caption("Артикули не вказані")

            st.divider()
            
            # Статус та Збереження
            c_status, c_save = st.columns([2, 1])
            f_status = c_status.selectbox(
                "Статус", ["НОВИЙ", "В РОБОТІ", "ГОТОВО", "ВИДАНО"], 
                index=["НОВИЙ", "В РОБОТІ", "ГОТОВО", "ВИДАНО"].index(order.get('status', 'НОВИЙ')),
                key=f"st_{oid}"
            )

            if c_save.button("💾 Зберегти", key=f"sv_{oid}", type="primary", width="stretch"):
                # Завантаження поточної бази для оновлення
