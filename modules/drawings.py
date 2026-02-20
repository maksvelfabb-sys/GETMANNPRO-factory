import streamlit as st
from modules.drive_tools import get_file_link_by_name

def render_drawings_list(skus):
    """
    Універсальна функція для відображення списку креслень за списком артикулів.
    Використовується і в каталозі, і всередині замовлень.
    """
    if not skus:
        st.caption("Артикули не вказані — креслення відсутні.")
        return

    # Очищуємо список від порожніх значень
    active_skus = [str(s).strip() for s in skus if str(s).strip()]
    
    if not active_skus:
        st.caption("Немає коректних артикулів для пошуку.")
        return

    # Відображення кнопками в ряд (по 4 у рядку)
    cols = st.columns(4)
    for i, sku in enumerate(active_skus):
        link = get_file_link_by_name(sku)
        with cols[i % 4]:
            if link:
                st.link_button(f"📄 {sku}", link, width="stretch", help=f"Відкрити креслення для {sku}")
            else:
                st.button(f"❌ {sku}", disabled=True, width="stretch", help="Файл не знайдено на Drive")

def show_drawings_catalog():
    """
    Функція для окремої сторінки 'Креслення' у бічній панелі.
    """
    st.markdown("### 🔍 Глобальний пошук креслень")
    search_sku = st.text_input("Введіть артикул (SKU) для швидкого пошуку", placeholder="Наприклад: GMN-102")
    
    if search_sku:
        st.write(f"Результат для: **{search_sku}**")
        render_drawings_list([search_sku])
    
    st.divider()
    st.info("💡 Підказка: Креслення шукаються автоматично в папці на Google Drive за назвою файлу, яка збігається з Артикулом.")
