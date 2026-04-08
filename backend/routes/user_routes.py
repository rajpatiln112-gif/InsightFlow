from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend import models
from backend import schemas
from sqlalchemy.exc import IntegrityError
from backend.auth_utils import hash_password, verify_password, create_access_token, get_current_user
import os
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

router = APIRouter(prefix="/users", tags=["Users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=dict)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        # Check username
        existing_user = db.query(models.User).filter(models.User.username == user.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Check email
        existing_email = db.query(models.User).filter(models.User.email == user.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")

        new_user = models.User(
            username=user.username,
            email=user.email,
            password=hash_password(user.password)
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "User registered successfully"}
    except IntegrityError as e:
        db.rollback()
        detail = str(e.orig)
        if "users.username" in detail:
            raise HTTPException(status_code=400, detail="Username already exists")
        if "users.email" in detail:
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(status_code=400, detail="Registration failed: Integrity constraint violation.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/login", response_model=schemas.TokenResponse)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):

    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": db_user.username,
        "role": db_user.role
    })

    return {"access_token": token, "username": db_user.username}


@router.post("/google-login", response_model=schemas.TokenResponse)
def google_login(request: schemas.GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        # Verify the ID token from Google
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        if not client_id:
             raise HTTPException(status_code=500, detail="Server-side GOOGLE_CLIENT_ID not configured")

        idinfo = id_token.verify_oauth2_token(request.id_token, google_requests.Request(), client_id)

        # ID token is valid. Get the user's Google ID, email, and name.
        email = idinfo['email']
        username = email.split('@')[0]  # Simple username from email

        # Check if user exists
        db_user = db.query(models.User).filter(models.User.email == email).first()
        
        if not db_user:
            # Create a new user if not exists
            # We use a random password for OAuth users since they don't use password-based login
            import secrets
            db_user = models.User(
                username=username,
                email=email,
                password=hash_password(secrets.token_urlsafe(16))
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

        # Create access token
        token = create_access_token({
            "sub": db_user.username,
            "role": db_user.role
        })

        return {"access_token": token, "username": db_user.username}

    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google ID token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
def read_users_me(current_user: str = Depends(get_current_user)):
    # If the token is valid, get_current_user returns the username
    return {"message": "You are viewing a protected route!", "current_user": current_user}