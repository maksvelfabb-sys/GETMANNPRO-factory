import streamlit as st
import pandas as pd
from datetime import datetime
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID, get_file_link_by_name

def show_orders_journal():
    st.subheader("📋 Журнал замовлень")

    # 1. Завантаження даних
    df = load_csv(ORDERS_CSV_ID)
    
    if df.empty:
        st.info("Замовлень не знайдено.")
        return

    # Підготовка типів даних
    df['Кількість'] = pd.to_numeric(df['Кількість'], errors='coerce').fillna(1)
    df['Ціна за од.'] = pd.to_numeric(df['Ціна за од.'], errors='coerce').fillna(0)
    df['Сума'] = df['Кількість'] * df['Ціна за од.']
    
    # Додаємо номер замовлення, якщо його немає (індекс + 1)
    if 'Номер' not in df.columns:
        df.insert(0, 'Номер', range(1, len(df) + 1))

    # 2. Фільтрація (Пошук)
    search = st.text_input("🔍 Пошук замовлення (ім'я, товар, номер)", placeholder="Введіть дані...")
    if search:
        df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]

    # 3. Відображення карток
    # Розвертаємо список, щоб нові замовлення були зверху
    for index, row in df.iloc[::-1].iterrows():
        
        # Колір статусу для візуалізації
        status_emoji = {
            "Прийняте": "🆕",
            "У роботі": "🛠️",
            "Виконано": "✅"
        }.get(row.get('Статус', 'Прийняте'), "📄")

        # --- ШАПКА КАРТКИ (st.expander) ---
        header = f"{status_emoji} №{row['Номер']} | {row['Дата']} | {row['Замовник']} | {row['Сума']:,} ₴"
        
        with st.expander(header):
            # Внутрішня частина картки
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**🔢 Номер замовлення:** {row['Номер']}")
                st.markdown(f"**📅 Дата створення:** {row['Дата']}")
                st.markdown(f"**👤 Клієнт:** {row['Замовник']}")
                
                # --- ВИБІР СТАТУСУ ---
                current_status = row.get('Статус', 'Прийняте')
                status_options = ["Прийняте", "У роботі", "Виконано"]
                try:
                    status_idx = status_options.index(current_status)
                except:
                    status_idx = 0
                
                new_status = st.selectbox(
                    "Змінити статус", 
                    status_options, 
                    index=status_idx, 
                    key=f"status_{index}"
                )
                
                if new_status != current_status:
                    df.at[index, 'Статус'] = new_status
                    save_csv(ORDERS_CSV_ID, df)
                    st.rerun()

            with col2:
                st.markdown(f"**📦 Товар:** {row.get('Товар', 'Не вказано')}")
                sku = str(row.get('Артикул', '')).strip()
                st.markdown(f"**🆔 Артикул:** {sku}")
                st.markdown(f"**💰 Ціна за од.:** {row['Ціна за од.']:,} ₴")
                st.markdown(f"**🔢 Кількість:** {row['Кількість']}")
                st.markdown(f"### Разом: {row['Суma'] if 'Суma' in row else row['Сума']:,} ₴")

            # --- РОБОТА З АРТИКУЛОМ ---
            if sku:
                st.divider()
                st.markdown(f"🔍 **Перевірка бази креслень:**")
                link = get_file_link_by_name(sku)
                if link:
                    st.success(f"Креслення для артикула {sku} знайдено!")
                    st.link_button(f"📄 Відкрити креслення {sku}", link)
                else:
                    st.warning(f"Креслення для {sku} не знайдено в папці.")

            # --- ДОДАТКОВІ ДІЇ ---
            st.divider()
            if st.button("🗑️ Видалити замовлення", key=f"del_{index}"):
                df = df.drop(index)
                save_csv(ORDERS_CSV_ID, df)
                st.rerun()

    # Кнопка для додавання нового замовлення прямо тут (якщо потрібно)
    st.divider()
    if st.button("➕ Додати нове замовлення"):
        st.session_state.page = "create"
        st.rerun()
