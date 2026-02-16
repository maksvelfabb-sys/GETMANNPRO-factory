import streamlit as st
import pandas as pd
from modules.db.create import show_create_order # Цей рядок викликав помилку
from modules.drive_tools import load_csv, save_csv, get_drive_service, ORDERS_CSV_ID
# ... решта імпортів ...

def show_order_cards():
    # 1. Кнопка тригер
    if st.button("➕ СТВОРИТИ ЗАМОВЛЕННЯ", key="main_btn"):
        st.session_state.creating_now = True

    # 2. Форма (викликається ОДИН раз поза циклом)
    if st.session_state.get("creating_now", False):
        show_create_order()

    st.divider()

    # 3. Список карток
    df = load_csv(ORDERS_CSV_ID)
    # ... цикл for ...

    # Виклик функції з create.py
    if st.session_state.get("creating_now", False):
        show_create_order() 

    st.divider()
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
