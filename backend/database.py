import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Check if we're in a read-only environment (like Streamlit Cloud /mount/src)
_current_dir = os.path.dirname(os.path.abspath(__file__))
_db_path = os.path.join(_current_dir, "insightflow.db")

# Fallback to temp directory if the current directory is read-only
if not os.access(_current_dir, os.W_OK):
    import tempfile
    _db_path = os.path.join(tempfile.gettempdir(), "insightflow.db")

# Fix for Windows paths in SQLAlchemy (needs forward slashes)
_db_url_path = _db_path.replace("\\", "/")
DATABASE_URL = f"sqlite:///{_db_url_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
