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
    """Get or create Supabase client - creates fresh client each time for reliability"""
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

def _sync_session_state():
    """Force sync session state to frontend - workaround for Streamlit bug"""
    try:
        for key in list(st.session_state.keys()):
            st.session_state[key] = st.session_state[key]
    except:
        pass

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
                'user': response.user,
                'refresh_token': response.session.refresh_token
            }
        return {'success': False, 'message': 'Login failed.', 'user': None}
    
    except Exception as e:
        return {'success': False, 'message': get_friendly_error(e), 'user': None}

def sign_out() -> dict:
    try:
        client = get_supabase_client()
        client.auth.sign_out()
    except:
        pass
    _clear_session()
    return {'success': True, 'message': 'Logged out successfully.'}

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
    """Store session in both session_state AND query params for iframe persistence"""
    st.session_state['access_token'] = session.access_token
    st.session_state['refresh_token'] = session.refresh_token
    st.session_state['user'] = session.user
    st.session_state['authenticated'] = True
    
    # Store refresh token in URL query params - this SURVIVES page switches in iframe
    st.query_params['rt'] = session.refresh_token
    
    # Try to set session on client
    try:
        client = get_supabase_client()
        client.auth.set_session(session.access_token, session.refresh_token)
    except:
        pass
    
    # Force sync to frontend
    _sync_session_state()

def _clear_session():
    """Clear all session data"""
    keys_to_clear = ['access_token', 'refresh_token', 'user', 'authenticated', 'supabase_client']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear query params
    if 'rt' in st.query_params:
        del st.query_params['rt']

def is_authenticated() -> bool:
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False) and st.session_state.get('user') is not None

def get_current_user():
    """Get current authenticated user"""
    if not is_authenticated():
        return None
    return st.session_state.get('user')

def get_session():
    """Get current session from Supabase client"""
    try:
        client = get_supabase_client()
        return client.auth.get_session()
    except:
        return None

def refresh_session() -> bool:
    """Refresh the current session"""
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

def restore_session() -> bool:
    """
    CRITICAL: Restore session from query params (primary) or session state (fallback)
    This is the key function that makes auth work in iframes
    """
    # Already authenticated in this run
    if is_authenticated():
        return True
    
    # PRIORITY 1: Check query params (survives page switches in iframe)
    refresh_token = st.query_params.get('rt')
    
    # PRIORITY 2: Check session state (may not survive page switch)
    if not refresh_token:
        refresh_token = st.session_state.get('refresh_token')
    
    if refresh_token:
        try:
            # Create a fresh client to ensure clean state
            client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            st.session_state.supabase_client = client
            
            response = client.auth.refresh_session(refresh_token)
            if response and response.session:
                _store_session(response.session)
                return True
        except Exception as e:
            # Token is invalid/expired, clear it
            if 'rt' in st.query_params:
                del st.query_params['rt']
            _clear_session()
    
    return False

def require_auth():
    """
    Require authentication - returns True if authenticated, False otherwise.
    Does NOT redirect - the main app handles showing login when needed.
    """
    return restore_session()
