import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID
# Припускаємо, що функція get_file_link_by_name з'явиться в drive_tools
from modules.drive_tools import get_file_link_by_name 

def get_id_column_name(df):
    return next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')

def render_order_card(order):
    id_col = get_id_column_name(pd.DataFrame([order]))
    oid = str(order.get(id_col, '0'))
    
    container = st.container(border=True)
    # Візуальний ряд (ID, Дата, Статус, Клієнт, Сума)
    cols = container.columns([0.5, 1, 1, 2, 1])
    cols[0].write(f"**{oid}**")
    cols[1].write(order.get('date', '---'))
    cols[2].info(order.get('status', 'Новий'))
    cols[3].write(f"👤 {order.get('client_name', '---')}")
    cols[4].write(f"**{order.get('total', 0)}**")

    with container.expander("🛠 Керування товарами та кресленнями"):
        # --- БЛОК ТОВАРІВ ---
        st.markdown("##### 🛒 Список товарів")
        
        # Перетворюємо рядок з товарами у список для редактора (якщо вони збережені через розділювач)
        raw_products = str(order.get('product', ''))
        product_list = [p.strip() for p in raw_products.split(',')] if raw_products else []
        
        # Створюємо тимчасову таблицю для редагування
        items_df = pd.DataFrame({"Назва товару": product_list})
        
        # РЕДАКТОР ТАБЛИЦІ (Тут можна додавати рядки через "+")
        edited_items = st.data_editor(
            items_df, 
            num_rows="dynamic", 
            key=f"editor_{oid}",
            use_container_width=True
        )
        
        # --- БЛОК КРЕСЛЕНЬ ---
        st.divider()
        st.markdown("##### 📐 Креслення за артикулом")
        sku = st.text_input("Введіть артикул (SKU) для пошуку", value=str(order.get('sku', '')), key=f"sku_{oid}")
        
        if sku:
            # Спроба знайти посилання на файл на Google Drive
            file_link = get_file_link_by_name(sku)
            if file_link:
                st.success(f"✅ Креслення для {sku} знайдено")
                st.link_button("📂 Відкрити креслення", file_link, use_container_width=True)
            else:
                st.warning("⚠️ Креслення з такою назвою не знайдено на Drive")
        
        # --- ЗБЕРЕЖЕННЯ ---
        if st.button("💾 Зберегти все", key=f"save_{oid}", type="primary", use_container_width=True):
            df = load_csv(ORDERS_CSV_ID)
            id_col_db = get_id_column_name(df)
            idx = df.index[df[id_col_db].astype(str) == oid].tolist()
            
            if idx:
                # Збираємо товари назад у рядок через кому
                new_products = ", ".join(edited_items["Назва товару"].tolist())
                df.at[idx[0], 'product'] = new_products
                df.at[idx[0], 'sku'] = sku
                # Тут можна додати оновлення інших полів...
                
                save_csv(ORDERS_CSV_ID, df)
                st.success("Оновлено!")
                st.rerun()

def show_order_cards():
    df = load_csv(ORDERS_CSV_ID)
    if not df.empty:
        for _, row in df.iterrows():
            render_order_card(row)
