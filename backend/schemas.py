from pydantic import BaseModel, EmailStr
from datetime import datetime


# ---------- USER ----------

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str

class TokenResponse(BaseModel):
    access_token: str
    username: str
    token_type: str = "bearer"


# ---------- QUERY ----------

class QueryCreate(BaseModel):
    question: str
    sql_query: str


class QueryResponse(BaseModel):
    id: int
    question: str
    sql_query: str
    created_at: datetime

    class Config:
        from_attributes = True

# ---------- CHART HISTORY ----------

class ChartHistoryLog(BaseModel):
    chart_type: str

class ChartHistoryResponse(BaseModel):
    id: int
    chart_type: str
    count: int
    updated_at: datetime

    class Config:
        from_attributes = True

class AdminChartHistoryResponse(BaseModel):
    username: str
    chart_type: str
    count: int