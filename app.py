import streamlit as st
from database.connection import read_db
from modules import order_ui, material_manager, user_manager
from styles import set_custom_css

st.set_page_config(page_title="GETMANN Pro", layout="wide")
set_custom_css()

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🔐 GETMANN Pro</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form"):
            l = st.text_input("Логін").lower().strip()
            p = st.text_input("Пароль", type="password").strip()
            if st.form_submit_button("УВІЙТИ", use_container_width=True):
                if l == MASTER_ADMIN["login"] and p == MASTER_ADMIN["password"]:
                    st.session_state.update({"auth": True, "user_role": MASTER_ADMIN["role"], "user_name": MASTER_ADMIN["name"]})
                    st.rerun()
                else:
                    try:
                        df = read_db("staff.csv", ["login", "password", "role", "name"])
                        user = df[(df['login'].astype(str) == l) & (df['password'].astype(str) == p)]
                        if not user.empty:
                            st.session_state.update({"auth": True, "user_role": user.iloc[0]['role'], "user_name": user.iloc[0]['name']})
                            st.rerun()
                        else: st.error("Помилка авторизації")
                    except: st.error("База порожня. Використовуйте Admin.")
else:
    st.sidebar.title("🚀 GETMANN Pro")
    st.sidebar.write(f"👤 {st.session_state.user_name}")
    choice = st.sidebar.radio("Меню", ["📊 Журнал", "📝 Нове замовлення", "🏗️ Склад", "👥 Персонал"])
    
    if st.sidebar.button("Вихід"):
        st.session_state.auth = False
        st.rerun()

    if choice == "📊 Журнал": order_ui.display_orders_list()
    elif choice == "📝 Нове замовлення": order_ui.render_order_form()
    elif choice == "🏗️ Склад": material_manager.show_manager()

    elif choice == "👥 Персонал": user_manager.show_user_editor()
