import streamlit as st
from modules.drive_tools import get_file_link_by_name

def show_drawings_catalog():
    st.markdown("### 🔍 Пошук креслень")
    search_sku = st.text_input("Введіть SKU", placeholder="GMN-01")
    if search_sku:
        link = get_file_link_by_name(search_sku)
        if link:
            st.success(f"Креслення знайдено")
            st.link_button(f"Відкрити {search_sku}", link, use_container_width=True)
        else:
            st.error("Файл не знайдено")

def render_drawings_list(skus):
    if not skus: return
    for sku in skus:
        link = get_file_link_by_name(str(sku))
        if link:
            st.link_button(f"📄 {sku}", link)
