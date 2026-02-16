import streamlit as st
from modules.db.create import show_create_order  # Імпорт з сусіднього файлу

def show_order_cards():
    if st.button("➕ СТВОРИТИ ЗАМОВЛЕННЯ", use_container_width=True):
        st.session_state.creating_now = True

    if st.session_state.get("creating_now", False):
        show_create_order()

    # Головна кнопка-тригер
    if st.button("➕ СТВОРИТИ ЗАМОВЛЕННЯ", use_container_width=True, type="primary"):
        st.session_state.creating_now = True

    # Виклик форми з іншого файлу
    if st.session_state.get("creating_now", False):
        show_create_order_form()

    st.divider()

    # Далі йде завантаження та відображення списку карток (ваш існуючий код)
    df = load_csv(ORDERS_CSV_ID)
    # ... (сортування та цикл render_order_card) ...
