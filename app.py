import streamlit as st
import sqlite3
from PIL import Image
import io
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta

try:
    from streamlit_cookies_controller import CookieController
except ImportError:
    st.error("Please install: pip install streamlit-cookies-controller")
    st.stop()


# ============================================================
# ENGINEER AHMAD - CAR KEY INVENTORY
# (Single-admin edition: no registration/approval flow,
#  long-lived login so you don't have to sign in every visit)
# ============================================================

DB_NAME = "car_keys.db"
LOGIN_DAYS = 365           # how long the "stay signed in" cookie lasts
LOW_STOCK_DEFAULT = 5


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Engineer Ahmad | Car Key Inventory",
    page_icon="🔑",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# COLORS / UI
# ============================================================

st.markdown("""
