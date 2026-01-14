
import streamlit as st

THEMES = {
    "Light": {
        "primaryColor": "#3b82f6",
        "backgroundColor": "#ffffff",
        "secondaryBackgroundColor": "#f8fafc",
        "textColor": "#0f172a",
    },
    "Dark": {
        "primaryColor": "#8b5cf6",
        "backgroundColor": "#0f172a",
        "secondaryBackgroundColor": "#1e293b",
        "textColor": "#f1f5f9",
    },
    "Ocean": {
        "primaryColor": "#06b6d4",
        "backgroundColor": "#ecfeff",
        "secondaryBackgroundColor": "#cffafe",
        "textColor": "#164e63",
    },
    "Forest": {
        "primaryColor": "#10b981",
        "backgroundColor": "#f0fdf4",
        "secondaryBackgroundColor": "#dcfce7",
        "textColor": "#14532d",
    },
    "Sunset": {
        "primaryColor": "#f97316",
        "backgroundColor": "#fff7ed",
        "secondaryBackgroundColor": "#ffedd5",
        "textColor": "#7c2d12",
    },
    "Purple Haze": {
        "primaryColor": "#a855f7",
        "backgroundColor": "#faf5ff",
        "secondaryBackgroundColor": "#f3e8ff",
        "textColor": "#581c87",
    },
    "Midnight": {
        "primaryColor": "#6366f1",
        "backgroundColor": "#0c0a1f",
        "secondaryBackgroundColor": "#1a1640",
        "textColor": "#e0e7ff",
    }
}

def apply_theme_css(theme_name):
    """Apply theme-specific CSS overrides"""
    theme = THEMES.get(theme_name, THEMES["Light"])
    
    css = f"""
    <style>
    :root {{
        --primary-color: {theme['primaryColor']};
        --background-color: {theme['backgroundColor']};
        --secondary-bg-color: {theme['secondaryBackgroundColor']};
        --text-color: {theme['textColor']};
    }}
    
    /* Override Streamlit's default colors */
    .stApp {{
        background-color: {theme['backgroundColor']};
        color: {theme['textColor']};
    }}
    
    .main {{
        background-color: {theme['backgroundColor']};
    }}
    
    div[data-testid="stSidebar"] {{
        background-color: {theme['secondaryBackgroundColor']};
    }}
    
    /* Metric cards */
    div[data-testid="metric-container"] {{
        background-color: {theme['secondaryBackgroundColor']};
        color: {theme['textColor']};
    }}
    
    /* DataFrames and Charts */
    .stPlotlyChart, div[data-testid="stDataFrame"] {{
        background-color: {theme['secondaryBackgroundColor']};
    }}
    
    /* Tabs */
    .stTabs [aria-selected="true"] {{
        background: {theme['primaryColor']} !important;
        color: white !important;
    }}
    
    /* Buttons */
    .stButton button[kind="primary"] {{
        background-color: {theme['primaryColor']} !important;
        color: white !important;
    }}
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {{
        color: {theme['textColor']};
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def theme_selector():
    """Display theme selector in sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎨 App Theme")
    
    # Initialize theme in session state
    if 'current_theme' not in st.session_state:
        st.session_state.current_theme = "Light"
    
    selected_theme = st.sidebar.selectbox(
        "Choose theme",
        options=list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.current_theme),
        key="theme_selector"
    )
    
    if selected_theme != st.session_state.current_theme:
        st.session_state.current_theme = selected_theme
        st.rerun()
    
    apply_theme_css(st.session_state.current_theme)
    
    return st.session_state.current_theme
