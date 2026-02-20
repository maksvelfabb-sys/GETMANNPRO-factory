import streamlit as st
import pandas as pd
from modules.drive_tools import get_all_files_in_folder, load_drawing_map, save_drawing_map

def show_drawings_catalog():
    st.subheader("📁 Реєстр технічної документації")

    # 1. Завантаження даних
    drawing_map = load_drawing_map()  # Наші "підписані" імена
    all_files = get_all_files_in_folder() # Список файлів з Drive

    if not all_files:
        st.info("Папка з кресленнями порожня або недоступна.")
        return

    # 2. Обробка списку для відображення
    data_for_table = []
    for f in all_files:
        # Перевіряємо, чи є для цього файлу присвоєне ім'я в нашому CSV
        custom_name = drawing_map.get(f['id'], "---") 
        data_for_table.append({
            "Артикул / Ім'я": custom_name,
            "Назва файлу на Drive": f['name'],
            "ID файлу": f['id'],
            "Посилання": f['webViewLink']
        })

    df = pd.DataFrame(data_for_table)

    # 3. Інтерфейс
    tab1, tab2 = st.tabs(["📋 Список креслень", "⚙️ Налаштування імен"])

    with tab1:
        search = st.text_input("🔎 Пошук по списку (Артикул або назва)", "")
        if search:
            df_filtered = df[
                df["Артикул / Ім'я"].str.contains(search, case=False) | 
                df["Назва файлу на Drive"].str.contains(search, case=False)
            ]
        else:
            df_filtered = df

        # Відображення списку з кнопками
        st.data_editor(
            df_filtered,
            column_config={
                "Посилання": st.column_config.LinkColumn("Відкрити PDF", display_text="🔗 Переглянути"),
                "ID файлу": None # Приховуємо технічне поле
            },
            disabled=True,
            use_container_width=True,
            hide_index=True
        )

    with tab2:
        st.write("🔧 Тут ви можете присвоїти технічні імена файлам. Це дозволить замовленням бачити їх автоматично.")
        # Редактор для мапінгу
        mapping_editor = st.data_editor(
            df[["ID файлу", "Назва файлу на Drive", "Артикул / Ім'я"]],
            column_config={
                "ID файлу": None,
                "Назва файлу на Drive": st.column_config.TextColumn(disabled=True),
                "Артикул / Ім'я": st.column_config.TextColumn("Присвоїти SKU", help="Введіть артикул, який буде в замовленнях")
            },
            use_container_width=True,
            hide_index=True,
            key="map_edit_table"
        )

        if st.button("💾 Зберегти зміни"):
            new_map = dict(zip(mapping_editor["ID файлу"], mapping_editor["Артикул / Ім'я"]))
            # Прибираємо порожні значення
            new_map = {k: v for k, v in new_map.items() if v != "---" and v.strip() != ""}
            if save_drawing_map(new_map):
                st.success("Дані оновлено!")
                st.rerun()
