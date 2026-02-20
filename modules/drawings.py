import streamlit as st
import pandas as pd
from modules.drive_tools import get_all_files_in_folder, save_drawing_map, load_drawing_map

def show_drawings_catalog():
    st.subheader("📐 Автоматична синхронізація креслень")
    
    # 1. Завантажуємо поточну карту відповідностей (SKU -> File ID)
    drawing_map = load_drawing_map() # Функція, що читає JSON або CSV файл з налаштуваннями
    
    # 2. Отримуємо список ВСІХ файлів з папки Drive
    all_files = get_all_files_in_folder() # Список словників {'id', 'name'}
    
    tab1, tab2 = st.tabs(["🔎 Перегляд", "✏️ Присвоїти імена (Мапінг)"])
    
    with tab1:
        search = st.text_input("Пошук креслення за іменем або артикулом")
        # Логіка фільтрації та відображення...
        render_drawings_grid(drawing_map, search)

    with tab2:
        st.write("Тут ви можете прив'язати завантажений файл до конкретного SKU")
        
        # Створюємо таблицю для редагування
        edit_data = []
        for f in all_files:
            current_sku = drawing_map.get(f['id'], f['name']) # Якщо не підписано, беремо назву файлу
            edit_data.append({"File ID": f['id'], "Назва файлу": f['name'], "Присвоєне ім'я/SKU": current_sku})
        
        df_editor = pd.DataFrame(edit_data)
        edited_df = st.data_editor(df_editor, hide_index=True, use_container_width=True)
        
        if st.button("💾 Зберегти зміни реєстру"):
            # Перетворюємо назад у словник і зберігаємо
            new_map = dict(zip(edited_df["File ID"], edited_df["Присвоєне ім'я/SKU"]))
            if save_drawing_map(new_map):
                st.success("Реєстр оновлено!")
                st.rerun()
