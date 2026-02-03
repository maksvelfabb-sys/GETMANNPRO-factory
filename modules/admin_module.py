import streamlit as st
# Змінено на абсолютний імпорт
from modules.database import load_data 

def show_admin_panel():
    st.header("👥 Панель керування")
    df = load_data()
    st.metric("Замовлень у базі", len(df))
    st.dataframe(df.tail(10))
