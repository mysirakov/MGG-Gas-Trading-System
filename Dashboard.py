import streamlit as st
from cookie_manager import get_cookie_manager
from auth import restore_session, is_authenticated, sign_out, get_current_user
from components import setup_page, load_material_icons

st.set_page_config(
    page_title="Mix Gas Group",
    page_icon="https://slelguoygbfzlpylpxfs.supabase.co/storage/v1/render/image/public/project-uploads/704afe63-0b4a-4050-803e-5116d1754a58/Untitled-Project-1768468114127.png?width=8000&height=8000&resize=contain",
    layout="wide",
    initial_sidebar_state="expanded"
)

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

get_cookie_manager()

restore_session()

if not is_authenticated():
    from views.login import show_login_page
    show_login_page()
    st.stop()

setup_page()
load_material_icons()

LOGO_URL = "https://slelguoygbfzlpylpxfs.supabase.co/storage/v1/render/image/public/project-uploads/704afe63-0b4a-4050-803e-5116d1754a58/logo-mgg-1768474458463.png?width=8000&height=8000&resize=contain"

if 'current_page' not in st.session_state:
    st.session_state.current_page = 'Dashboard'

with st.sidebar:
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 1.5rem;">
        <img src="{LOGO_URL}" alt="Mix Gas Group" style="max-width: 180px;">
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <style>
    div[data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebar"] > div:first-child {padding-top: 1rem;}
    
    /* Style radio buttons as menu items */
    div[data-testid="stRadio"] > label {display: none;}
    div[data-testid="stRadio"] > div {gap: 0.25rem !important;}
    div[data-testid="stRadio"] > div > label {
        display: flex;
        align-items: center;
        padding: 0.75rem 1rem;
        margin: 0;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 500;
        color: #334155;
        background: transparent;
        transition: all 0.2s;
    }
    div[data-testid="stRadio"] > div > label:hover {
        background: rgba(59, 130, 246, 0.1);
        color: #1e40af;
    }
    div[data-testid="stRadio"] > div > label[data-checked="true"] {
        background: rgba(59, 130, 246, 0.15);
        color: #1e40af;
        font-weight: 600;
    }
    div[data-testid="stRadio"] > div > label > div:first-child {
        display: none !important;
    }
    div[data-testid="stRadio"] > div > label > div:last-child {
        margin-left: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    nav_options = ["Dashboard", "Purchases", "Sales", "Payments", "Seller Balance", "Analytics", "Settings"]
    
    current_index = nav_options.index(st.session_state.current_page) if st.session_state.current_page in nav_options else 0
    
    selected = st.radio(
        "Navigation",
        nav_options,
        index=current_index,
        label_visibility="collapsed",
        key="main_nav"
    )
    
    if selected != st.session_state.current_page:
        st.session_state.current_page = selected
        st.rerun()
    
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.divider()
    
    user = get_current_user()
    if user:
        st.markdown(f"""
        <div style="padding: 0.5rem; font-size: 0.85rem; color: #64748b;">
            Signed in as:<br/>
            <strong style="color: #334155;">{user.email}</strong>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("Logout", key="sidebar_logout", use_container_width=True):
        sign_out()
        st.rerun()

current_page = st.session_state.current_page

if current_page == "Dashboard":
    from views.dashboard import show_dashboard
    show_dashboard()
elif current_page == "Purchases":
    from views.purchases import show_purchases
    show_purchases()
elif current_page == "Sales":
    from views.sales import show_sales
    show_sales()
elif current_page == "Payments":
    from views.payments import show_payments
    show_payments()
elif current_page == "Seller Balance":
    from views.seller_balance import show_seller_balance
    show_seller_balance()
elif current_page == "Analytics":
    from views.analytics import show_analytics
    show_analytics()
elif current_page == "Settings":
    from views.settings import show_settings
    show_settings()
