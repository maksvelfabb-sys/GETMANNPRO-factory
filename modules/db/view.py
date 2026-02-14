import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, get_drive_service, ORDERS_CSV_ID
from datetime import datetime

DRAWINGS_FOLDER_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

# --- ДОПОМІЖНІ ФУНКЦІЇ ---
def get_val(order, keys):
    for key in keys:
        if key in order and pd.notnull(order[key]):
            return order[key]
    return ""

def update_db(order_id, field_name, new_value):
    df = load_csv(ORDERS_CSV_ID)
    id_col = next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')
    idx = df.index[df[id_col].astype(str) == str(order_id)].tolist()
    if idx:
        real_col = next((c for c in df.columns if c.lower() == field_name.lower() or c == field_name), field_name)
        if str(df.at[idx[0], real_col]) != str(new_value):
            df.at[idx[0], real_col] = new_value
            save_csv(ORDERS_CSV_ID, df)
            st.toast(f"💾 {real_col} збережено")

def find_drawing(query):
    service = get_drive_service()
    if not service or not query or query == "---": return None
    q = f"'{DRAWINGS_FOLDER_ID}' in parents and name contains '{query}' and trashed = false"
    try:
        results = service.files().list(q=q, fields="files(name, webViewLink)").execute()
        files = results.get('files', [])
        return files[0] if files else None
    except: return None

# --- ВІДОБРАЖЕННЯ КАРТКИ ---
def render_order_card(order):
    oid = str(get_val(order, ['order_id', 'ID']))
    
    with st.container(border=True):
        h1, h2 = st.columns([3, 1])
        h1.subheader(f"📦 Замовлення №{oid}")
        
        status_list = ["Новий", "В роботі", "Готово", "Видано", "Скасовано"]
        curr_st = get_val(order, ['status', 'Статус'])
        new_st = h2.selectbox("Статус", status_list, index=status_list.index(curr_st) if curr_st in status_list else 0, key=f"st_{oid}")
        if new_st != curr_st: update_db(oid, 'status', new_st)

        st.divider()
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Клієнт", value=get_val(order, ['client_name', 'ПІБ']), key=f"n_{oid}")
        if n != get_val(order, ['client_name', 'ПІБ']): update_db(oid, 'client_name', n)
        
        ph = c2.text_input("Телефон", value=get_val(order, ['client_phone', 'Телефон']), key=f"ph_{oid}")
        if ph != get_val(order, ['client_phone', 'Телефон']): update_db(oid, 'client_phone', ph)
        
        adr = c3.text_input("Адреса", value=get_val(order, ['address', 'Адреса']), key=f"adr_{oid}")
        if adr != get_val(order, ['address', 'Адреса']): update_db(oid, 'address', adr)

        t1, t2, t3 = st.columns([2, 1, 1])
        prod = t1.text_input("Товар", value=get_val(order, ['product', 'Товар']), key=f"p_{oid}")
        if prod != get_val(order, ['product', 'Товар']): update_db(oid, 'product', prod)
        
        sku = t2.text_input("Артикул", value=get_val(order, ['sku', 'Артикул']), key=f"s_{oid}")
        if sku != get_val(order, ['sku', 'Артикул']): update_db(oid, 'sku', sku)
        
        qty = t3.number_input("К-сть", value=int(get_val(order, ['qty', 'Кількість']) or 1), key=f"q_{oid}")
        if qty != int(get_val(order, ['qty', 'Кількість']) or 1): update_db(oid, 'qty', qty)

        # Креслення
        draw = find_drawing(sku if sku else prod)
        if draw:
            st.link_button(f"📄 Креслення: {draw['name']}", draw['webViewLink'], type="primary")

        st.divider()
        f1, f2, f3 = st.columns(3)
        curr_tot = float(get_val(order, ['total', 'Сума']) or 0)
        curr_pre = float(get_val(order, ['prepayment', 'Аванс']) or 0)
        
        val_tot = f1.number_input("Загальна сума", value=curr_tot, key=f"t_{oid}")
        val_pre = f2.number_input("Аванс", value=curr_pre, key=f"pr_{oid}")
        if val_tot != curr_tot: update_db(oid, 'total', val_tot)
        if val_pre != curr_pre: update_db(oid, 'prepayment', val_pre)
        f3.metric("Залишок", f"{val_tot - val_pre} грн")

# --- ГОЛОВНИЙ ЕКРАН ---
def show_order_cards():
    st.title("🏭 GETMANN ERP")

    # Кнопка для перемикання режиму створення
    if st.button("➕ СТВОРИТИ ЗАМОВЛЕННЯ", use_container_width=True):
        st.session_state.creating_now = True

    # --- ФОРМА НОВОЇ КАРТКИ ---
    if st.session_state.get("creating_now", False):
        with st.container(border=True):
            st.markdown("### 🆕 Нове замовлення")
            with st.form("new_order_form"):
                col1, col2, col3 = st.columns(3)
                f_name = col1.text_input("Клієнт")
                f_phone = col2.text_input("Телефон")
                f_addr = col3.text_input("Адреса")
                
                col4, col5, col6 = st.columns([2, 1, 1])
                f_prod = col4.text_input("Назва товару")
                f_sku = col5.text_input("Артикул")
                f_qty = col6.number_input("Кількість", min_value=1, value=1)
                
                col7, col8 = st.columns(2)
                f_total = col7.number_input("Загальна сума", min_value=0.0)
                f_pre = col8.number_input("Аванс", min_value=0.0)
                
                btn_save, btn_cancel = st.columns(2)
                if btn_save.form_submit_button("✅ ДОДАТИ ЗАМОВЛЕННЯ", use_container_width=True):
                    df = load_csv(ORDERS_CSV_ID)
                    # Пошук останнього ID
                    id_col = next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), 'order_id')
                    new_id = int(df[id_col].max() + 1) if not df.empty else 1001
                    
                    new_row = {
                        id_col: new_id, 'client_name': f_name, 'client_phone': f_phone, 'address': f_addr,
                        'product': f_prod, 'sku': f_sku, 'qty': f_qty, 'total': f_total, 
                        'prepayment': f_pre, 'status': 'Новий', 'date': datetime.now().strftime("%d.%m.%Y")
                    }
                    
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_csv(ORDERS_CSV_ID, df)
                    st.session_state.creating_now = False
                    st.rerun()
                
                if btn_cancel.form_submit_button("❌ СКАСУВАТИ", use_container_width=True):
                    st.session_state.creating_now = False
                    st.rerun()

    st.divider()

    # --- СПИСОК КАРТОК ---
    df = load_csv(ORDERS_CSV_ID)
    if not df.empty:
        id_col = next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), None)
        if id_col:
            df[id_col] = pd.to_numeric(df[id_col], errors='coerce')
            df = df.sort_values(by=id_col, ascending=False)
        
        for _, row in df.iterrows():
            render_order_card(row)
    else:
        st.info("Замовлень не знайдено.")
