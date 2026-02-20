import streamlit as st
import pandas as pd
from datetime import datetime
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def show_orders_journal():
    st.subheader("📋 Журнал замовлень")

    # 1. Завантаження даних
    df = load_csv(ORDERS_CSV_ID)
    
    columns_list = ["Дата", "Замовник", "Товар", "Кількість", "Ціна за од.", "Сума", "Статус", "Коментар менеджера"]

    if df.empty or len(df.columns) < 2:
        df = pd.DataFrame(columns=columns_list)
        save_csv(ORDERS_CSV_ID, df)
        st.rerun()

    # --- КРИТИЧНЕ ВИПРАВЛЕННЯ ТИПІВ ДАНИХ ---
    for col in columns_list:
        if col not in df.columns:
            df[col] = ""
    
    # Перетворюємо на числа і ЗАМІНЯЄМО все, що не число, на 0.0
    # Це гарантує, що st.data_editor не отримає текст там, де чекає число
    df['Кількість'] = pd.to_numeric(df['Кількість'], errors='coerce').fillna(0).astype(float)
    df['Ціна за од.'] = pd.to_numeric(df['Ціна за од.'], errors='coerce').fillna(0).astype(float)
    df['Сума'] = pd.to_numeric(df['Сума'], errors='coerce').fillna(0).astype(float)

    # 2. Пошук
    search = st.text_input("🔎 Пошук у журналі", placeholder="Введіть дані...")
    df_display = df.copy()
    if search:
        # Шукаємо тільки по текстових колонках, щоб уникнути помилок порівняння
        mask = df_display.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        df_display = df_display[mask]

    # 3. Редактор таблиці
    # Важливо: використовуємо .copy(), щоб уникнути SettingWithCopyWarning
    edited_df = st.data_editor(
        df_display,
        column_config={
            "Дата": st.column_config.TextColumn("Дата"),
            "Замовник": st.column_config.TextColumn("Замовник"),
            "Товар": st.column_config.TextColumn("Товар"),
            "Кількість": st.column_config.NumberColumn("К-сть", format="%d", min_value=0),
            "Ціна за од.": st.column_config.NumberColumn("Ціна, ₴", format="%.2f"),
            "Сума": st.column_config.NumberColumn("Всього, ₴", format="%.2f", disabled=True),
            "Статус": st.column_config.SelectboxColumn(
                "Статус", 
                options=["Новий", "В роботі", "Виконано", "Очікує оплати", "Скасовано"]
            ),
            "Коментар менеджера": st.column_config.TextColumn("Коментар", width="large")
        },
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="orders_editor_v4"
    )

    # 4. Збереження
    if st.button("💾 Зберегти зміни", type="primary"):
        # Обробка дат для нових рядків
        if "Дата" in edited_df.columns:
            today = datetime.now().strftime("%d.%m.%Y")
            # Замінюємо пусті значення на сьогоднішню дату
            edited_df["Дата"] = edited_df["Дата"].apply(lambda x: today if str(x).strip() in ["", "None", "nan"] else x)

        # Перерахунок суми
        edited_df['Сума'] = edited_df['Кількість'] * edited_df['Ціна за од.']
        
        # Об'єднуємо зміни з основним файлом, якщо був пошук
        if search:
            # Використовуємо індекси для точного оновлення
            df.loc[edited_df.index, :] = edited_df
            final_to_save = df
        else:
            final_to_save = edited_df

        if save_csv(ORDERS_CSV_ID, final_to_save):
            st.success("✅ Журнал оновлено!")
            st.rerun()

    # Підсумок
    if not edited_df.empty:
        st.write(f"💰 **Разом за списком:** {edited_df['Сума'].sum():,.2f} ₴")
