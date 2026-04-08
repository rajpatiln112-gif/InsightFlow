from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend import models, schemas
from backend.auth_utils import get_current_user

router = APIRouter(prefix="/charts", tags=["Charts"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/log", response_model=schemas.ChartHistoryResponse)
def log_chart(chart: schemas.ChartHistoryLog, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.username == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    db_chart = db.query(models.ChartHistory).filter(
        models.ChartHistory.user_id == user.id,
        models.ChartHistory.chart_type == chart.chart_type
    ).first()

    if db_chart:
        db_chart.count += 1
    else:
        db_chart = models.ChartHistory(
            user_id=user.id,
            chart_type=chart.chart_type,
            count=1
        )
        db.add(db_chart)
        
    db.commit()
    db.refresh(db_chart)
    return db_chart

@router.get("/history", response_model=list[schemas.ChartHistoryResponse])
def get_user_chart_history(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.username == current_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return db.query(models.ChartHistory).filter(models.ChartHistory.user_id == user.id).all()

@router.get("/admin/all", response_model=list[schemas.AdminChartHistoryResponse])
def get_all_chart_history(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.username == current_user).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    history = db.query(models.ChartHistory, models.User.username).\
        join(models.User, models.ChartHistory.user_id == models.User.id).all()

    result = []
    for chart_history, username in history:
        result.append({
            "username": username,
            "chart_type": chart_history.chart_type,
            "count": chart_history.count
        })

    return result
