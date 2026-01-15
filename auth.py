import os
import streamlit as st
from supabase import create_client, Client
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

def get_supabase_client() -> Client:
    if 'supabase_client' not in st.session_state:
        st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return st.session_state.supabase_client

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
        client = get_supabase_client()
        response = client.auth.sign_up({
            'email': email,
            'password': password
        })
        
        if response.user:
            if response.session is None:
                return {
                    'success': True,
                    'message': 'Account created! Please check your email to confirm.',
                    'user': response.user,
                    'needs_confirmation': True
                }
            else:
                _store_session(response.session)
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
        client = get_supabase_client()
        response = client.auth.sign_in_with_password({
            'email': email,
            'password': password
        })
        
        if response.user and response.session:
            _store_session(response.session)
            return {
                'success': True,
                'message': 'Login successful!',
                'user': response.user
            }
        return {'success': False, 'message': 'Login failed.', 'user': None}
    
    except Exception as e:
        return {'success': False, 'message': get_friendly_error(e), 'user': None}

def sign_out() -> dict:
    try:
        client = get_supabase_client()
        client.auth.sign_out()
        _clear_session()
        return {'success': True, 'message': 'Logged out successfully.'}
    except Exception as e:
        _clear_session()
        return {'success': False, 'message': get_friendly_error(e)}

def reset_password(email: str) -> dict:
    try:
        client = get_supabase_client()
        client.auth.reset_password_email(email)
        return {
            'success': True,
            'message': 'Password reset email sent! Check your inbox.'
        }
    except Exception as e:
        return {'success': False, 'message': get_friendly_error(e)}

def _store_session(session):
    st.session_state['access_token'] = session.access_token
    st.session_state['refresh_token'] = session.refresh_token
    st.session_state['user'] = session.user
    st.session_state['authenticated'] = True

def _clear_session():
    keys_to_clear = ['access_token', 'refresh_token', 'user', 'authenticated', 'supabase_client']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def is_authenticated() -> bool:
    """Check if user is authenticated and session is valid"""
    return st.session_state.get('authenticated', False) and st.session_state.get('user') is not None

def get_current_user():
    if not is_authenticated():
        return None
    return st.session_state.get('user')

def get_session():
    try:
        client = get_supabase_client()
        return client.auth.get_session()
    except:
        return None

def refresh_session() -> bool:
    try:
        client = get_supabase_client()
        refresh_token = st.session_state.get('refresh_token')
        if refresh_token:
            response = client.auth.refresh_session(refresh_token)
            if response.session:
                _store_session(response.session)
                return True
    except:
        pass
    _clear_session()
    return False

def require_auth():
    """Ensure user is logged in, redirect to login page if not"""
    if not is_authenticated():
        st.switch_page("pages/_Login.py")
    return True
