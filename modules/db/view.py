import streamlit as st
import pandas as pd
from datetime import datetime
from modules.drive_tools import load_csv, save_csv, ORDERS_CSV_ID

def show_create_order():
    """Функція для створення замовлення (викликається з view або app)"""
    st.markdown("### 🆕 Нове замовлення")
    
    # Використовуємо унікальний ключ для форми
    with st.form(key="form_create_order_v3", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_name = c1.text_input("Клієнт")
        f_phone = c2.text_input("Телефон")
        f_prod = st.text_input("Товар / Артикул")
        
        if st.form_submit_button("✅ Зберегти", use_container_width=True):
            if f_name and f_prod:
                df = load_csv(ORDERS_CSV_ID)
                # Логіка додавання рядка...
                st.success("Додано!")
                st.rerun()
            else:
                st.error("Заповніть поля!")

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
