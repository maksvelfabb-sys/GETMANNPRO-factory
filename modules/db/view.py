import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def show_orders_journal():
    st.subheader("📋 Журнал замовлень")

    # 1. Завантаження даних
    df_orders = load_csv(ORDERS_CSV_ID)
    
    if df_orders.empty:
        st.info("Замовлень поки немає.")
        return

    # Переконуємося, що типи даних вірні для розрахунків
    df_orders['Кількість'] = pd.to_numeric(df_orders['Кількість'], errors='coerce').fillna(0)
    df_orders['Ціна за од.'] = pd.to_numeric(df_orders['Ціна за од.'], errors='coerce').fillna(0)
    
    # Автоматичний розрахунок суми (якщо стовпчик порожній або для нових рядків)
    df_orders['Сума'] = df_orders['Кількість'] * df_orders['Ціна за од.']

    # 2. Фільтри для зручності
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("🔍 Пошук (Замовник, Товар, Номер)", placeholder="Введіть дані...")
    with col2:
        status_filter = st.multiselect("Статус", options=df_orders['Статус'].unique())

    # Фільтрація
    df_display = df_orders.copy()
    if search:
        df_display = df_display[df_display.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
    if status_filter:
        df_display = df_display[df_display['Статус'].isin(status_filter)]

    # 3. Редактор замовлень
    st.write("📝 *Редагуйте будь-яку клітинку. Сума перераховується автоматично при зміні ціни або кількості.*")
    
    edited_df = st.data_editor(
        df_display,
        column_config={
            "Товар": st.column_config.TextColumn("Товар", width="medium"),
            "Кількість": st.column_config.NumberColumn("К-сть", min_value=0, format="%d"),
            "Ціна за од.": st.column_config.NumberColumn("Ціна за од.", format="%.2f ₴"),
            "Сума": st.column_config.NumberColumn("Загальна сума", help="Можна змінити вручну, якщо є знижка", format="%.2f ₴"),
            "Коментар менеджера": st.column_config.TextColumn("Коментар менеджера", width="large", placeholder="Додайте примітку..."),
            "Статус": st.column_config.SelectboxColumn("Статус", options=["Новий", "В роботі", "Очікує оплати", "Виконано", "Скасовано"]),
            "Дата": st.column_config.DateColumn("Дата", disabled=True)
        },
        num_rows="dynamic", # Дозволяє додавати/видаляти замовлення прямо тут
        use_container_width=True,
        hide_index=True,
        key="orders_editor"
    )

    # 4. Логіка автоматичного перерахунку суми при редагуванні
    # Якщо змінили Кількість або Ціну, оновлюємо Суму в реальному часі
    if st.session_state.get("orders_editor"):
        changes = st.session_state["orders_editor"].get("edited_rows", {})
        for row_idx, updated_fields in changes.items():
            # Якщо змінили ціну або кількість, але НЕ чіпали суму вручну — перераховуємо
            if ("Кількість" in updated_fields or "Ціна за од." in updated_fields) and "Сума" not in updated_fields:
                row = edited_df.iloc[int(row_idx)]
                edited_df.at[int(row_idx), "Сума"] = row["Кількість"] * row["Ціна за од."]

    # 5. Кнопка збереження
    if st.button("💾 Зберегти зміни в журналі", type="primary"):
        # Оновлюємо основний DataFrame зміненими даними
        # (Тут важливо правильно змерджити зміни, якщо був пошук)
        if save_csv(ORDERS_CSV_ID, edited_df):
            st.success("✅ Журнал замовлень оновлено!")
            st.rerun()

    # Підсумок
    total_revenue = edited_df['Сума'].sum()
    st.metric("Загальна вартість обраних замовлень", f"{total_revenue:,.2f} ₴")
