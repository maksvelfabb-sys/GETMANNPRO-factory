import streamlit as st
import pandas as pd
from modules.admin_module import load_csv, save_csv
from modules.drawings import get_pdf_link
from .core import ORDERS_HEADER_ID, ORDER_ITEMS_ID, update_order_header

def show_order_cards():
    # Перевіряємо, чи ми зараз у режимі редагування конкретного замовлення
    if 'editing_id' in st.session_state and st.session_state.editing_id:
        show_edit_form(st.session_state.editing_id)
        return

    df_h = load_csv(ORDERS_HEADER_ID)
    df_i = load_csv(ORDER_ITEMS_ID)
    
    if df_h.empty:
        st.info("Журнал замовлень порожній.")
        return

    # --- ФІЛЬТРИ ---
    with st.expander("🔍 Пошук та фільтри"):
        c1, c2 = st.columns(2)
        f_search = c1.text_input("Пошук (Клієнт, ID, ТТН)")
        f_manager = c2.selectbox("Менеджер:", ["Всі"] + sorted(list(df_h['Менеджер'].unique())))

    # Логіка фільтрації
    view_df = df_h.copy()
    if f_manager != "Всі": view_df = view_df[view_df['Менеджер'] == f_manager]
    if f_search: view_df = view_df[view_df.apply(lambda r: f_search.lower() in str(r.values).lower(), axis=1)]
    
    view_df = view_df.iloc[::-1] # Нові зверху

    # --- ВІДОБРАЖЕННЯ КАРТОК ---
    for _, row in view_df.iterrows():
        with st.container(border=True):
            h1, h2, h3 = st.columns([3, 2, 1])
            h1.subheader(f"№{row['ID']} — {row['Клієнт']}")
            h2.write(f"👤 {row['Менеджер']} | 📅 {row['Дата']}")
            
            # Кнопка переходу до редагування
            if h3.button("📝 Редагувати", key=f"edit_btn_{row['ID']}", use_container_width=True):
                st.session_state.editing_id = row['ID']
                st.rerun()

            st.write(f"📍 {row['Місто']} | 📞 {row['Телефон']} | 🚚 ТТН: `{row.get('ТТН', '')}`")
            
            with st.expander("📦 Товари"):
                items = df_i[df_i['order_id'] == str(row['ID'])]
                if not items.empty:
                    for idx, it in items.iterrows():
                        col_it, col_pdf = st.columns([4, 1])
                        col_it.write(f"🔹 {it['назва']} ({it['арт']}) — {it['к-ть']} шт. | {it.get('сума', 0)} грн")
                        link = get_pdf_link(it['арт'])
                        if link:
                            col_pdf.markdown(f'<a href="{link}" target="_blank" class="pdf-button">📕 PDF</a>', unsafe_allow_html=True)
                else:
                    st.caption("Товари не додані")

def show_edit_form(order_id):
    """Форма редагування замовлення"""
    st.button("⬅️ Назад до списку", on_click=lambda: st.session_state.update({"editing_id": None}))
    st.header(f"📝 Редагування замовлення №{order_id}")

    df_h = load_csv(ORDERS_HEADER_ID)
    df_i = load_csv(ORDER_ITEMS_ID)
    
    # Дані поточної шапки
    order_row = df_h[df_h['ID'] == str(order_id)].iloc[0]
    
    with st.container(border=True):
        st.subheader("Дані клієнта")
        c1, c2 = st.columns(2)
        new_client = c1.text_input("Клієнт", value=order_row['Клієнт'])
        new_phone = c2.text_input("Телефон", value=order_row['Телефон'])
        new_city = c1.text_input("Місто", value=order_row.get('Місто', ''))
        new_ttn = c2.text_input("ТТН", value=order_row.get('ТТН', ''))
        new_status = st.selectbox("Статус", ["В черзі", "В роботі", "Готово", "Відправлено"], index=["В черзі", "В роботі", "Готово", "Відправлено"].index(order_row['Готовність']))

    st.subheader("📦 Товари")
    current_items = df_i[df_i['order_id'] == str(order_id)]
    
    # Видалення існуючих товарів
    if not current_items.empty:
        for idx, it in current_items.iterrows():
            col_n, col_d = st.columns([5, 1])
            col_n.write(f"🔹 {it['назва']} | {it['арт']} | {it['к-ть']} шт.")
            if col_d.button("🗑️", key=f"del_{idx}"):
                new_i_df = df_i.drop(idx)
                save_csv(ORDER_ITEMS_ID, new_i_df)
                st.rerun()

    # Додавання нового товару
    with st.expander("➕ Додати товар"):
        it1, it2, it3 = st.columns([3, 1, 1])
        add_n = it1.text_input("Назва")
        add_a = it2.text_input("Арт")
        add_q = it3.number_input("К-ть", min_value=1, value=1)
        if st.button("Додати"):
            new_it = pd.DataFrame([{'order_id': str(order_id), 'назва': add_n, 'арт': add_a, 'к-ть': str(add_q), 'сума': '0'}])
            save_csv(ORDER_ITEMS_ID, pd.concat([df_i, new_it], ignore_index=True))
            st.rerun()

    if st.button("💾 ЗБЕРЕГТИ ЗМІНИ", type="primary", use_container_width=True):
        update_data = {
            'Клієнт': new_client,
            'Телефон': new_phone,
            'Місто': new_city,
            'ТТН': new_ttn,
            'Готовність': new_status
        }
        update_order_header(order_id, update_data)
        st.session_state.editing_id = None
        st.success("Зміни збережено!")
        st.rerun()
