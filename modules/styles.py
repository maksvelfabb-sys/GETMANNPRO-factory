import streamlit as st

def apply_custom_styles():
    st.markdown("""
    <style>
    /* Компактність карток */
    [data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"] {
        gap: 0.5rem !important;
        padding: 0.5rem !important;
    }
    
    /* Кольори статусів */
    .status-v-cherzi { border-left: 10px solid #FFA500 !important; background-color: #FFF5E6; } /* Помаранчевий */
    .status-v-roboti { border-left: 10px solid #007BFF !important; background-color: #E6F0FF; } /* Синій */
    .status-gotovo { border-left: 10px solid #28A745 !important; background-color: #EAF9EE; }   /* Зелений */
    .status-vidpravleno { border-left: 10px solid #6C757D !important; opacity: 0.8; }         /* Сірий */

    /* Стиль для тексту всередині компактної картки */
    .card-id { font-size: 1.1rem; font-weight: bold; color: #1E1E1E; }
    .card-info { font-size: 0.9rem; color: #555; }
    
    /* Кнопка PDF */
    .pdf-button {
        background-color: #FF4B4B;
        color: white !important;
        padding: 2px 8px;
        border-radius: 4px;
        text-decoration: none;
        font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)
