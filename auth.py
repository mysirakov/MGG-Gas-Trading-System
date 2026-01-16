import os
import streamlit as st
from st_supabase_connection import SupabaseConnection
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

ERROR_MESSAGES = {
    'invalid_grant': 'Invalid email or password. Please try again.',
    'invalid_credentials': 'Invalid email or password. Please try again.',
    'user_already_exists': 'An account with this email already exists.',
    'email_exists': 'An account with this email already exists.',
    'weak_password': 'Password is too weak. Use at least 6 characters with letters and numbers.',
    'email_not_confirmed': 'Please confirm your email before logging in.',
    'over_request_limit': 'Too many requests. Please wait a moment and try again.',
    'over_email_send_rate_limit': 'Too many requests. Please wait a moment and try again.',
    'rate_limit': 'Too many requests. Please wait a moment and try again.',
    'session_expired': 'Your session has expired. Please log in again.',
    'network_error': 'Connection error. Please check your internet and try again.',
}

@st.cache_resource
def get_supabase_connection():
    return st.connection(
        "supabase",
        type=SupabaseConnection,
        url=SUPABASE_URL,
        key=SUPABASE_ANON_KEY,
    )

def get_supabase_client():
    conn = get_supabase_connection()
    return conn.client

def get_friendly_error(error) -> str:
    error_code = getattr(error, 'code', None)
    error_status = getattr(error, 'status', None)
    error_msg = str(error).lower()
    
    if error_code in ERROR_MESSAGES:
        return ERROR_MESSAGES[error_code]
    
    if error_status == 429:
        return ERROR_MESSAGES['rate_limit']
    if error_status == 401:
        return ERROR_MESSAGES['invalid_credentials']
    
    if 'already registered' in error_msg or 'already exists' in error_msg:
        return ERROR_MESSAGES['user_already_exists']
    if 'weak' in error_msg or ('password' in error_msg and 'short' in error_msg):
        return ERROR_MESSAGES['weak_password']
    if 'invalid' in error_msg and ('credentials' in error_msg or 'grant' in error_msg or 'login' in error_msg):
        return ERROR_MESSAGES['invalid_credentials']
    if 'email rate limit' in error_msg or 'over_email_send_rate_limit' in error_msg:
        return ERROR_MESSAGES['over_email_send_rate_limit']
    
    return f'An error occurred: {str(error)}'

def sign_up(email: str, password: str) -> dict:
    try:
        conn = get_supabase_connection()
        response = conn.auth.sign_up(
            email=email,
            password=password,
        )
        
        if response and response.user:
            if not response.session:
                return {
                    'success': True,
                    'message': 'Account created! Please check your email to confirm.',
                    'user': response.user,
                    'needs_confirmation': True
                }
            else:
                st.session_state['authenticated'] = True
                st.session_state['user'] = response.user
                return {
                    'success': True,
                    'message': 'Account created successfully!',
                    'user': response.user,
                    'needs_confirmation': False
                }
        return {'success': False, 'message': 'Failed to create account.', 'user': None}
    
    except Exception as e:
        return {'success': False, 'message': get_friendly_error(e), 'user': None}

def sign_in(email: str, password: str) -> dict:
    try:
        conn = get_supabase_connection()
        response = conn.auth.sign_in_with_password(
            email=email,
            password=password,
        )
        
        if response and response.user:
            st.session_state['authenticated'] = True
            st.session_state['user'] = response.user
            return {
                'success': True,
                'message': 'Login successful!',
                'user': response.user,
            }
        return {'success': False, 'message': 'Login failed.', 'user': None}
    
    except Exception as e:
        return {'success': False, 'message': get_friendly_error(e), 'user': None}

def sign_out() -> dict:
    try:
        conn = get_supabase_connection()
        conn.auth.sign_out()
    except:
        pass
    
    keys_to_clear = ['user', 'authenticated', 'user_role']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    return {'success': True, 'message': 'Logged out successfully.'}

def reset_password(email: str) -> dict:
    try:
        conn = get_supabase_connection()
        conn.auth.reset_password_for_email(email=email)
        return {
            'success': True,
            'message': 'Password reset email sent! Check your inbox.'
        }
    except Exception as e:
        return {'success': False, 'message': get_friendly_error(e)}

def is_authenticated() -> bool:
    conn = get_supabase_connection()
    session = conn.auth.get_session()
    if session and session.user:
        st.session_state['authenticated'] = True
        st.session_state['user'] = session.user
        return True
    return False

def get_current_user():
    conn = get_supabase_connection()
    session = conn.auth.get_session()
    if session and session.user:
        return session.user
    return None

def is_admin() -> bool:
    user = get_current_user()
    if not user:
        return False
    
    if 'user_role' in st.session_state:
        return st.session_state['user_role'] == 'admin'
    
    try:
        client = get_supabase_client()
        result = client.table('user_roles').select('role').eq('user_id', user.id).execute()
        if result.data and len(result.data) > 0:
            role = result.data[0].get('role', 'viewer')
        else:
            role = 'viewer'
        st.session_state['user_role'] = role
        return role == 'admin'
    except:
        return False

def get_session():
    try:
        conn = get_supabase_connection()
        return conn.auth.get_session()
    except:
        return None

def restore_session() -> bool:
    return is_authenticated()

def require_auth():
    return restore_session()
