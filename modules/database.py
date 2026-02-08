import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from modules.drawings import get_pdf_link, get_drive_service 

ORDERS_CSV_ID = "1Ws7rL1uyWcYbLeXsmqmaijt98Gxo6k3i"
COLS = ['ID', 'Дата', 'Клієнт', 'Телефон', 'Місто', 'ТТН', 'Товари_JSON', 'Аванс', 'Готовність', 'Коментар']

def load_data():
    service = get_drive_service()
    if not service: return pd.DataFrame(columns=COLS)
    try:
        request = service.files().get_media(fileId=ORDERS_CSV_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh, dtype=str).fillna("")
        return df
    except: return pd.DataFrame(columns=COLS)

def save_data(df):
    service = get_drive_service()
    if not service: return
    csv_data = df.to_csv(index=False).encode('utf-8')
    media_body = MediaIoBaseUpload(io.BytesIO(csv_data), mimetype='text/csv')
    service.files().update(fileId=ORDERS_CSV_ID, media_body=media_body).execute()
    st.toast("Зміни збережено на Drive! ✅")

def show_orders_page(role):
    st.header("📋 Керування замовленнями")
    df = load_data()

    # --- СТВОРЕННЯ НОВОГО ЗАМОВЛЕННЯ ---
    with st.expander("➕ Створити нове замовлення"):
        with st.form("new_order_form"):
            # Автоматичний ID (макс + 1)
            next_id = 1
            if not df.empty and 'ID' in df.columns:
                ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
                if not ids.empty: next_id = int(ids.max() + 1)
            
            st.write(f"**Замовлення №{next_id}**")
            c1, c2 = st.columns(2)
            n_cl = c1.text_input("Клієнт")
            n_ph = c2.text_input("Телефон")
                      
            if st.form_submit_button("Створити порожню картку"):
                new_row = pd.DataFrame([{
                    'ID': str(next_id), 'Дата': datetime.now().strftime("%d.%m.%Y"),
                    'Клієнт': n_cl, 'Телефон': n_ph, 'Товари_JSON': '[]', 'Готовність': 'В черзі'
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.rerun()

    # --- СПИСОК ЗАМОВЛЕНЬ ---
    search = st.text_input("🔍 Пошук замовлення...").lower()
    df_v = df.iloc[::-1] # Нові зверху
    
    if search:
        df_v = df_v[df_v.apply(lambda r: search in str(r.values).lower(), axis=1)]

    for idx, row in df_v.iterrows():
        # Компактна картка
        with st.container(border=True):
            header_col, edit_col = st.columns([4, 1])
            header_col.subheader(f"№{row['ID']} — {row['Клієнт']}")
            
            # --- РЕДАГУВАННЯ КЛІЄНТА (Popover) ---
            with edit_col.popover("✏️ Редагувати"):
                st.write("Дані клієнта")
                new_cl = st.text_input("Ім'я", value=row['Клієнт'], key=f"cl_{row['ID']}")
                new_ph = st.text_input("Тел", value=row['Телефон'], key=f"ph_{row['ID']}")
                if st.button("Зберегти інфо", key=f"sv_cl_{row['ID']}"):
                    df.at[idx, 'Клієнт'] = new_cl
                    df.at[idx, 'Телефон'] = new_ph
                    save_data(df); st.rerun()

            # --- ТОВАРИ ---
            try: items = json.loads(row['Товари_JSON'])
            except: items = []

            for i, it in enumerate(items):
                t_c1, t_c2, t_c3 = st.columns([3, 1, 1])
                t_c1.write(f"• {it['назва']} ({it['арт']})")
                
                # Кнопка PDF
                link = get_pdf_link(it['арт'])
                if link:
                    t_c2.markdown(f'<a href="{link}" target="_blank" class="pdf-button">📕 PDF</a>', unsafe_allow_html=True)
                
                if t_c3.button("🗑️", key=f"del_{row['ID']}_{i}"):
                    items.pop(i)
                    df.at[idx, 'Товари_JSON'] = json.dumps(items, ensure_ascii=False)
                    save_data(df); st.rerun()

            # --- ДОДАВАННЯ ТОВАРУ ---
            with st.expander("➕ Додати товар до цього замовлення"):
                a1, a2, a3 = st.columns([2, 1, 1])
                add_n = a1.text_input("Назва", key=f"addn_{row['ID']}")
                add_a = a2.text_input("Арт", key=f"adda_{row['ID']}")
                add_q = a3.number_input("К-ть", 1, key=f"addq_{row['ID']}")
                if st.button("Додати", key=f"btn_add_{row['ID']}"):
                    items.append({"назва": add_n, "арт": add_a, "к-ть": int(add_q)})
                    df.at[idx, 'Товари_JSON'] = json.dumps(items, ensure_ascii=False)
                    save_data(df); st.rerun()

            st.caption(f"📞 {row['Телефон']} | Статус: {row['Готовність']}")
