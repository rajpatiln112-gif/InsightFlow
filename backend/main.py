from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, SessionLocal
from backend import models
from backend.routes import user_routes, query_routes, chart_routes
from backend.auth_utils import hash_password
from dotenv import load_dotenv

load_dotenv()

models.Base.metadata.create_all(bind=engine)

# Create admin user if it doesn't exist
with SessionLocal() as db:
    admin_user = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin_user:
        admin_user = models.User(
            username="admin",
            email="admin@insightflow.com",
            password=hash_password("IBSAR123"),
            role="admin"
        )
        db.add(admin_user)
        db.commit()

    # Create default standard user if it doesn't exist
    standard_user = db.query(models.User).filter(models.User.username == "user").first()
    if not standard_user:
        standard_user = models.User(
            username="user",
            email="user@insightflow.com",
            password=hash_password("IBSAR123"),
            role="user"
        )
        db.add(standard_user)
        db.commit()

app = FastAPI(title="InsightFlow Backend")

# Add CORS middleware to allow requests from Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (Streamlit apps)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "InsightFlow API is running"}

app.include_router(user_routes.router)
app.include_router(query_routes.router)
app.include_router(chart_routes.router)
