import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv
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
    # ВИПРАВЛЕНО: Прибрали імпорт, просто викликаємо функцію нижче
    if 'editing_id' in st.session_state and st.session_state.editing_id:
        show_edit_form(st.session_state.editing_id)
        return

    df_h = load_csv(ORDERS_HEADER_ID)
    df_i = load_csv(ORDER_ITEMS_ID)
    
    if df_h.empty:
        st.info("Журнал замовлень порожній.")
        return

    # --- ПАНЕЛЬ ФІЛЬТРІВ (Компактна) ---
    c1, c2, c3 = st.columns([2, 1, 1])
    f_search = c1.text_input("🔍 Пошук", placeholder="Клієнт, ID, ТТН...")
    f_manager = c2.selectbox("👤 Менеджер", ["Всі"] + sorted(list(df_h['Менеджер'].unique()) if 'Менеджер' in df_h.columns else []))
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
            
            with st.container():
                # Картка з кольоровою лінією зліва
                st.markdown(f'<div class="{status_class}" style="padding: 10px; border-radius: 5px; margin-bottom: 8px; border: 1px solid #ddd; border-left-width: 8px !important;">', unsafe_allow_html=True)
                
                col_title, col_edit, col_status = st.columns([4, 0.5, 1])
                
                col_title.markdown(f'<span style="font-size:1.1rem; font-weight:bold;">№{row["ID"]} — {row["Клієнт"]}</span>', unsafe_allow_html=True)
                
                # Кнопка редагування (олівець)
                if col_edit.button("📝", key=f"ed_{row['ID']}"):
                    st.session_state.editing_id = row['ID']
                    st.rerun()

                # Зміна статусу
                with col_status.popover(f"⚙️ {row['Готовність']}"):
                    new_st = st.selectbox("Змінити статус", ["В черзі", "В роботі", "Готово", "Відправлено"], 
                                        index=["В черзі", "В роботі", "Готово", "Відправлено"].index(row['Готовність']),
                                        key=f"pop_st_{row['ID']}")
                    if st.button("Оновити", key=f"pop_btn_{row['ID']}"):
                        update_order_header(row['ID'], {'Готовність': new_st})
                        st.rerun()

                # Інфо рядок
                st.markdown(f'<div style="font-size:0.85rem; color:#555;">📍 {row.get("Місто", "")} | 📱 {row["Телефон"]} | 👤 {row["Менеджер"]}</div>', unsafe_allow_html=True)

                # Товари (згорнуто для економії місця)
                with st.expander("📦 Список товарів"):
                    items = df_i[df_i['order_id'] == str(row['ID'])]
                    if not items.empty:
                        for _, it in items.iterrows():
                            it_c1, it_c2 = st.columns([4, 1])
                            it_c1.write(f"• {it['назва']} ({it['арт']}) x{it['к-ть']}")
                            link = get_pdf_link(it['арт'])
                            if link:
                                it_c2.markdown(f'<a href="{link}" target="_blank" class="pdf-button">PDF</a>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

def show_edit_form(order_id):
    """Функція для редагування замовлення з перевіркою наявності даних"""
    st.button("⬅️ Назад", on_click=lambda: st.session_state.update({"editing_id": None}))
    
    df_h = load_csv(ORDERS_HEADER_ID)
    
    # БЕЗПЕЧНИЙ ПОШУК: перевіряємо і рядки, і числа
    mask = (df_h['ID'].astype(str) == str(order_id))
    results = df_h[mask]
    
    if results.empty:
        st.error(f"Помилка: Замовлення №{order_id} не знайдено в базі даних.")
        if st.button("Спробувати оновити базу"):
            st.rerun()
        return

    # Тепер безпечно беремо перший рядок
    order_row = results.iloc[0]
    st.header(f"📝 Редагування №{order_id}")

    df_i = load_csv(ORDER_ITEMS_ID)
    
    # --- ДАЛІ ВАШ КОД ФОРМИ РЕДАГУВАННЯ ---
    with st.container(border=True):
        c1, c2 = st.columns(2)
        u_client = c1.text_input("Клієнт", value=str(order_row.get('Клієнт', '')))
        u_phone = c2.text_input("Телефон", value=str(order_row.get('Телефон', '')))
        u_city = c1.text_input("Місто", value=str(order_row.get('Місто', '')))
        u_ttn = c2.text_input("ТТН", value=str(order_row.get('ТТН', '')))
        
        # Безпечний пошук індексу для статусу
        statuses = ["В черзі", "В роботі", "Готово", "Відправлено"]
        current_status = order_row.get('Готовність', 'В черзі')
        try:
            st_idx = statuses.index(current_status)
        except ValueError:
            st_idx = 0
            
        u_status = st.selectbox("Статус", statuses, index=st_idx)

    if st.button("💾 ЗБЕРЕГТИ ЗМІНИ", type="primary"):
        update_order_header(order_id, {
            'Клієнт': u_client, 
            'Телефон': u_phone, 
            'Місто': u_city, 
            'ТТН': u_ttn, 
            'Готовність': u_status
        })
        st.session_state.editing_id = None
        st.success("Дані оновлено!")
        st.rerun()
