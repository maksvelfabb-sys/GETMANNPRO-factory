import streamlit as st
import pandas as pd
from datetime import datetime
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def show_orders_journal():
    # 1. Завантаження та підготовка даних
    df = load_csv(ORDERS_CSV_ID)
    
    if df.empty:
        st.info("Замовлень поки немає. Створіть перше замовлення!")
        return

    # Очищення даних
    df['Кількість'] = pd.to_numeric(df['Кількість'], errors='coerce').fillna(0)
    df['Ціна за од.'] = pd.to_numeric(df['Ціна за од.'], errors='coerce').fillna(0)
    df['Сума'] = df['Кількість'] * df['Ціна за од.']
    df = df.fillna("")

    # 2. Фільтри та Пошук (у верхній панелі)
    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        search = st.text_input("🔎 Пошук замовника або товару", placeholder="Кого шукаємо?")
    with col_s2:
        status_list = ["Всі"] + list(df['Статус'].unique())
        status_filter = st.selectbox("Фільтр статусу", status_list)

    # Фільтрація даних
    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[filtered_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
    if status_filter != "Всі":
        filtered_df = filtered_df[filtered_df['Статус'] == status_filter]

    # 3. Відображення карток
    st.write(f"Знайдено замовлень: **{len(filtered_df)}**")
    st.divider()

    # Створюємо сітку карток (по 2 в ряд на широкому екрані)
    for index, row in filtered_df.iterrows():
        # Визначаємо колір статусу
        status_colors = {
            "Новий": "🔵",
            "В роботі": "🟡",
            "Виконано": "🟢",
            "Очікує оплати": "🟠",
            "Скасовано": "🔴"
        }
        icon = status_colors.get(row['Статус'], "⚪")

        # Сама картка
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            
            with c1:
                st.markdown(f"### {icon} {row['Замовник']}")
                st.caption(f"📅 Дата: {row['Дата']}")
                st.markdown(f"**Товар:** {row['Товар']}")
            
            with c2:
                st.write(f"**Кількість:** {int(row['Кількість'])} шт.")
                st.write(f"**Ціна:** {row['Ціна за од.']:,} ₴")
                st.markdown(f"#### Сума: {row['Сума']:,} ₴")
            
            with c3:
                # Кнопка для відкриття редагування конкретного замовлення
                if st.button("📝 Редагувати", key=f"edit_{index}"):
                    edit_order_modal(index, row, df)

            if row['Коментар менеджера']:
                st.info(f"💬 {row['Коментар менеджера']}")

# Функція для редагування (викликається всередині картки)
def edit_order_modal(index, row, full_df):
    with st.expander(f"Змінити замовлення: {row['Замовник']}", expanded=True):
        with st.form(key=f"form_{index}"):
            new_customer = st.text_input("Замовник", value=row['Замовник'])
            new_item = st.text_input("Товар", value=row['Товар'])
            
            col_a, col_b = st.columns(2)
            with col_a:
                new_qty = st.number_input("Кількість", value=float(row['Кількість']), step=1.0)
                new_status = st.selectbox("Статус", 
                                        ["Новий", "В роботі", "Виконано", "Очікує оплати", "Скасовано"],
                                        index=["Новий", "В роботі", "Виконано", "Очікує оплати", "Скасовано"].index(row['Статус']) if row['Статус'] in ["Новий", "В роботі", "Виконано", "Очікує оплати", "Скасовано"] else 0)
            with col_b:
                new_price = st.number_input("Ціна за од.", value=float(row['Ціна за од.']))
                new_comment = st.text_area("Коментар менеджера", value=row['Коментар менеджера'])

            if st.form_submit_button("💾 Оновити дані замовлення"):
                # Оновлюємо рядок у великому DataFrame
                full_df.at[index, 'Замовник'] = new_customer
                full_df.at[index, 'Товар'] = new_item
                full_df.at[index, 'Кількість'] = new_qty
                full_df.at[index, 'Ціна за од.'] = new_price
                full_df.at[index, 'Статус'] = new_status
                full_df.at[index, 'Коментар менеджера'] = new_comment
                full_df.at[index, 'Сума'] = new_qty * new_price
                
                if save_csv(ORDERS_CSV_ID, full_df):
                    st.success("Зміни збережено!")
                    st.rerun()
