import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import hashlib
import base64
import os

COOKIE_NAME = "mgg_auth_token"
COOKIE_EXPIRY_DAYS = 30

_cookie_manager = None

def get_cookie_manager():
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = stx.CookieManager(key="mgg_cookie_manager")
    return _cookie_manager

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
        cm = get_cookie_manager()
        encrypted = _encrypt_token(refresh_token)
        expires = datetime.now() + timedelta(days=COOKIE_EXPIRY_DAYS)
        cm.set(COOKIE_NAME, encrypted, expires_at=expires)
        return True
    except Exception as e:
        return False

def get_auth_cookie() -> str:
    try:
        cm = get_cookie_manager()
        encrypted = cm.get(COOKIE_NAME)
        if encrypted:
            return _decrypt_token(encrypted)
        return None
    except:
        return None

def delete_auth_cookie() -> bool:
    try:
        cm = get_cookie_manager()
        cm.delete(COOKIE_NAME)
        return True
    except:
        return False

def cookies_available() -> bool:
    try:
        cm = get_cookie_manager()
        cm.get_all()
        return True
    except:
        return False
