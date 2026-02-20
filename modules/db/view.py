import streamlit as st
import pandas as pd
from datetime import datetime
from modules.drive_tools import (
    load_csv, save_csv, ORDERS_CSV_ID, ITEMS_CSV_ID, get_file_link_by_name
)

def show_orders_journal():
    # 1. Завантаження даних з ПРИМУСОВИМ форматом тексту для Телефону
    # Ми передаємо dtype={'Телефон': str}, щоб Pandas не перетворював його на число
    df_orders = load_csv(ORDERS_CSV_ID)
    df_items = load_csv(ITEMS_CSV_ID)

    # Еталонний список колонок (має збігатися з orders_header.csv)
    columns_list = [
        "Дата", "Номер замовлення", "Замовник", "Телефон", 
        "Товар", "Артикул", "Кількість", "Ціна за од.", 
        "Сума", "Статус", "Коментар менеджера"
    ]

    if df_orders.empty:
        st.info("Журнал порожній. Створіть замовлення.")
        # Якщо файл зовсім порожній, ініціалізуємо його правильною структурою
        if st.button("Ініціалізувати структуру файлу"):
            empty_df = pd.DataFrame(columns=columns_list)
            save_csv(ORDERS_CSV_ID, empty_df)
            st.rerun()
        return

    # Гарантуємо наявність всіх колонок та правильні типи
    for col in columns_list:
        if col not in df_orders.columns:
            df_orders[col] = ""

    # Примусова конвертація: Телефон -> Текст, Математика -> Числа
    df_orders['Телефон'] = df_orders['Телефон'].astype(str).replace(['nan', 'None', 'NaN'], '')
    df_orders['Кількість'] = pd.to_numeric(df_orders['Кількість'], errors='coerce').fillna(0)
    df_orders['Ціна за од.'] = pd.to_numeric(df_orders['Ціна за од.'], errors='coerce').fillna(0)
    df_orders['Сума'] = pd.to_numeric(df_orders['Сума'], errors='coerce').fillna(0)

    # 2. Фільтрація
    search = st.text_input("🔍 Пошук", placeholder="Ім'я, телефон або артикул...")
    display_df = df_orders.copy()
    if search:
        display_df = display_df[display_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]

    # 3. Відображення карток
    for index, row in display_df.iloc[::-1].iterrows():
        status = str(row.get('Статус', 'Прийняте')).strip() or "Прийняте"
        status_emoji = {"Прийняте": "🔵", "У роботі": "🟡", "Виконано": "🟢"}.get(status, "⚪")
        
        # Шапка картки згідно вашого запиту
        header = f"{status_emoji} №{row['Номер замовлення']} | {row['Дата']} | {row['Замовник']} | {row['Сума']:,.2f} ₴"
        
        with st.expander(header):
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown(f"**👤 Клієнт:** {row['Замовник']}")
                # Вивід телефону як тексту
                st.markdown(f"**📞 Телефон:** `{row['Телефон']}`")
                st.markdown(f"**📅 Дата:** {row['Дата']}")
                
                # Зміна статусу
                new_status = st.selectbox(
                    "Змінити статус", ["Прийняте", "У роботі", "Виконано"], 
                    index=["Прийняте", "У роботі", "Виконано"].index(status) if status in ["Прийняте", "У роботі", "Виконано"] else 0,
                    key=f"status_{index}"
                )
                if new_status != status:
                    df_orders.at[index, 'Статус'] = new_status
                    save_csv(ORDERS_CSV_ID, df_orders)
                    st.rerun()

            with c2:
                st.markdown(f"**📦 Товар:** {row['Товар']}")
                sku = str(row.get('Артикул', '')).strip()
                st.markdown(f"**🆔 Артикул:** `{sku}`")
                st.markdown(f"**🔢 Кількість:** {int(row['Кількість'])} шт.")
                st.markdown(f"**💰 Ціна за од.:** {row['Ціна за од.']:,} ₴")
                st.markdown(f"### Разом: {row['Сума']:,} ₴")

            # Перевірка креслення
            if sku:
                st.divider()
                link = get_file_link_by_name(sku)
                if link:
                    st.success(f"✅ Креслення {sku} знайдено")
                    st.link_button(f"📄 Відкрити креслення", link)
                else:
                    st.caption(f"❔ Креслення для {sku} не знайдено")

            # Додавання товару (Пункт 3 плану)
            st.divider()
            with st.status("➕ Додати товар до цього замовлення", expanded=False):
                if not df_items.empty:
                    sel_item = st.selectbox("Оберіть товар", df_items['Назва'].unique(), key=f"add_it_{index}")
                    item_data = df_items[df_items['Назва'] == sel_item].iloc[0]
                    
                    add_q = st.number_input("К-сть", min_value=1, value=1, key=f"add_q_{index}")
                    add_p = st.number_input("Ціна", value=float(item_data.get('Ціна', 0)), key=f"add_p_{index}")
                    
                    if st.button("➕ Додати", key=f"btn_add_{index}"):
                        new_row = row.copy()
                        new_row['Товар'] = sel_item
                        new_row['Артикул'] = item_data.get('Артикул', '')
                        new_row['Кількість'] = add_q
                        new_row['Ціна за од.'] = add_p
                        new_row['Сума'] = add_q * add_p
                        
                        df_orders = pd.concat([df_orders, pd.DataFrame([new_row])], ignore_index=True)
                        save_csv(ORDERS_CSV_ID, df_orders)
                        st.rerun()

            if st.button("🗑 Видалити", key=f"del_{index}"):
                df_orders = df_orders.drop(index)
                save_csv(ORDERS_CSV_ID, df_orders)
                st.rerun()
