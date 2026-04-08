import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000"

def log_chart_creation(chart_type: str) -> dict:
    """Save chart creation log to the backend SQLite history."""
    if not st.session_state.get("logged_in") or not st.session_state.get("access_token"):
        return {"success": False, "message": "User not logged in or token missing"}

    try:
        response = requests.post(
            f"{BACKEND_URL}/charts/log",
            json={"chart_type": chart_type},
            headers={"Authorization": f"Bearer {st.session_state.get('access_token', '')}"},
            timeout=5
        )
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "message": f"Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def get_chart_history() -> list:
    """Fetch current user's chart history from the backend."""
    if not st.session_state.get("logged_in") or not st.session_state.get("access_token"):
        return []

    try:
        response = requests.get(
            f"{BACKEND_URL}/charts/history",
            headers={"Authorization": f"Bearer {st.session_state.get('access_token', '')}"},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception:
        return []

def get_all_users_chart_history() -> list:
    """Fetch the chart history of all users. Accessible only by admin."""
    if not st.session_state.get("logged_in") or not st.session_state.get("access_token"):
        return []

    try:
        response = requests.get(
            f"{BACKEND_URL}/charts/admin/all",
            headers={"Authorization": f"Bearer {st.session_state.get('access_token', '')}"},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception:
        return []
