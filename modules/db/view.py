import streamlit as st
import pandas as pd
from modules.drive_tools import load_csv, save_csv, get_drive_service, ORDERS_CSV_ID
from datetime import datetime

# ID папки з кресленнями
DRAWINGS_FOLDER_ID = "1SQyZ6OUk9xNBMvh98Ob4zw9LVaqWRtas"

def get_val(order, keys):
    for key in keys:
        if key in order and pd.notnull(order[key]):
            return order[key]
    return ""

def update_db(order_id, field_name, new_value):
    """Швидке оновлення поля без зайвих повідомлень"""
    df = load_csv(ORDERS_CSV_ID)
    id_col = next((c for c in ['order_id', 'ID', 'id'] if c in df.columns), None)
    if id_col:
        idx = df.index[df[id_col].astype(str) == str(order_id)].tolist()
        if idx:
            # Знаходимо точну назву колонки
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

def render_order_card(order):
    """Картка, де все можна редагувати відразу"""
    oid = str(get_val(order, ['order_id', 'ID']))
    
    with st.container(border=True):
        # Рядок 1: ID та Статус
        h1, h2 = st.columns([3, 1])
        h1.subheader(f"📦 Замовлення №{oid}")
        
        status_list = ["Новий", "В роботі", "Готово", "Видано", "Скасовано"]
        curr_st = get_val(order, ['status', 'Статус'])
        new_st = h2.selectbox("Статус", status_list, index=status_list.index(curr_st) if curr_st in status_list else 0, key=f"st_{oid}")
        if new_st != curr_st: update_db(oid, 'status', new_st)

        # Рядок 2: Клієнт (ПІБ, Телефон, Адреса)
        c1, c2, c3 = st.columns(3)
        val_name = c1.text_input("Клієнт", value=get_val(order, ['client_name', 'ПІБ']), key=f"n_{oid}")
        if val_name != get_val(order, ['client_name', 'ПІБ']): update_db(oid, 'client_name', val_name)
        
        val_ph = c2.text_input("Телефон", value=get_val(order, ['client_phone', 'Телефон']), key=f"ph_{oid}")
        if val_ph != get_val(order, ['client_phone', 'Телефон']): update_db(oid, 'client_phone', val_ph)
        
        val_adr = c3.text_input("Адреса", value=get_val(order, ['address', 'Адреса']), key=f"adr_{oid}")
        if val_adr != get_val(order, ['address', 'Адреса']): update_db(oid, 'address', val_adr)

        # Рядок 3: Товар (Назва, Артикул, Кількість)
        t1, t2, t3 = st.columns([2, 1, 1])
        val_prod = t1.text_input("Товар", value=get_val(order, ['product', 'Товар']), key=f"p_{oid}")
        if val_prod != get_val(order, ['product', 'Товар']): update_db(oid, 'product', val_prod)
        
        val_sku = t2.text_input("Артикул", value=get_val(order, ['sku', 'Артикул']), key=f"s_{oid}")
        if val_sku != get_val(order, ['sku', 'Артикул']): update_db(oid, 'sku', val_sku)
        
        val_qty = t3.number_input("К-сть", value=int(get_val(order, ['qty', 'Кількість']) or 1), key=f"q_{oid}")
        if val_qty != int(get_val(order, ['qty', 'Кількість']) or 1): update_db(oid, 'qty', val_qty)

        # Рядок 4: Креслення (Автопошук)
        st.markdown("---")
        draw = find_drawing(val_sku if val_sku else val_prod)
        d_col1, d_col2 = st.columns([1, 2])
        if draw:
            d_col1.link_button("📂 Відкрити креслення", draw['webViewLink'], type="primary", use_container_width=True)
            d_col2.success(f"Знайдено файл: {draw['name']}")
        else:
            d_col1.link_button("📁 Тека", f"https://drive.google.com/drive/folders/{DRAWINGS_FOLDER_ID}", use_container_width=True)
            d_col2.warning("Файл не знайдено за артикулом")

        # Рядок 5: Гроші (Сума, Аванс, Залишок)
        st.markdown("---")
        f1, f2, f3 = st.columns(3)
        curr_tot = float(get_val(order, ['total', 'Сума']) or 0)
        curr_pre = float(get_val(order, ['prepayment', 'Аванс']) or 0)
        
        val_tot = f1.number_input("Загальна сума", value=curr_tot, key=f"t_{oid}")
        val_pre = f2.number_input("Аванс", value=curr_pre, key=f"pr_{oid}")
        
        if val_tot != curr_tot: update_db(oid, 'total', val_tot)
        if val_pre != curr_pre: update_db(oid, 'prepayment', val_pre)
        
        f3.metric("Доплата", f"{val_tot - val_pre} грн", delta_color="inverse")

def show_order_cards():
    # ШВИДКЕ СТВОРЕННЯ (Без зайвих кнопок)
    with st.expander("➕ НОВЕ ЗАМОВЛЕННЯ", expanded=False):
        with st.form("quick_create", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            f_name = c1.text_input("Клієнт")
            f_phone = c2.text_input("Телефон")
            f_prod = c3.text_input("Товар / Артикул")
            
            f_total = st.number_input("Сума", min_value=0)
            if st.form_submit_button("ЗБЕРЕГТИ ЗАМОВЛЕННЯ"):
                df = load_csv(ORDERS_CSV_ID)
                new_id = int(df['order_id'].max() + 1) if not df.empty else 1001
                new_row = {
                    'order_id': new_id, 'client_name': f_name, 'client_phone': f_phone,
                    'product': f_prod, 'total': f_total, 'status': 'Новий', 'date': datetime.now().strftime("%d.%m.%Y")
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_csv(ORDERS_CSV_ID, df)
                st.rerun()

    st.divider()

    # СПИСОК КАРТОК
    df = load_csv(ORDERS_CSV_ID)
    if not df.empty:
        # Сортуємо: нові зверху
        df = df.sort_values(by='order_id', ascending=False)
        for _, row in df.iterrows():
            render_order_card(row)
