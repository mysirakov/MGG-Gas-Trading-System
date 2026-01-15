"""
Custom UI Components for Glass-Morphism Design
"""
import streamlit as st

LOGO_URL = "https://slelguoygbfzlpylpxfs.supabase.co/storage/v1/render/image/public/project-uploads/704afe63-0b4a-4050-803e-5116d1754a58/Untitled-Project-1768468114127.png?width=8000&height=8000&resize=contain"

CRITICAL_CSS = """
<style>
[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.85) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.3) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
}
[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
    padding-top: 1rem !important;
}
[data-testid="stSidebarNav"] {
    background: transparent !important;
}
[data-testid="stSidebarNav"] li {
    margin: 0.5rem 0.75rem !important;
}
[data-testid="stSidebarNav"] a {
    background: transparent !important;
    border-radius: 12px !important;
    padding: 1rem 1.25rem !important;
    color: #475569 !important;
    font-weight: 500 !important;
    font-size: 1.05rem !important;
    transition: none !important;
    border: 1px solid transparent !important;
    display: flex !important;
    align-items: center !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: rgba(255, 255, 255, 0.4) !important;
    color: #1e293b !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: white !important;
    border: 1px solid rgba(255, 255, 255, 0.8) !important;
    color: #0f172a !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
}
[data-testid="stSidebarContent"] {
    opacity: 1 !important;
    visibility: visible !important;
}
[data-testid="stLogo"] {
    width: 180px !important;
    max-width: 180px !important;
    margin: 0 auto 1.5rem auto !important;
    display: block !important;
}
[data-testid="stLogo"] img {
    width: 100% !important;
    height: auto !important;
}
[data-testid="stSidebarHeader"] {
    display: flex !important;
    justify-content: center !important;
    padding: 1.5rem 1rem !important;
}
</style>
"""

def setup_page():
    """Initialize page with logo and critical CSS - call immediately after st.set_page_config()"""
    st.markdown(CRITICAL_CSS, unsafe_allow_html=True)
    st.logo(LOGO_URL, size="large")

def load_material_icons():
    """Load Material Icons font"""
    st.markdown("""
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons+Round" rel="stylesheet">
    """, unsafe_allow_html=True)

def page_header(title: str, subtitle: str):
    """Render a styled page header with mobile navigation"""
    st.markdown(f"""
        <div class="mobile-nav-hint">
            <span class="material-icons-round">menu</span>
            Tap top-left for menu
        </div>
        <div class="header-container">
            <h1 class="page-title">{title}</h1>
            <p class="page-subtitle">{subtitle}</p>
        </div>
    """, unsafe_allow_html=True)

def metric_card(icon: str, label: str, value: str, color: str = "blue"):
    """
    Render a glass-morphism metric card with Material Icon
    """
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon {color}">
                <span class="material-icons-round">{icon}</span>
            </div>
            <div class="metric-content">
                <p class="metric-label">{label}</p>
                <p class="metric-value">{value}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

def section_header(icon: str, title: str):
    """Render a section header with icon"""
    st.markdown(f"""
        <div class="section-header">
            <span class="material-icons-round">{icon}</span>
            <span>{title}</span>
        </div>
    """, unsafe_allow_html=True)

def glass_container_start():
    """Start a glass container div"""
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)

def glass_container_end():
    """End a glass container div"""
    st.markdown("</div>", unsafe_allow_html=True)

def status_badge(status: str, text: str = None):
    """
    Render a status badge
    """
    configs = {
        "success": ("success", "check_circle", text or "Completed"),
        "warning": ("warning", "schedule", text or "Processing"),
        "error": ("error", "error", text or "Pending"),
        "processing": ("warning", "schedule", text or "Processing"),
    }
    cls, icon, label = configs.get(status, configs["success"])
    
    return f"""
        <span class="status-badge {cls}">
            <span class="material-icons-round">{icon}</span>
            {label}
        </span>
    """

def info_card(icon: str, title: str, value: str, subtitle: str = None):
    """Render an info card with icon"""
    subtitle_html = f'<p class="info-subtitle">{subtitle}</p>' if subtitle else ''
    
    st.markdown(f"""
        <div class="info-card">
            <div class="info-header">
                <span class="material-icons-round">{icon}</span>
                <span class="info-title">{title}</span>
            </div>
            <p class="info-value">{value}</p>
            {subtitle_html}
        </div>
    """, unsafe_allow_html=True)

def empty_state(icon: str, message: str):
    """Render an empty state message"""
    st.markdown(f"""
        <div class="empty-state">
            <span class="material-icons-round">{icon}</span>
            <p>{message}</p>
        </div>
    """, unsafe_allow_html=True)


