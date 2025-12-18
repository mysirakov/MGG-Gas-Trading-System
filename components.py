"""
Custom UI Components for Glass-Morphism Design
"""
import streamlit as st

def load_material_icons():
    """Load Material Icons font"""
    st.markdown("""
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons+Round" rel="stylesheet">
    """, unsafe_allow_html=True)

def page_header(title: str, subtitle: str):
    """Render a styled page header"""
    st.markdown(f"""
        <div style="margin-bottom: 2rem;">
            <h1 style="margin: 0; font-size: 2.25rem; font-weight: 700; color: #0f172a; letter-spacing: -0.02em;">{title}</h1>
            <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem; color: #64748b; font-weight: 400;">{subtitle}</p>
        </div>
    """, unsafe_allow_html=True)

def metric_card(icon: str, label: str, value: str, color: str = "blue"):
    """
    Render a glass-morphism metric card with Material Icon
    
    Args:
        icon: Material Icons name (e.g., 'local_gas_station', 'attach_money')
        label: Metric label text
        value: Metric value text
        color: Icon background color ('blue', 'green', 'orange', 'purple')
    """
    color_map = {
        "blue": ("#dbeafe", "#2563eb"),
        "green": ("#d1fae5", "#059669"),
        "orange": ("#fed7aa", "#ea580c"),
        "purple": ("#e9d5ff", "#9333ea"),
        "red": ("#fee2e2", "#dc2626"),
        "teal": ("#ccfbf1", "#0d9488"),
    }
    bg_color, icon_color = color_map.get(color, color_map["blue"])
    
    st.markdown(f"""
        <div style="
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
            display: flex;
            align-items: center;
            gap: 1.25rem;
            transition: transform 0.2s ease;
            height: 100%;
        ">
            <div style="
                width: 56px;
                height: 56px;
                border-radius: 12px;
                background: {bg_color};
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            ">
                <span class="material-icons-round" style="font-size: 28px; color: {icon_color};">{icon}</span>
            </div>
            <div>
                <p style="margin: 0; font-size: 0.875rem; font-weight: 500; color: #64748b;">{label}</p>
                <p style="margin: 0.25rem 0 0 0; font-size: 1.5rem; font-weight: 700; color: #0f172a; line-height: 1.2;">{value}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

def section_header(icon: str, title: str):
    """Render a section header with icon"""
    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 0.75rem; margin: 1.5rem 0 1rem 0;">
            <span class="material-icons-round" style="color: #3b82f6; font-size: 24px;">{icon}</span>
            <span style="font-size: 1.1rem; font-weight: 600; color: #1e293b;">{title}</span>
        </div>
    """, unsafe_allow_html=True)

def glass_container_start():
    """Start a glass container div"""
    st.markdown("""
        <div style="
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
            margin-bottom: 1.5rem;
        ">
    """, unsafe_allow_html=True)

def glass_container_end():
    """End a glass container div"""
    st.markdown("</div>", unsafe_allow_html=True)

def status_badge(status: str, text: str = None):
    """
    Render a status badge
    
    Args:
        status: 'success', 'warning', 'error', 'processing'
        text: Optional text override
    """
    configs = {
        "success": ("#dcfce7", "#15803d", "check_circle", text or "Completed"),
        "warning": ("#fef3c7", "#b45309", "schedule", text or "Processing"),
        "error": ("#fee2e2", "#dc2626", "error", text or "Pending"),
        "processing": ("#fef3c7", "#b45309", "schedule", text or "Processing"),
    }
    bg, color, icon, label = configs.get(status, configs["success"])
    
    return f"""
        <span style="
            display: inline-flex;
            align-items: center;
            gap: 0.375rem;
            padding: 0.375rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
            background: {bg};
            color: {color};
        ">
            <span class="material-icons-round" style="font-size: 14px;">{icon}</span>
            {label}
        </span>
    """

def info_card(icon: str, title: str, value: str, subtitle: str = None):
    """Render an info card with icon"""
    subtitle_html = f'<p style="margin: 0.25rem 0 0 0; font-size: 0.8rem; color: #94a3b8;">{subtitle}</p>' if subtitle else ''
    
    st.markdown(f"""
        <div style="
            background: rgba(255, 255, 255, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.4);
            border-radius: 12px;
            padding: 1.25rem;
            backdrop-filter: blur(8px);
        ">
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
                <span class="material-icons-round" style="color: #3b82f6; font-size: 20px;">{icon}</span>
                <span style="font-size: 0.9rem; font-weight: 500; color: #64748b;">{title}</span>
            </div>
            <p style="margin: 0; font-size: 1.25rem; font-weight: 700; color: #0f172a;">{value}</p>
            {subtitle_html}
        </div>
    """, unsafe_allow_html=True)

def empty_state(icon: str, message: str):
    """Render an empty state message"""
    st.markdown(f"""
        <div style="
            text-align: center;
            padding: 3rem 2rem;
            color: #94a3b8;
        ">
            <span class="material-icons-round" style="font-size: 48px; opacity: 0.5;">{icon}</span>
            <p style="margin: 1rem 0 0 0; font-size: 1rem;">{message}</p>
        </div>
    """, unsafe_allow_html=True)
