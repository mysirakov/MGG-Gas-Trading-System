import streamlit as st
from auth import sign_in, sign_up, reset_password, is_authenticated, sign_out, get_current_user
from components import setup_page, load_material_icons

st.set_page_config(
    page_title="Mix Gas Group | Login",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

setup_page()
load_material_icons()

st.markdown("""
<style>
.auth-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
}
.auth-header {
    text-align: center;
    margin-bottom: 2rem;
}
.auth-header h1 {
    color: #1E3A5F;
    font-size: 2rem;
    margin-bottom: 0.5rem;
}
.auth-header p {
    color: #666;
}
div[data-testid="stTabs"] {
    max-width: 450px;
    margin: 0 auto;
}
</style>
""", unsafe_allow_html=True)

if is_authenticated():
    user = get_current_user()
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<div class="auth-header">', unsafe_allow_html=True)
    st.markdown("## Welcome Back!")
    st.markdown(f"**Logged in as:** {user.email}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 Go to Dashboard", use_container_width=True, type="primary"):
            st.switch_page("Dashboard.py")
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            result = sign_out()
            if result['success']:
                st.success(result['message'])
                st.rerun()
            else:
                st.error(result['message'])
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

st.markdown('<div class="auth-header">', unsafe_allow_html=True)
st.markdown("# Mix Gas Group")
st.markdown("Gas Trading Management System")
st.markdown('</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🔑 Login", "📝 Sign Up", "🔄 Reset Password"])

with tab1:
    st.markdown("### Sign In")
    with st.form("login_form", clear_on_submit=False):
        login_email = st.text_input("Email Address", placeholder="you@example.com", key="login_email")
        login_password = st.text_input("Password", type="password", placeholder="Your password", key="login_password")
        
        submit_login = st.form_submit_button("Sign In", use_container_width=True, type="primary")
        
        if submit_login:
            if not login_email or not login_password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Signing in..."):
                    result = sign_in(login_email, login_password)
                if result['success']:
                    st.success(result['message'])
                    st.balloons()
                    st.rerun()
                else:
                    st.error(result['message'])

with tab2:
    st.markdown("### Create Account")
    with st.form("signup_form", clear_on_submit=False):
        signup_email = st.text_input("Email Address", placeholder="you@example.com", key="signup_email")
        signup_password = st.text_input("Password", type="password", placeholder="Min. 6 characters", key="signup_password")
        signup_confirm = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="signup_confirm")
        
        submit_signup = st.form_submit_button("Create Account", use_container_width=True, type="primary")
        
        if submit_signup:
            if not signup_email or not signup_password or not signup_confirm:
                st.error("Please fill in all fields.")
            elif signup_password != signup_confirm:
                st.error("Passwords do not match.")
            elif len(signup_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                with st.spinner("Creating account..."):
                    result = sign_up(signup_email, signup_password)
                if result['success']:
                    if result.get('needs_confirmation'):
                        st.success(result['message'])
                        st.info("📧 Check your email inbox and click the confirmation link to activate your account.")
                    else:
                        st.success(result['message'])
                        st.balloons()
                        st.rerun()
                else:
                    st.error(result['message'])

with tab3:
    st.markdown("### Reset Password")
    st.markdown("Enter your email address and we'll send you a link to reset your password.")
    
    with st.form("reset_form", clear_on_submit=False):
        reset_email = st.text_input("Email Address", placeholder="you@example.com", key="reset_email")
        
        submit_reset = st.form_submit_button("Send Reset Link", use_container_width=True, type="primary")
        
        if submit_reset:
            if not reset_email:
                st.error("Please enter your email address.")
            else:
                with st.spinner("Sending reset email..."):
                    result = reset_password(reset_email)
                if result['success']:
                    st.success(result['message'])
                    st.info("📧 Check your email inbox for the password reset link.")
                else:
                    st.error(result['message'])
