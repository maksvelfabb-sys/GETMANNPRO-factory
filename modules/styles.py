import streamlit as st

def apply_custom_styles():
    st.markdown("""
        <style>
        .pdf-button {
            display: block; width: 100%; padding: 8px;
            background-color: #ff4b4b; color: white !important;
            text-align: center; text-decoration: none;
            border-radius: 5px; font-weight: bold;
        }
        .pdf-button:hover { background-color: #d33; }
        .stContainer { border: 1px solid #ddd; border-radius: 10px; padding: 15px; }
        </style>
    """, unsafe_allow_html=True)
