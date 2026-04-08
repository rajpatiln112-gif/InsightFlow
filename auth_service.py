"""
auth_service.py
Helper functions to call the FastAPI backend from Streamlit.
"""
import requests

BACKEND_URL = "http://127.0.0.1:8000"


def register_user(username: str, email: str, password: str) -> dict:
    """Call POST /users/register. Returns dict with 'success' bool and 'message'."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/users/register",
            json={"username": username, "email": email, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            return {"success": True, "message": "Registered successfully!"}
        elif response.status_code == 400:
            detail = response.json().get("detail", "Username already exists.")
            return {"success": False, "message": detail}
        else:
            return {"success": False, "message": f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "❌ Cannot connect to backend. Is the server running?"}


def login_user(username: str, password: str) -> dict:
    """Call POST /users/login. Returns dict with 'success' bool, 'token' or 'message'."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/users/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token", "")
            username = data.get("username", "")
            return {"success": True, "token": token, "username": username}
        elif response.status_code == 401:
            return {"success": False, "message": "Invalid username or password."}
        else:
            return {"success": False, "message": f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "❌ Cannot connect to backend. Is the server running?"}


def google_login(id_token: str) -> dict:
    """Call POST /users/google-login. Returns dict with 'success' bool and 'token'."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/users/google-login",
            json={"id_token": id_token},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token", "")
            username = data.get("username", "")
            return {"success": True, "token": token, "username": username}
        else:
            try:
                detail = response.json().get("detail", "Google authentication failed.")
            except:
                detail = f"Error {response.status_code}: {response.text}"
            return {"success": False, "message": detail}
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "❌ Cannot connect to backend. Is the server running?"}
