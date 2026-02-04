import streamlit as st
import pandas as pd
from modules.admin_module import load_csv
from modules.drawings import get_pdf_link
from .core import ORDERS_HEADER_ID, ORDER_ITEMS_ID, update_order_header

def show_order_cards():
    df_h = load_csv(ORDERS_HEADER_ID)
    if df_h.empty:
        st.info("У базі поки немає жодного замовлення.")
        return

    # --- ПАНЕЛЬ ІНСТРУМЕНТІВ ---
    with st.expander("🛠️ Фільтри та налаштування вигляду", expanded=True):
        col_v, col_m, col_s = st.columns([1, 1, 2])
        view_mode = col_v.radio("Вигляд:", ["🗂️ Картки", "📊 Таблиця"])
        
        managers = ["Всі"] + sorted(list(df_h['Менеджер'].unique()))
        sel_manager = col_m.selectbox("Менеджер:", managers)
        
        search = col_s.text_input("🔍 Пошук (ID, Клієнт, Місто, ТТН)")

    # Фільтрація
    filtered_df = df_h.copy()
    if sel_manager != "Всі":
        filtered_df = filtered_df[filtered_df['Менеджер'] == sel_manager]
    if search:
        filtered_df = filtered_df[filtered_df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

    # Сортування: нові зверху
    filtered_df = filtered_df.iloc[::-1]

    if view_mode == "📊 Таблиця":
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    
    else:
        df_i = load_csv(ORDER_ITEMS_ID) # Завантажуємо товари для карток
        
        for _, row in filtered_df.iterrows():
            with st.container(border=True):
                h1, h2, h3 = st.columns([2, 2, 1])
                h1.subheader(f"№{row['ID']} — {row['Клієнт']}")
                h2.write(f"👤 **{row['Менеджер']}** | 📅 {row['Дата']}")
                
                # Зміна статусу через поповер
                with h3.popover("⚙️ Статус"):
                    new_st = st.selectbox("Змінити на:", ["В черзі", "В роботі", "Готово"], key=f"st_{row['ID']}")
                    if st.button("Оновити", key=f"btn_st_{row['ID']}"):
                        update_order_header(row['ID'], {'Готовність': new_st})
                        st.rerun()

                st.write(f"📍 {row['Місто']} | 📞 {row['Телефон']} | 🚚 ТТН: `{row['ТТН']}`")
                
                # Відображення товарів замовлення
                with st.expander("📦 Переглянути товари"):
                    if not df_i.empty:
                        items = df_i[df_i['order_id'] == str(row['ID'])]
                        if items.empty:
                            st.caption("Товари ще не додані")
                        else:
                            for _, it in items.iterrows():
                                c_it, c_pdf = st.columns([4, 1])
                                c_it.write(f"🔹 {it['назва']} (**{it['арт']}**) — {it['к-ть']} шт.")
                                
                                link = get_pdf_link(it['арт'])
                                if link:
                                    c_pdf.markdown(f'<a href="{link}" target="_blank" class="pdf-button">📕 PDF</a>', unsafe_allow_html=True)
                    
                    if st.button("➕ Редагувати товари / інфо", key=f"edit_full_{row['ID']}"):
                        st.session_state.editing_id = row['ID']
                        st.info("Функція детального редагування в розробці...")
