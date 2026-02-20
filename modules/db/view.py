import streamlit as st
import pandas as pd
from datetime import datetime
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID, get_file_link_by_name

def show_orders_journal():
    # 1. Завантаження
    df = load_csv(ORDERS_CSV_ID)
    
    # Визначаємо структуру
    columns_list = ["Дата", "Замовник", "Товар", "Артикул", "Кількість", "Ціна за од.", "Сума", "Статус", "Коментар менеджера"]

    if df.empty or len(df.columns) < 2:
        st.info("Журнал порожній. Створіть нове замовлення.")
        return

    # --- ОЧИЩЕННЯ ВІД 'nan' ---
    # Додаємо відсутні колонки
    for col in columns_list:
        if col not in df.columns:
            df[col] = ""
    
    # Замінюємо всі типи NaN на пусті рядки або 0
    df = df.fillna("")
    df['Кількість'] = pd.to_numeric(df['Кількість'], errors='coerce').fillna(0)
    df['Ціна за од.'] = pd.to_numeric(df['Ціна за од.'], errors='coerce').fillna(0)
    
    # Виправляємо проблему з Сумою (якщо вона в базі з помилкою в назві)
    if 'Суma' in df.columns:
        df['Сума'] = pd.to_numeric(df['Суma'], errors='coerce').fillna(0)
    else:
        df['Сума'] = pd.to_numeric(df['Сума'], errors='coerce').fillna(0)
    
    # Перераховуємо суму, якщо вона 0
    df.loc[df['Сума'] == 0, 'Сума'] = df['Кількість'] * df['Ціна за од.']

    # 2. Пошук
    search = st.text_input("🔍 Пошук замовлення (ім'я, товар, номер)", placeholder="Введіть дані...")
    if search:
        # Шукаємо тільки в тих рядках, де є дані
        df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]

    # 3. Відображення карток
    # Фільтруємо зовсім пусті рядки, щоб не бачити "картки-привиди"
    df = df[df['Замовник'] != ""]

    if df.empty:
        st.warning("За вашим запитом нічого не знайдено.")
        return

    for index, row in df.iloc[::-1].iterrows():
        # Визначаємо іконку статусу
        status_map = {"Прийняте": "🆕", "У роботі": "🛠️", "Виконано": "✅"}
        current_status = str(row.get('Статус', 'Прийняте')).strip()
        if not current_status: current_status = "Прийняте"
        icon = status_map.get(current_status, "📄")

        # Формуємо заголовок (прибираємо nan через str() та strip())
        order_num = index + 1
        customer = str(row['Замовник'])
        date = str(row['Дата'])
        total = row['Сума']

        header = f"{icon} №{order_num} | {date} | {customer} | {total:,.1f} ₴"
        
        with st.expander(header):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"👤 **Клієнт:** {customer}")
                st.write(f"📅 **Дата:** {date}")
                
                # Селектбокс статусу
                st_options = ["Прийняте", "У роботі", "Виконано"]
                try:
                    idx = st_options.index(current_status)
                except:
                    idx = 0
                
                new_st = st.selectbox("Змінити статус", st_options, index=idx, key=f"st_{index}")
                if new_st != current_status:
                    df.at[index, 'Статус'] = new_st
                    save_csv(ORDERS_CSV_ID, df)
                    st.rerun()

            with col2:
                st.write(f"📦 **Товар:** {row['Товар']}")
                sku = str(row.get('Артикул', '')).strip()
                st.write(f"🆔 **Артикул:** {sku}")
                st.write(f"🔢 **Кількість:** {row['Кількість']}")
                st.write(f"💰 **Ціна:** {row['Ціна за од.']:,} ₴")
                st.markdown(f"### Разом: {total:,.1f} ₴")

            # Перевірка креслення
            if sku and sku != "nan" and sku != "":
                link = get_file_link_by_name(sku)
                if link:
                    st.success(f"✅ Креслення для {sku} знайдено")
                    st.link_button(f"🔗 Відкрити файл {sku}", link)
                else:
                    st.caption(f"❔ Креслення для {sku} не знайдено")

            if st.button("🗑 Видалити", key=f"del_{index}"):
                df = df.drop(index)
                save_csv(ORDERS_CSV_ID, df)
                st.rerun()
