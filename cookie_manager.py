import streamlit as st
from streamlit_cookies_controller import CookieController
from datetime import datetime, timedelta
import base64
import os

COOKIE_NAME = "mgg_auth_token"
COOKIE_EXPIRY_DAYS = 30

def get_cookie_controller():
    if 'cookie_controller' not in st.session_state:
        st.session_state.cookie_controller = CookieController()
    return st.session_state.cookie_controller

def _encrypt_token(token: str) -> str:
    secret = os.environ.get('SUPABASE_ANON_KEY', 'fallback_secret')[:32]
    combined = f"{secret}:{token}"
    encoded = base64.b64encode(combined.encode()).decode()
    return encoded

def _decrypt_token(encrypted: str) -> str:
    try:
        decoded = base64.b64decode(encrypted.encode()).decode()
        secret = os.environ.get('SUPABASE_ANON_KEY', 'fallback_secret')[:32]
        if decoded.startswith(f"{secret}:"):
            return decoded[len(secret) + 1:]
        return None
    except:
        return None

def store_auth_cookie(refresh_token: str) -> bool:
    try:
        controller = get_cookie_controller()
        encrypted = _encrypt_token(refresh_token)
        expires = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
        controller.set(COOKIE_NAME, encrypted, expires=expires)
        return True
    except Exception as e:
        return False

def get_auth_cookie() -> str:
    try:
        controller = get_cookie_controller()
        encrypted = controller.get(COOKIE_NAME)
        if encrypted:
            return _decrypt_token(encrypted)
        return None
    except:
        return None

def delete_auth_cookie() -> bool:
    try:
        controller = get_cookie_controller()
        controller.remove(COOKIE_NAME)
        return True
    except:
        return False

def cookies_available() -> bool:
    try:
        controller = get_cookie_controller()
        controller.getAll()
        return True
    except:
        return False
