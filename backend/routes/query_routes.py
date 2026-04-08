from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend import models, schemas
from backend.auth_utils import get_current_user
from groq import Groq
import os

router = APIRouter(prefix="/queries", tags=["Queries"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.QueryResponse)
def create_query(query: schemas.QueryCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.username == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    db_query = models.QueryHistory(
        user_id=user.id,
        question=query.question,
        sql_query=query.sql_query
    )
    db.add(db_query)
    db.commit()
    db.refresh(db_query)
    return db_query

@router.get("/", response_model=list[schemas.QueryResponse])
def get_queries(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.username == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return db.query(models.QueryHistory).filter(models.QueryHistory.user_id == user.id).all()

@router.post("/fix", response_model=dict)
def fix_sql(payload: dict):
    sql = payload.get("sql")
    api_key = payload.get("api_key") or os.getenv("GROQ_API_KEY")
    
    if not sql:
        raise HTTPException(status_code=400, detail="SQL query is required")
    
    if not api_key:
         return {"fixed_sql": sql, "message": "GROQ_API_KEY not provided. Please set it in the sidebar."}

    client = Groq(api_key=api_key)
    prompt = f"You are an SQL expert. The following SQL query might be broken: `{sql}`. Please fix it and return ONLY the corrected SQL string. No explanations. No markdown blocks."
    
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        fixed_sql = completion.choices[0].message.content.strip()
        return {"fixed_sql": fixed_sql}
    except Exception as e:
        return {"fixed_sql": sql, "message": f"Error fixing SQL: {str(e)}"}
