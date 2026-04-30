import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

st.set_page_config(
    page_title="E-commerce Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }
        .stApp {
            background-color: #F0F4F8;
        }
        [data-testid="stSidebar"] {
            background-color: #1A2B4A !important;
        }
        [data-testid="stSidebar"] * {
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] .stRadio label {
            font-size: 15px !important;
            font-weight: 500 !important;
        }
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stMultiSelect label {
            font-size: 13px !important;
            color: #94A3B8 !important;
        }
        .block-container {
            padding-top: 2rem !important;
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_nav() -> str:
    with st.sidebar:
        st.markdown(
            "<h2 style='color:#FFFFFF;font-size:20px;font-weight:700;margin-bottom:0'>📊 E-commerce</h2>"
            "<p style='color:#94A3B8;font-size:13px;margin-top:2px;margin-bottom:0'>Analytics Dashboard</p>",
            unsafe_allow_html=True,
        )
        st.divider()
        page = st.radio(
            "Navegação",
            options=["📈 Vendas", "👥 Clientes", "💰 Pricing"],
            label_visibility="collapsed",
        )
        st.divider()
    return page


def main():
    inject_css()
    page = sidebar_nav()

    if page == "📈 Vendas":
        from views.vendas import render
        render()
    elif page == "👥 Clientes":
        from views.clientes import render
        render()
    elif page == "💰 Pricing":
        from views.pricing import render
        render()


main()
