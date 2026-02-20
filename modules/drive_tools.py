# Додайте новий ID до списку конфігурацій (створіть порожній CSV на Drive і вставте сюди його ID)
DRAWINGS_MAP_CSV_ID = "ВАШ_ID_ФАЙЛУ_DRAWINGS_MAP" # Замініть на реальний ID

def get_all_drawings_in_folder(folder_id="ID_ВАШОЇ_ПАПКИ_З_КРЕСЛЕННЯМИ"):
    """Отримує список усіх файлів з конкретної папки Drive"""
    try:
        service = get_drive_service()
        if not service: return []
        
        # Шукаємо файли тільки в конкретній папці
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query, 
            fields="files(id, name, webViewLink)",
            pageSize=1000
        ).execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"Помилка отримання списку файлів: {e}")
        return []

def load_drawing_map():
    """Завантажує словник відповідностей {file_id: custom_name}"""
    df = load_csv(DRAWINGS_MAP_CSV_ID)
    if df.empty:
        return {}
    # Перетворюємо DataFrame у словник для швидкого пошуку
    return dict(zip(df['file_id'].astype(str), df['custom_name'].astype(str)))

def save_drawing_map(mapping_dict):
    """Зберігає словник відповідностей у CSV на Drive"""
    df = pd.DataFrame(list(mapping_dict.items()), columns=['file_id', 'custom_name'])
    return save_csv(DRAWINGS_MAP_CSV_ID, df)

def get_link_by_mapped_name(custom_name):
    """Шукає посилання на файл за його ПРИСВОЄНИМ іменем"""
    mapping = load_drawing_map()
    # Шукаємо file_id, якому відповідає custom_name
    file_id = None
    for fid, name in mapping.items():
        if name.lower().strip() == str(custom_name).lower().strip():
            file_id = fid
            break
    
    if file_id:
        try:
            service = get_drive_service()
            file = service.files().get(fileId=file_id, fields="webViewLink").execute()
            return file.get('webViewLink')
        except:
            return None
    return None
