import streamlit as st

# Цей блок допоможе вивести помилку на екран, якщо вона є
try:
    from modules.auth import check_auth, login_screen, logout
    from modules.styles import apply_custom_styles
    from modules.db.view import show_order_cards
    from modules.db.create import show_create_order
    from modules.admin_module import show_admin_panel
except Exception as e:
    st.error(f"Помилка завантаження модулів: {e}")
    st.stop()

# Далі ваш стандартний код...
st.set_page_config(page_title="GETMANN Pro", layout="wide")

if not check_auth():
    login_screen()
    st.stop()

def render_order_card(order):
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    container = st.container(border=True)
    
    # Головний рядок картки
    c1, c2, c3, c4 = container.columns([0.5, 1, 2, 1])
    c1.markdown(f"**№{oid}**")
    c2.caption(order.get('date', '---'))
    c3.markdown(f"👤 **{order.get('client_name', '---')}**")
    c4.markdown(f"**{order.get('total', 0)} грн**")

    with container.expander("🛠 Товари, Ціни та Креслення"):
        # 1. Дані клієнта
        col_n, col_p = st.columns(2)
        f_name = col_n.text_input("ПІБ", value=str(order.get('client_name', '')), key=f"n_{oid}")
        f_phone = col_p.text_input("Телефон", value=str(order.get('client_phone', '')), key=f"p_{oid}")
        f_addr = st.text_input("Адреса", value=str(order.get('address', '')), key=f"a_{oid}")
        
        st.divider()

        # 2. Розширена таблиця товарів
        st.markdown("##### 📦 Склад замовлення")
        
        raw_items = order.get('items_json', '[]')
        try:
            items_data = json.loads(raw_items) if isinstance(raw_items, str) and raw_items.startswith('[') else []
        except:
            items_data = []
            
        # Якщо даних немає, створюємо структуру з існуючих полів
        if not items_data:
            items_data = [{
                "Товар": order.get('product', ''), 
                "Артикул": order.get('sku', ''),
                "К-сть": 1,
                "Ціна": float(order.get('total', 0))
            }]

        df_items = pd.DataFrame(items_data)

        # РЕДАКТОР ТАБЛИЦІ ТОВАРІВ
        edited_df = st.data_editor(
            df_items,
            num_rows="dynamic",
            column_config={
                "Товар": st.column_config.TextColumn("Найменування", width="large", required=True),
                "Артикул": st.column_config.TextColumn("SKU (Креслення)", width="small", required=True),
                "К-сть": st.column_config.NumberColumn("К-сть", min_value=1, default=1, width="small"),
                "Ціна": st.column_config.NumberColumn("Ціна за од.", min_value=0, format="%d грн", width="small"),
            },
            key=f"ed_{oid}",
            use_container_width=True
        )

        # 3. АВТОМАТИЧНИЙ РОЗРАХУНОК СУМИ
        # Рахуємо суму кожного рядка (Ціна * К-сть) і додаємо все разом
        if not edited_df.empty:
            calculated_total = (edited_df["Ціна"] * edited_df["К-сть"]).sum()
        else:
            calculated_total = 0.0

        st.markdown(f"### 💰 Разом до оплати: `{calculated_total} грн`")

        st.divider()

        # 4. ПОШУК КРЕСЛЕНЬ (По кожному артикулу окремо)
        st.markdown("##### 📐 Креслення")
        skus = edited_df["Артикул"].dropna().unique()
        valid_skus = [s.strip() for s in skus if str(s).strip()]
        
        if valid_skus:
            draw_cols = st.columns(4)
            for i, sku in enumerate(valid_skus):
                # Виклик функції пошуку на Google Drive
                link = get_file_link_by_name(sku)
                with draw_cols[i % 4]:
                    if link:
                        st.link_button(f"📂 {sku}", link, use_container_width=True)
                    else:
                        st.error(f"❌ {sku}")
                        st.caption("Не знайдено на Drive")
        else:
            st.info("Введіть артикул у таблицю для пошуку креслення")

        st.divider()

        # 5. Статус та Збереження
        f_status = st.selectbox("Статус", ["НОВИЙ", "В РОБОТІ", "ГОТОВО", "ВИДАНО"], 
                               index=0, key=f"st_{oid}")

        if st.button("💾 Зберегти зміни", key=f"sv_{oid}", type="primary", use_container_width=True):
            df = load_csv(ORDERS_CSV_ID)
            id_col_db = get_id_column_name(df)
            idx = df.index[df[id_col_db].astype(str) == oid].tolist()
            
            if idx:
                curr_idx = idx[0]
                df.at[curr_idx, 'client_name'] = f_name
                df.at[curr_idx, 'client_phone'] = f_phone
                df.at[curr_idx, 'address'] = f_addr
                df.at[curr_idx, 'status'] = f_status
                # Зберігаємо ПЕРЕРАХОВАНУ суму в базу
                df.at[curr_idx, 'total'] = calculated_total
                # Зберігаємо складний список товарів
                df.at[curr_idx, 'items_json'] = edited_df.to_json(orient='records', force_ascii=False)
                
                save_csv(ORDERS_CSV_ID, df)
                st.success(f"Замовлення №{oid} оновлено! Сума: {calculated_total} грн")
                st.rerun()

