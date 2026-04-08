import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000"

def save_query(question: str, sql_query: str) -> dict:
    """Save a query to the backend SQLite history."""
    if st.session_state.get("username") == "guest" or not st.session_state.get("logged_in"):
        return {"success": False, "message": "User not logged in"}

    try:
        response = requests.post(
            f"{BACKEND_URL}/queries/",
            json={"question": question, "sql_query": sql_query},
            headers={"Authorization": f"Bearer {st.session_state.get('access_token', '')}"},
            timeout=5
        )
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "message": f"Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def get_queries() -> list:
    """Fetch all queries for the current user from the backend."""
    if not st.session_state.get("logged_in"):
        return []

    try:
        response = requests.get(
            f"{BACKEND_URL}/queries/",
            headers={"Authorization": f"Bearer {st.session_state.get('access_token', '')}"},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception:
        return []

def fix_sql_query(sql: str, api_key: str = None) -> dict:
    """Call the backend to fix a broken SQL query."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/queries/fix",
            json={"sql": sql, "api_key": api_key},
            timeout=10
        )
        if response.status_code == 200:
            return {"success": True, "fixed_sql": response.json().get("fixed_sql")}
        else:
            return {"success": False, "message": f"Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"success": False, "message": str(e)}
