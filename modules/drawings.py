import streamlit as st
import pandas as pd
from modules.drive_tools import get_all_files_in_folder, load_drawing_map, save_drawing_map

def handle_save():
    """Надійний обробник збереження"""
    if "drawings_editor" in st.session_state and "current_display_df" in st.session_state:
        changes = st.session_state["drawings_editor"].get("edited_rows", {})
        if not changes:
            return

        # Беремо таблицю, яка БУЛА на екрані в момент редагування
        df_visible = st.session_state["current_display_df"]
        current_map = load_drawing_map()
        
        has_updates = False
        for row_idx_str, updated_fields in changes.items():
            if "Ім'я (опис)" in updated_fields:
                row_idx = int(row_idx_str)
                # Отримуємо ID файлу саме з того рядка, який бачив користувач
                file_id = df_visible.iloc[row_idx]["file_id"]
                new_name = updated_fields["Ім'я (опис)"]
                current_map[str(file_id)] = str(new_name)
                has_updates = True
        
        if has_updates:
            save_drawing_map(current_map)
            # Не викликаємо rerun тут, щоб не переривати потік введення

def show_drawings_catalog():
    st.subheader("📐 Реєстр технічної документації")

    # 1. Отримуємо дані з Drive
    all_files = get_all_files_in_folder()
    drawing_names_map = load_drawing_map()

    if not all_files:
        st.info("Папка Drive порожня або доступ обмежений.")
        return

    # 2. Формуємо повний список
    all_data = []
    for f in all_files:
        sku = f['name'].rsplit('.', 1)[0]
        all_data.append({
            "Ім'я (опис)": drawing_names_map.get(f['id'], ""),
            "Артикул": sku,
            "Файл": f.get('webViewLink', '#'),
            "file_id": f['id']
        })
    df_full = pd.DataFrame(all_data)

    # 3. Пошук
    search = st.text_input("🔎 Пошук за артикулом або описом", placeholder="Введіть SKU чи назву...")
    
    if search:
        df_display = df_full[
            df_full["Артикул"].str.contains(search, case=False, na=False) | 
            df_full["Ім'я (опис)"].str.contains(search, case=False, na=False)
        ].copy()
    else:
        df_display = df_full.copy()

    # ВАЖЛИВО: Зберігаємо саме ту копію, яку бачить користувач
    st.session_state["current_display_df"] = df_display

    st.write("📝 *Редагуйте 'Ім'я' та натисніть Enter або клікніть мимо клітинки*")
    
    # 4. Редактор
    st.data_editor(
        df_display,
        column_config={
            "Ім'я (опис)": st.column_config.TextColumn("Ім'я (опис)", width="large"),
            "Артикул": st.column_config.TextColumn("Артикул (File Name)", disabled=True, width="medium"),
            "Файл": st.column_config.LinkColumn("Креслення", display_text="🔗 Відкрити"),
            "file_id": None 
        },
        use_container_width=True,
        hide_index=True,
        key="drawings_editor",
        on_change=handle_save
    )

    if st.button("🔄 Оновити список з Drive"):
        st.rerun()
