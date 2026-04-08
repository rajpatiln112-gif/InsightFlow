"""
🤖 InsightFlow
A premium Streamlit application for automated data exploration and AI-powered insights.
"""

import streamlit as st
import pandas as pd
import os
import sys
import socket
import subprocess
import time
from groq import Groq
import streamlit.components.v1 as components
from dotenv import load_dotenv
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

load_dotenv()

# ── Project Core Paths ───────────────────────────────────────────────
v_project_root = os.path.dirname(os.path.abspath(__file__))
if v_project_root not in sys.path:
    sys.path.insert(0, v_project_root)

# ── Page Configuration ───────────────────────────────────────────────
st.set_page_config(page_title="InsightFlow", page_icon="🌊", layout="wide")

# ── Load Custom CSS ──────────────────────────────────────────────────
css_path = os.path.join(v_project_root, "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Auto-start Backend Server ────────────────────────────────────────
def is_port_open(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((host, port)) == 0
    except: return False

def start_backend():
    host, port = "127.0.0.1", 8000
    if is_port_open(host, port): return True
    try:
        backend_cmd = f'"{sys.executable}" -m uvicorn backend.main:app --host {host} --port {port}'
        # Redirect output to DEVNULL to avoid creating a log file
        subprocess.Popen(backend_cmd, cwd=v_project_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        
        with st.status("🚀 Starting Backend...", expanded=False) as status:
            for _ in range(20):
                if is_port_open(host, port): 
                    return True
                time.sleep(1)
            status.update(label="❌ Backend Offline", state="error", expanded=True)
            return False
    except Exception as e:
        st.error(f"Failed to start backend: {e}")
        return False

if "backend_attempted" not in st.session_state:
    st.session_state.backend_attempted = True
    if not start_backend():
        st.error("⚠️ **SYSTEM CONFLICT**: Backend failed to initialize. Please check `backend_log.txt` or run uvicorn manually.")

# ── Module Imports ───────────────────────────────────────────────────
try:
    from modules.data_handler import load_data, get_data_summary
    from modules.data_cleaning import render_data_cleaning
    from modules.eda_engine import render_eda
    from modules.ai_chat import render_chat, render_query_history
    from modules.viz_builder import render_viz_builder
    from modules.advanced_analytics import render_advanced_analytics
    from modules.auto_analyst import render_auto_flow
    from auth_service import login_user, register_user, google_login
    from query_service import fix_sql_query
except Exception as e:
    st.error(f"FATAL SYNC ERROR: {e}")
    st.stop()

# ── Session State Initialization ─────────────────────────────────────

# Persist login across browser refreshes via URL parameters
qs_logged_in = st.query_params.get("logged_in") == "true"
qs_username = st.query_params.get("username", "")

defaults = {
    "df": None, "groq_client": None, "api_key_set": False, 
    "logged_in": qs_logged_in, "username": qs_username, "access_token": "", 
    "dataset_name": None, "dashboard_charts": []
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

# ══════════════════════════════════════════════════════════════════════
#   AUTH PAGE
# ══════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_oauth_memory():
    return {}

oauth_states = get_oauth_memory()


def render_auth_page():
    st.markdown(
        """
        <div style='text-align:center; padding: 6rem 1rem 2rem;'>
            <div class="hero-title">INSIGHT<span style='opacity:0.3;'> | </span>FLOW</div>
            <div style="color: #2dd4bf; font-size: 0.8rem; letter-spacing: 0.8rem; font-weight: 500; opacity: 0.6; text-transform: uppercase;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    with col2:
        tab = st.radio("System Access", ["Login", "Register"], label_visibility="collapsed", horizontal=True)
        
        if tab == "Login":
            with st.form("login_form"):
                u = st.text_input("Username", placeholder="Username", key="l_u", label_visibility="collapsed")
                p = st.text_input("Password", type="password", placeholder="Password", key="l_p", label_visibility="collapsed")
                if st.form_submit_button("Login", use_container_width=True):
                    if u and p:
                        with st.spinner("Logging in..."):
                            res = login_user(u, p)
                        if res["success"]:
                            st.session_state.logged_in = True
                            st.session_state.username = u
                            st.session_state.access_token = res.get("token", "")
                            st.query_params["logged_in"] = "true"
                            st.query_params["username"] = u
                            st.rerun()
                        else: st.error(res["message"])
                    else: st.error("Credentials Required")
            
            st.markdown("<div style='text-align:center; margin: 1rem 0; opacity: 0.5;'>OR</div>", unsafe_allow_html=True)
            
            # --- GOOGLE SIGN IN ---
            if not os.path.exists("client_secret.json"):
                st.warning("⚠️ `client_secret.json` not found. Please download it from Google Cloud Console and place it in the project root.")
            else:
                scopes = ["openid", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"]
                redirect_uri = "http://localhost:8501"
                
                # Handle the Google redirect callback
                if "code" in st.query_params:
                    auth_code = st.query_params.get("code")
                    auth_state = st.query_params.get("state")
                    st.query_params.clear()
                    
                    try:
                        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                            "client_secret.json", scopes=scopes, redirect_uri=redirect_uri
                        )
                        # CRITICAL FIX: Restore the PKCE code_verifier from the session state
                        cv = st.session_state.get("oauth_code_verifier")
                        if not cv and auth_state:
                            cv = oauth_states.get(auth_state)
                        flow.code_verifier = cv
                        flow.fetch_token(code=auth_code)
                        
                        credentials = flow.credentials
                        user_info_service = build(serviceName="oauth2", version="v2", credentials=credentials)
                        user_info = user_info_service.userinfo().get().execute()
                        
                        st.session_state.logged_in = True
                        st.session_state.username = user_info.get('name', 'Google User')
                        st.query_params.clear()
                        st.query_params["logged_in"] = "true"
                        st.query_params["username"] = st.session_state.username
                        st.rerun()
                    except Exception as e:
                        st.error(f"Authentication Failed: {e}")
                else:
                    # Generate the Google Login Link
                    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                        "client_secret.json", scopes=scopes, redirect_uri=redirect_uri
                    )
                    auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
                    
                    # Store the generated PKCE code verifier in session state before redirecting
                    cv = getattr(flow, "code_verifier", None)
                    st.session_state["oauth_code_verifier"] = cv
                    if state and cv:
                        oauth_states[state] = cv
                    
                    # Styled Login Button matching Streamlit aesthetics
                    google_btn = f"""
                    <div style="display: flex; justify-content: center; margin-top: 10px;">
                        <a href="{auth_url}" target="_self" style="background-color: #4285f4; color: #fff; text-decoration: none; text-align: center; font-size: 16px; margin: 4px 2px; padding: 8px 12px; border-radius: 4px; display: flex; align-items: center; width: 100%; justify-content: center; border: 1px solid #ddd;">
                            <img src="https://lh3.googleusercontent.com/COxitqgJr1sJnIDe8-jiKhxDx1FrYbtRHKJ9z_hELisAlapwE9LUPh6fcXIfb5vwpbMl4xl9H9TRFPc5NOO8Sb3VSgIBrfRYvW6cUA" alt="Google logo" style="margin-right: 12px; width: 22px; height: 22px; background-color: white; border-radius: 50%;">
                            <span style="font-family: 'Roboto', sans-serif; font-weight: 500;">Sign in with Google</span>
                        </a>
                    </div>
                    """
                    st.markdown(google_btn, unsafe_allow_html=True)
        else:
            with st.form("register_form"):
                ru = st.text_input("Username", placeholder="Username", key="r_u", label_visibility="collapsed")
                rm = st.text_input("Email", placeholder="Email", key="r_m", label_visibility="collapsed")
                rp = st.text_input("Password", type="password", placeholder="Password", key="r_p", label_visibility="collapsed")
                if st.form_submit_button("Register", use_container_width=True):
                    if ru and rm and rp:
                        with st.spinner("Registering..."):
                            res = register_user(ru, rm, rp)
                        if res["success"]: st.success("Account Created")
                        else: st.error(res["message"])
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
#   NULL VALUE HANDLING
# ══════════════════════════════════════════════════════════════════════

def render_null_handler(df):
    null_count = df.isnull().sum().sum()
    if null_count == 0:
        return True, df

    if null_count > 10:
        st.error("🚨 **CRITICAL DATA GAP**: Please fill the null values and re-upload the database.")
        st.info(f"Total missing values detected: {null_count}")
        return False, df
    else:
        st.warning(f"⚠️ **DATA INCONSISTENCY**: {null_count} missing values detected. Manual synchronization required.")
        
        # Identify locations of null values
        null_mask = df.isnull()
        null_indices = []
        for col in df.columns:
            rows = df.index[null_mask[col]].tolist()
            for r in rows:
                null_indices.append((r, col))
        
        with st.expander("🛠️ Manual Data Repair", expanded=True):
            new_df = df.copy()
            updated = False
            with st.form("null_fixer_form"):
                for idx, (r, col) in enumerate(null_indices):
                    # Show context for the row if possible
                    row_preview = df.iloc[r].fillna("NULL").to_dict()
                    val = st.text_input(f"Row {r} | Column: {col}", key=f"null_{r}_{col}")
                    if val:
                        # Try to cast to numeric if the column is numeric
                        orig_dtype = df[col].dtype
                        try:
                            if pd.api.types.is_numeric_dtype(orig_dtype):
                                new_df.at[r, col] = float(val) if '.' in val else int(val)
                            else:
                                new_df.at[r, col] = val
                        except:
                            new_df.at[r, col] = val
                
                if st.form_submit_button("🔨 Apply Repairs"):
                    if not new_df.isnull().sum().sum() < null_count:
                        st.error("No values were filled.")
                    else:
                        st.session_state.df = new_df
                        st.success("Data Repaired")
                        st.rerun()
            
        return False, df

# ══════════════════════════════════════════════════════════════════════
#   MAIN APP
# ══════════════════════════════════════════════════════════════════════

def render_main_app():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        
        nav_options = ["Data Studio", "Data Cleaning", "EDA", "Data Mind", "Visualization", "Advanced Analytics", "Comparative Analysis"]
        if st.session_state.username == "admin":
            nav_options.insert(0, "Admin Dashboard")
            
        page = st.radio("Navigation", nav_options)
        
        if st.session_state.df is None:
            if st.session_state.username == "admin":
                exceptions = ":not(:nth-child(1)):not(:nth-child(2)):not(:last-child)"
            else:
                exceptions = ":not(:nth-child(1)):not(:last-child)"
                
            st.markdown(
                f"""
                <style>
                div[role="radiogroup"] > label{exceptions},
                div[role="radiogroup"] > div{exceptions} {{
                    pointer-events: none;
                    opacity: 0.4;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown("---")
        
        if st.button("🔄 Refresh", use_container_width=True):
            # Clear all data-heavy variables to simulate a true application refresh
            preserve_keys = {"logged_in", "username", "access_token", "api_keys_list", "active_api_key_index", "groq_client", "groq_api_key", "api_key_set"}
            for key in list(st.session_state.keys()):
                if key not in preserve_keys:
                    del st.session_state[key]
            st.rerun()
            
        st.markdown("### ⚙️ Settings")
        
        # Initialize multi-key state if not present
        if "api_keys_list" not in st.session_state:
            st.session_state.api_keys_list = ["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"]
            st.session_state.active_api_key_index = 0
            
        st.caption(f"API Keys ({len(st.session_state.api_keys_list)}/3)")
        
        # Selector for active API key
        new_active_idx = st.radio(
            "Select Active API Key",
            options=range(len(st.session_state.api_keys_list)),
            format_func=lambda i: "Default System Key" if i == 0 else f"Personal Key {i}",
            index=st.session_state.active_api_key_index
        )
        
        # Immediate state update + rerun if selection changes
        if new_active_idx != st.session_state.active_api_key_index:
            st.session_state.active_api_key_index = new_active_idx
            st.rerun()
            
        # Form to add a new key, disabled implicitly if limit reached
        if len(st.session_state.api_keys_list) < 3:
            with st.expander("➕ Add New Key"):
                with st.form("new_key_form"):
                    new_key = st.text_input("New GROQ API Key", type="password", placeholder="Paste here...")
                    if st.form_submit_button("Save Key", use_container_width=True):
                        if new_key and new_key not in st.session_state.api_keys_list:
                            st.session_state.api_keys_list.append(new_key)
                            # Auto-select the newly added key
                            st.session_state.active_api_key_index = len(st.session_state.api_keys_list) - 1
                            st.rerun()

        # Connect to Groq using the active key
        active_key = st.session_state.api_keys_list[st.session_state.active_api_key_index]
        if active_key:
            try:
                st.session_state.groq_client = Groq(api_key=active_key)
                st.session_state.groq_api_key = active_key
                st.session_state.api_key_set = True
                st.success("AI Activated", icon="💎")
            except Exception as e:
                st.error(f"Sync error: {e}")

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.query_params.clear()
            st.rerun()

    df = st.session_state.df
    st.markdown(
        f"""
        <div class="glass-header" style="margin-bottom: 3rem; display: flex; justify-content: space-between; align-items: center;">
            <div style="font-family: 'Outfit'; font-size: 1.5rem; font-weight: 200; letter-spacing: 0.4rem; color: #fff;">
                INSIGHT<span style='opacity:0.3;'> | </span>FLOW <span style="color: #2dd4bf; opacity: 0.6; font-size: 0.8rem; font-weight: 500;">// {page}</span>
            </div>
            <div style="display: flex; align-items: center; background: rgba(0,0,0,0.3); padding: 0.4rem 1.5rem; border-radius: 40px;">
                <div class="status-node" style="background: {'#2dd4bf' if df is not None else '#f43f5e'};"></div>
                <div style="font-size: 0.7rem; font-weight: 600; letter-spacing: 0.2rem; color: #fff; opacity: 0.8;">
                    { 'DATA LOADED' if df is not None else 'NO DATA' }
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True
    )

    if page == "Data Studio":
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("#### 📥 Import Data")
            u_file = st.file_uploader("Select File", type=["csv", "xlsx"], label_visibility="collapsed")
            if u_file and (st.session_state.df is None or st.session_state.dataset_name != u_file.name):
                st.session_state.df = load_data(u_file)
                st.session_state.dataset_name = u_file.name
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            if df is not None:
                st.markdown(f"**Dataset:** `{st.session_state.dataset_name}`")
                st.dataframe(df.head(10), use_container_width=True)
                c_exp, c_ref = st.columns(2)
                with c_exp:
                    st.download_button("📤 Export Data", df.to_csv(index=False), f"flow_{st.session_state.dataset_name}", use_container_width=True)
                with c_ref:
                    if st.button("🔄 Refresh Data", use_container_width=True):
                        st.session_state.df = None
                        st.rerun()
            else: st.info("Upload a dataset to begin.")
            st.markdown('</div>', unsafe_allow_html=True)

            # --- NEW: SQL FIXER ---
            st.markdown('<div class="premium-card" style="margin-top: 1.5rem;">', unsafe_allow_html=True)
            st.markdown("#### 🛠️ Auto SQL Fixer")
            st.caption("AI-powered syntactical repair for broken SQL queries.")
            
            sql_input = st.text_area("SQL Context", placeholder="e.g. SELECT * FORM users", label_visibility="collapsed", key="sql_fix_input", disabled=(df is None))
            if st.button("🔧 Resolve Query", use_container_width=True, disabled=(df is None)):
                if sql_input:
                    with st.spinner("Refining..."):
                        # Get API key from session state if available
                        api_key = None
                        if "groq_api_key" in st.session_state:
                             api_key = st.session_state.groq_api_key
                        
                        res = fix_sql_query(sql_input, api_key=api_key)
                        if res["success"]:
                            st.success("Query Refined")
                            st.code(res["fixed_sql"], language="sql")
                        else:
                            st.error(res["message"])
                else:
                    st.warning("Enter a query to fix.")
            st.markdown('</div>', unsafe_allow_html=True)

    elif page == "Data Cleaning":
        if df is not None: render_data_cleaning(df)
        else: st.warning("Upload data first.")
    elif page == "EDA":
        if df is not None:
            is_clean, df_clean = render_null_handler(df)
            if is_clean: render_eda(df_clean, st.session_state.groq_client)
        else: st.warning("Upload data first.")
    elif page == "Data Mind":
        if df is not None: render_chat(df, st.session_state.groq_client)
        else: st.warning("Upload data first.")
    elif page == "Visualization":
        if df is not None:
            is_clean, df_clean = render_null_handler(df)
            if is_clean: render_viz_builder(df_clean)
        else: st.warning("Upload data first.")
    elif page == "Advanced Analytics":
        if df is not None: render_advanced_analytics(df, st.session_state.groq_client)
        else: st.warning("Upload data first.")
    elif page == "Comparative Analysis":
        render_auto_flow()
    elif page == "Admin Dashboard":
        from modules.admin_dashboard import render_admin_dashboard
        render_admin_dashboard()

# ── ROUTER ───────────────────────────────────────────────────────────
if st.session_state.logged_in: render_main_app()
else: render_auth_page()