import streamlit as st
import pandas as pd
from modules.admin_module import load_csv, save_csv
from modules.drawings import get_pdf_link
from .core import ORDERS_HEADER_ID, ORDER_ITEMS_ID, update_order_header

def get_status_class(status):
    mapping = {
        "В черзі": "status-v-cherzi",
        "В роботі": "status-v-roboti",
        "Готово": "status-gotovo",
        "Відправлено": "status-vidpravleno"
    }
    return mapping.get(status, "")

def show_order_cards():
    if 'editing_id' in st.session_state and st.session_state.editing_id:
        from .view import show_edit_form # Щоб уникнути циклічного імпорту
        show_edit_form(st.session_state.editing_id)
        return

    df_h = load_csv(ORDERS_HEADER_ID)
    df_i = load_csv(ORDER_ITEMS_ID)
    
    if df_h.empty:
        st.info("Журнал замовлень порожній.")
        return

    # --- ФІЛЬТРИ (тепер в один рядок для економії місця) ---
    c1, c2, c3 = st.columns([2, 1, 1])
    f_search = c1.text_input("🔍 Пошук", placeholder="Клієнт, ID, ТТН...")
    f_manager = c2.selectbox("👤 Менеджер", ["Всі"] + sorted(list(df_h['Менеджер'].unique())))
    f_view = c3.radio("Вигляд", ["🗂️", "📊"], horizontal=True)

    view_df = df_h.copy()
    if f_manager != "Всі": view_df = view_df[view_df['Менеджер'] == f_manager]
    if f_search: view_df = view_df[view_df.apply(lambda r: f_search.lower() in str(r.values).lower(), axis=1)]
    
    view_df = view_df.iloc[::-1]

    if f_view == "📊":
        st.dataframe(view_df, use_container_width=True, hide_index=True)
    else:
        for _, row in view_df.iterrows():
            status_class = get_status_class(row['Готовність'])
            
            # Початок контейнера картки з кольоровою міткою
            with st.container():
                st.markdown(f'<div class="{status_class}" style="padding: 10px; border-radius: 5px; margin-bottom: 5px; border: 1px solid #ddd;">', unsafe_allow_html=True)
                
                # Рядок 1: ID, Клієнт, Дата
                col_title, col_status = st.columns([4, 1])
                col_title.markdown(f'<span class="card-id">№{row["ID"]} — {row["Клієнт"]}</span>', unsafe_allow_html=True)
                
                # Кнопка статусу (зменшена)
                with col_status.popover("⚙️"):
                    new_st = st.selectbox("Статус", ["В черзі", "В роботі", "Готово", "Відправлено"], 
                                        index=["В черзі", "В роботі", "Готово", "Відправлено"].index(row['Готовність']),
                                        key=f"st_change_{row['ID']}")
                    if st.button("Зберегти", key=f"btn_st_{row['ID']}"):
                        update_order_header(row['ID'], {'Готовність': new_st})
                        st.rerun()

                # Рядок 2: Інфо та кнопка редагування
                inf1, inf2, inf3 = st.columns([3, 2, 1])
                inf1.markdown(f'<div class="card-info">📍 {row.get("Місто", "")} | 📱 {row["Телефон"]}</div>', unsafe_allow_html=True)
                inf2.markdown(f'<div class="card-info">👤 {row["Менеджер"]} | 📅 {row["Дата"]}</div>', unsafe_allow_html=True)
                
                if inf3.button("📝", key=f"edit_{row['ID']}", help="Редагувати замовлення"):
                    st.session_state.editing_id = row['ID']
                    st.rerun()

                # Компактний список товарів (лише якщо розгорнуто)
                with st.expander("📦 Товари"):
                    items = df_i[df_i['order_id'] == str(row['ID'])]
                    for _, it in items.iterrows():
                        it_c1, it_c2 = st.columns([4, 1])
                        it_c1.write(f"• {it['назва']} ({it['арт']}) x{it['к-ть']}")
                        link = get_pdf_link(it['art'] if 'art' in it else it.get('арт'))
                        if link:
                            it_c2.markdown(f'<a href="{link}" target="_blank" class="pdf-button">PDF</a>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True) # Закриваємо div картки
