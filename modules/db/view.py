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
    c2.caption(order.get('date', '---'))
    c3.markdown(f"👤 **{order.get('client_name', '---')}**")
    c4.markdown(f"**{order.get('total', 0)} грн**")

    with container.expander("🛠 Деталі замовлення та Креслення"):
        # 1. Дані клієнта
        st.markdown("##### 👤 Покупець")
        col_n, col_p = st.columns(2)
        f_name = col_n.text_input("ПІБ", value=str(order.get('client_name', '')), key=f"n_{oid}")
        f_phone = col_p.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"p_{oid}")
        f_addr = st.text_input("Адреса", value=str(order.get('address', '')), key=f"a_{oid}")
        
        st.divider()

        # 2. Таблиця Товарів та Артикулів
        st.markdown("##### 📦 Товари та Артикули")
        
        # Десеріалізація даних (якщо збережено як JSON або список)
        raw_items = order.get('items_json', '[]')
        try:
            items_data = json.loads(raw_items) if isinstance(raw_items, str) and raw_items.startswith('[') else []
        except:
            items_data = []
            
        # Якщо даних немає, створюємо структуру з існуючих полів (для міграції)
        if not items_data and order.get('product'):
            items_data = [{"Товар": order.get('product'), "Артикул": order.get('sku', '')}]

        df_items = pd.DataFrame(items_data if items_data else [{"Товар": "", "Артикул": ""}])
        
        # Редактор таблиці з двома колонками
        edited_df = st.data_editor(
            df_items,
            num_rows="dynamic",
            column_config={
                "Товар": st.column_config.TextColumn("Назва товару", width="large", required=True),
                "Артикул": st.column_config.TextColumn("Артикул (SKU)", width="medium", required=True),
            },
            key=f"ed_{oid}",
            use_container_width=True
        )

        # 3. Креслення (підтягуються автоматично для кожного артикулу в таблиці)
        st.markdown("##### 📐 Доступні креслення")
        skus = edited_df["Артикул"].dropna().unique()
        
        if len(skus) > 0:
            draw_cols = st.columns(len(skus) if len(skus) < 4 else 4)
            for i, sku in enumerate(skus):
                if sku.strip():
                    link = get_file_link_by_name(sku.strip())
                    with draw_cols[i % 4]:
                        if link:
                            st.link_button(f"📄 {sku}", link, use_container_width=True)
                        else:
                            st.caption(f"❌ {sku} (немає)")
        else:
            st.info("Додайте артикул у таблицю, щоб побачити креслення")

        st.divider()

        # 4. Статус та Збереження
        f_status = st.selectbox("Статус", ["НОВИЙ", "В РОБОТІ", "ГОТОВО", "ВИДАНО"], 
                               index=0, key=f"st_{oid}")
        f_total = st.number_input("Загальна сума", value=float(order.get('total', 0)), key=f"tot_{oid}")

        if st.button("💾 Зберегти зміни", key=f"sv_{oid}", type="primary", use_container_width=True):
            df = load_csv(ORDERS_CSV_ID)
            id_col_db = get_id_column_name(df)
            idx = df.index[df[id_col_db].astype(str) == oid].tolist()
            
            if idx:
                curr_idx = idx[0]
                # Оновлюємо основні поля
                df.at[curr_idx, 'client_name'] = f_name
                df.at[curr_idx, 'client_phone'] = f_phone
                df.at[curr_idx, 'address'] = f_addr
                df.at[curr_idx, 'status'] = f_status
                df.at[curr_idx, 'total'] = f_total
                
                # Зберігаємо товари та артикули як JSON рядок в одну колонку
                items_json = edited_df.to_json(orient='records', force_ascii=False)
                df.at[curr_idx, 'items_json'] = items_json
                
                # Для зворотної сумісності (перший товар)
                if not edited_df.empty:
                    df.at[curr_idx, 'product'] = edited_df.iloc[0]['Товар']
                    df.at[curr_idx, 'sku'] = edited_df.iloc[0]['Артикул']

                save_csv(ORDERS_CSV_ID, df)
                st.success("Замовлення оновлено!")
                st.rerun()
