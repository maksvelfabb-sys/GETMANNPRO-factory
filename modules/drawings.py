import streamlit as st
import pandas as pd
from modules.drive_tools import get_all_files_in_folder, load_drawing_map, save_drawing_map

def handle_save():
    """Обробник автоматичного збереження при зміні даних у таблиці"""
    # Отримуємо зміни з editor_key
    if "drawings_editor" in st.session_state:
        changes = st.session_state["drawings_editor"].get("edited_rows", {})
        if changes:
            # Завантажуємо поточну карту імен
            current_map = load_drawing_map()
            # Отримуємо поточний список файлів з сесії, щоб знайти file_id за індексом рядка
            df = st.session_state["current_df"]
            
            for row_idx, updated_fields in changes.items():
                if "Ім'я (опис)" in updated_fields:
                    file_id = df.iloc[int(row_idx)]["file_id"]
                    new_name = updated_fields["Ім'я (опис)"]
                    current_map[str(file_id)] = str(new_name)
            
            save_drawing_map(current_map)

def show_drawings_catalog():
    st.subheader("📐 Реєстр технічної документації")

    # 1. Отримуємо дані
    all_files = get_all_files_in_folder()
    drawing_names_map = load_drawing_map()

    if not all_files:
        st.info("Папка Drive порожня або ID папки вказано невірно.")
        return

    # 2. Формуємо DataFrame
    data = []
    for f in all_files:
        # Артикул — це назва файлу, яку неможливо змінити тут
        sku = f['name'].rsplit('.', 1)[0]
        data.append({
            "Ім'я (опис)": drawing_names_map.get(f['id'], ""),
            "Артикул": sku,
            "Файл": f.get('webViewLink', '#'),
            "file_id": f['id']
        })

    df = pd.DataFrame(data)
    # Зберігаємо в session_state для обробника handle_save
    st.session_state["current_df"] = df

    # 3. Пошук
    search = st.text_input("🔎 Пошук за артикулом або описом", placeholder="Введіть SKU...")
    
    if search:
        df_display = df[
            df["Артикул"].str.contains(search, case=False) | 
            df["Ім'я (опис)"].str.contains(search, case=False)
        ]
    else:
        df_display = df

    # 4. Основна таблиця
    st.write("📝 *Для зміни імені просто відредагуйте клітинку та натисніть Enter*")
    
    st.data_editor(
        df_display,
        column_config={
            "Ім'я (опис)": st.column_config.TextColumn(
                "Ім'я (опис)", 
                help="Натисніть для редагування",
                width="large"
            ),
            "Артикул": st.column_config.TextColumn(
                "Артикул (File Name)", 
                disabled=True, # Змінити неможливо
                width="medium"
            ),
            "Файл": st.column_config.LinkColumn(
                "Креслення", 
                display_text="🔗 Відкрити"
            ),
            "file_id": None # Технічне поле приховано
        },
        use_container_width=True,
        hide_index=True,
        key="drawings_editor",
        on_change=handle_save # Викликає збереження автоматично
    )

    st.caption(f"Синхронізовано файлів: {len(df)}")
