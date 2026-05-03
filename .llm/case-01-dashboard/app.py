from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from filters import render_sidebar

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
            background-color: #F8FAFC;
        }
        [data-testid="stHeader"] {
            background: transparent;
            height: 0;
        }
        [data-testid="stToolbar"] {
            right: 1rem;
            top: 0.5rem;
        }
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
            color: #0F172A;
        }
        [data-testid="stSidebar"] label {
            color: #334155 !important;
            font-size: 13px !important;
            font-weight: 700 !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"][aria-disabled="true"] {
            opacity: 0.55;
        }
        [data-testid="stSidebar"] label:has(+ div [aria-disabled="true"]) {
            color: #94A3B8 !important;
        }
        .sidebar-brand {
            padding: 0.25rem 0 0.75rem;
        }
        .sidebar-eyebrow {
            color: #0072B2;
            font-size: 13px !important;
            font-weight: 600 !important;
            margin-bottom: 0.35rem;
        }
        .sidebar-title {
            color: #0F172A;
            font-size: 22px;
            font-weight: 700;
            line-height: 1.2;
            margin: 0 0 0.4rem;
        }
        .sidebar-description {
            color: #475569;
            font-size: 14px;
            line-height: 1.45;
            margin: 0;
        }
        .sidebar-section-title {
            color: #64748B;
            font-size: 12px;
            font-weight: 700;
            margin: 0.35rem 0 0.75rem;
            text-transform: uppercase;
        }
        .block-container {
            padding-top: 2rem !important;
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
        }
        h1, h2, h3, h4, h5, h6, p, label {
            color: #0F172A;
        }
        [data-testid="stMarkdownContainer"] h3 {
            color: #0F172A;
            font-weight: 700;
        }
        [data-testid="stDataFrame"] {
            color: #0F172A;
        }
        [data-testid="stRadio"] div[role="radiogroup"] {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
        }
        [data-testid="stRadio"] div[role="radiogroup"] label {
            background-color: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            color: #334155;
            font-weight: 700;
            min-height: 44px;
            padding: 0.45rem 1rem;
        }
        [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
            background-color: #EFF6FF;
            border-color: #0072B2;
            color: #0F172A;
        }
        [data-testid="stRadio"] div[role="radiogroup"] label p {
            font-weight: 700;
        }
        .insight-box {
            background-color: #FFFBEB;
            border: 1px solid #FCD34D;
            border-left: 4px solid #E69F00;
            border-radius: 8px;
            color: #0F172A;
            line-height: 1.55;
            padding: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    inject_css()

    page = st.radio(
        "Página",
        options=["Vendas", "Clientes", "Pricing"],
        horizontal=True,
        label_visibility="collapsed",
        key="main_page",
    )
    st.divider()

    selection = render_sidebar(page)

    if page == "Vendas":
        from views.vendas import render

        render(selection)
    elif page == "Clientes":
        from views.clientes import render

        render(selection)
    else:
        from views.pricing import render

        render(selection)


main()
