import os
import json
import time
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv
from streamlit_js_eval import streamlit_js_eval

load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')

SESSION_KEY = 'mgg_auth_session'
SESSION_DURATION_DAYS = 30
SESSION_DURATION_SECONDS = SESSION_DURATION_DAYS * 24 * 60 * 60

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
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

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

def _save_session_to_storage(access_token: str, refresh_token: str, user_id: str, user_email: str):
    expires_at = int(time.time()) + SESSION_DURATION_SECONDS
    session_data = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user_id': user_id,
        'user_email': user_email,
        'expires_at': expires_at
    }
    json_str = json.dumps(session_data).replace("'", "\\'").replace('"', '\\"')
    js_code = f'localStorage.setItem("{SESSION_KEY}", "{json_str}")'
    streamlit_js_eval(js_expressions=js_code, key=f"save_session_{int(time.time()*1000)}")

def _clear_session_from_storage():
    streamlit_js_eval(js_expressions=f'localStorage.removeItem("{SESSION_KEY}")', key=f"clear_session_{int(time.time()*1000)}")

def sign_up(email: str, password: str) -> dict:
    try:
        client = get_supabase_client()
        response = client.auth.sign_up({
            'email': email,
            'password': password,
        })
        
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
                _save_session_to_storage(
                    response.session.access_token,
                    response.session.refresh_token,
                    response.user.id,
                    response.user.email
                )
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
            'password': password,
        })
        
        if response and response.user:
            st.session_state['authenticated'] = True
            st.session_state['user'] = response.user
            _save_session_to_storage(
                response.session.access_token,
                response.session.refresh_token,
                response.user.id,
                response.user.email
            )
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
        client = get_supabase_client()
        client.auth.sign_out()
    except:
        pass
    
    _clear_session_from_storage()
    
    keys_to_clear = ['user', 'authenticated', 'user_role', '_session_restore_complete', '_restore_attempt']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    return {'success': True, 'message': 'Logged out successfully.'}

def reset_password(email: str) -> dict:
    try:
        client = get_supabase_client()
        client.auth.reset_password_for_email(email)
        return {
            'success': True,
            'message': 'Password reset email sent! Check your inbox.'
        }
    except Exception as e:
        return {'success': False, 'message': get_friendly_error(e)}

def restore_session() -> bool:
    if st.session_state.get('authenticated'):
        return True
    
    restore_key = f"restore_session_{st.session_state.get('_restore_attempt', 0)}"
    
    if st.session_state.get('_session_restore_complete'):
        return False
    
    stored_data = streamlit_js_eval(
        js_expressions=f'localStorage.getItem("{SESSION_KEY}")', 
        key=restore_key
    )
    
    if stored_data is None:
        return False
    
    st.session_state['_session_restore_complete'] = True
    
    if not stored_data:
        return False
    
    try:
        session_data = json.loads(stored_data)
        
        expires_at = session_data.get('expires_at', 0)
        if expires_at and int(time.time()) > expires_at:
            _clear_session_from_storage()
            return False
        
        client = get_supabase_client()
        response = client.auth.set_session(
            session_data['access_token'],
            session_data['refresh_token']
        )
        
        if response and response.user:
            st.session_state['authenticated'] = True
            st.session_state['user'] = response.user
            if response.session:
                _save_session_to_storage(
                    response.session.access_token,
                    response.session.refresh_token,
                    response.user.id,
                    response.user.email
                )
            return True
    except Exception as e:
        _clear_session_from_storage()
    
    return False

def is_authenticated() -> bool:
    return st.session_state.get('authenticated', False)

def get_current_user():
    return st.session_state.get('user')

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
        client = get_supabase_client()
        return client.auth.get_session()
    except:
        return None

def require_auth():
    return restore_session()
