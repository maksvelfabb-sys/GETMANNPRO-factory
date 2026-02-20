import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def show_orders_journal():
    """Основна функція журналу замовлень (табличний вигляд)"""
    st.subheader("📋 Журнал замовлень")

    # 1. Завантаження даних
    df = load_csv(ORDERS_CSV_ID)
    
    if df.empty:
        st.info("Замовлень не знайдено.")
        return

    # Підготовка даних: конвертуємо в числа для розрахунків
    df['Кількість'] = pd.to_numeric(df['Кількість'], errors='coerce').fillna(0)
    df['Ціна за од.'] = pd.to_numeric(df['Ціна за од.'], errors='coerce').fillna(0)
    
    # Розрахунок суми, якщо вона ще не була порахована
    if 'Сума' not in df.columns:
        df['Сума'] = df['Кількість'] * df['Ціна за од.']
    else:
        df['Сума'] = pd.to_numeric(df['Сума'], errors='coerce').fillna(0)

    # Додаємо колонку для коментаря, якщо її немає в CSV
    if 'Коментар менеджера' not in df.columns:
        df['Коментар менеджера'] = ""

    # 2. Фільтрація та пошук
    search = st.text_input("🔎 Пошук замовника або товару")
    if search:
        df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]

    # 3. Редактор таблиці
    st.write("📝 *Редагуйте дані прямо в таблиці. Сума перераховується автоматично.*")
    
    edited_df = st.data_editor(
        df,
        column_config={
            "Дата": st.column_config.TextColumn("Дата", disabled=True),
            "Замовник": st.column_config.TextColumn("Замовник", width="medium"),
            "Товар": st.column_config.TextColumn("Товар", width="medium"),
            "Кількість": st.column_config.NumberColumn("К-сть", format="%d"),
            "Ціна за од.": st.column_config.NumberColumn("Ціна за од.", format="%.2f ₴"),
            "Сума": st.column_config.NumberColumn("Сума замовлення", help="Автоматичний розрахунок", format="%.2f ₴"),
            "Коментар менеджера": st.column_config.TextColumn("Коментар менеджера", width="large"),
            "Статус": st.column_config.SelectboxColumn(
                "Статус", 
                options=["Новий", "В роботі", "Виконано", "Очікує оплати", "Скасовано"]
            )
        },
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic", # Дозволяє додавати рядки вручну
        key="orders_editor_table"
    )

    # 4. Логіка автоперерахунку (якщо змінили ціну/кількість)
    if st.session_state.get("orders_editor_table"):
        changes = st.session_state["orders_editor_table"].get("edited_rows", {})
        for row_idx_str, updated_fields in changes.items():
            row_idx = int(row_idx_str)
            # Якщо змінили Кількість або Ціну, але не Суму — оновлюємо Суму
            if ("Кількість" in updated_fields or "Ціна за од." in updated_fields) and "Сума" not in updated_fields:
                new_qty = updated_fields.get("Кількість", edited_df.iloc[row_idx]["Кількість"])
                new_price = updated_fields.get("Ціна за од.", edited_df.iloc[row_idx]["Ціна за од."])
                edited_df.at[row_idx, "Сума"] = new_qty * new_price

    # 5. Кнопка збереження
    col_save, col_empty = st.columns([1, 4])
    with col_save:
        if st.button("💾 Зберегти зміни", type="primary", use_container_width=True):
            if save_csv(ORDERS_CSV_ID, edited_df):
                st.success("Дані збережено!")
                st.rerun()

# Для сумісності, якщо в app.py ще залишився старий виклик:
def show_order_cards():
    show_orders_journal()
