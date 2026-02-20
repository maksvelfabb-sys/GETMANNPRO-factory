import streamlit as st
import pandas as pd
from modules.drive_tools import get_all_files_in_folder, load_drawing_map, save_drawing_map

def show_drawings_catalog():
    st.subheader("📁 Бібліотека креслень")

    # 1. Отримуємо актуальні файли з Drive та наш реєстр "Імен"
    all_files = get_all_files_in_folder()
    drawing_names_map = load_drawing_map() # Тут ми зберігаємо {file_id: "Довільне Ім'я"}

    if not all_files:
        st.info("В папці на Drive поки немає файлів.")
        return

    # 2. Формуємо дані
    data = []
    for f in all_files:
        # Артикул — це назва файлу без розширення (напр. "GMN-10.pdf" -> "GMN-10")
        sku = f['name'].rsplit('.', 1)[0]
        # Ім'я беремо з карти, якщо воно там є
        custom_name = drawing_names_map.get(f['id'], "")
        
        data.append({
            "Артикул (Файл)": sku,
            "Додаткове Ім'я": custom_name,
            "Посилання": f['webViewLink'],
            "file_id": f['id'],
            "full_name": f['name']
        })

    df = pd.DataFrame(data)

    # 3. Інтерфейс
    search = st.text_input("🔎 Швидкий пошук (за Артикулом або Іменем)", placeholder="Введіть частину назви...")
    
    if search:
        df_display = df[
            df["Артикул (Файл)"].str.contains(search, case=False) | 
            df["Додаткове Ім'я"].str.contains(search, case=False)
        ]
    else:
        df_display = df

    # 4. Таблиця з можливістю редагування "Імені"
    st.write("💡 Ви можете вписати 'Ім'я' для уточнення, але це не обов'язково.")
    
    edited_df = st.data_editor(
        df_display,
        column_config={
            "Артикул (Файл)": st.column_config.TextColumn("Артикул", disabled=True),
            "Додаткове Ім'я": st.column_config.TextColumn("Присвоїти ім'я (опц.)", help="Наприклад: 'Кронштейн посилений'"),
            "Посилання": st.column_config.LinkColumn("Креслення", display_text="🔗 Відкрити"),
            "file_id": None,
            "full_name": None
        },
        use_container_width=True,
        hide_index=True,
        key="drawings_editor"
    )

    # 5. Кнопка збереження змін в "Іменах"
    if st.button("💾 Зберегти зміни в іменах"):
        # Оновлюємо тільки колонку Імен
        new_names = dict(zip(edited_df["file_id"], edited_df["Додаткове Ім'я"]))
        
        # Завантажуємо повну карту (щоб не затерти те, що не потрапило в пошук)
        current_full_map = load_drawing_map()
        current_full_map.update(new_names)
        
        if save_drawing_map(current_full_map):
            st.success("Імена оновлені!")
            st.rerun()

    st.divider()
    st.caption(f"Всього креслень у папці: {len(df)}")
