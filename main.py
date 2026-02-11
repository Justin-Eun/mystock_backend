from fastapi import FastAPI, Depends, HTTPException, Body
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import uvicorn
import os
from dotenv import load_dotenv
import crud, models, schemas, database

# IMPORT NEW PROVIDER EXPLICITLY
import stock_data_provider as data_service
import ai_service
import report_service
import thinkpool_service

load_dotenv()

try:
    models.Base.metadata.create_all(bind=database.engine)
except Exception as e:
    print(f"Warning: Database connection failed during startup. DB features will be unavailable. Error: {e}")

app = FastAPI(title="Stock Search AI (NEW SERVER)", description="Stock Search with AI Analysis")

# CORS Setup
origins = [
    "*", # Allow all origins for local network sharing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Stock Search AI API (Verified New Server)"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Database Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Favorites Endpoints
# Favorites Endpoints
# KR
@app.post("/api/favorites/kr", response_model=schemas.Favorite)
def add_favorite_kr(favorite: schemas.FavoriteCreate, db: Session = Depends(get_db)):
    return crud.create_favorite_kr(db=db, favorite=favorite)

@app.get("/api/favorites/kr", response_model=List[schemas.Favorite])
def read_favorites_kr(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_favorites_kr(db, skip=skip, limit=limit)

@app.delete("/api/favorites/kr/{stock_code}")
def delete_favorite_kr(stock_code: str, db: Session = Depends(get_db)):
    success = crud.delete_favorite_kr(db, stock_code=stock_code)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"status": "success"}

# US
@app.post("/api/favorites/us", response_model=schemas.Favorite)
def add_favorite_us(favorite: schemas.FavoriteCreate, db: Session = Depends(get_db)):
    return crud.create_favorite_us(db=db, favorite=favorite)

@app.get("/api/favorites/us", response_model=List[schemas.Favorite])
def read_favorites_us(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_favorites_us(db, skip=skip, limit=limit)

@app.delete("/api/favorites/us/{stock_code}")
def delete_favorite_us(stock_code: str, db: Session = Depends(get_db)):
    success = crud.delete_favorite_us(db, stock_code=stock_code)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"status": "success"}

# Legacy support
@app.get("/api/favorites", response_model=List[schemas.Favorite])
def read_favorites_all(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    kr = crud.get_favorites_kr(db, skip, limit)
    us = crud.get_favorites_us(db, skip, limit)
    return kr + us

@app.delete("/api/favorites/code/{stock_code}")
def delete_favorite_by_code(stock_code: str, db: Session = Depends(get_db)):
    success = crud.delete_favorite_kr(db, stock_code)
    if not success:
        success = crud.delete_favorite_us(db, stock_code)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"status": "success"}

# Stock & AI Endpoints
class AnalysisRequest(BaseModel):
    stock_code: str
    stock_name: str

class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []
    context: dict = {}

@app.get("/api/search")
async def search_stocks(q: str):
    return await data_service.search_stock(q)

@app.get("/api/stock/{code}/price")
async def get_price(code: str, timeframe: str = "day", start_date: str = None, end_date: str = None):
    return await data_service.get_stock_price(code, timeframe, start_date, end_date)

@app.get("/api/stock/{code}/financials")
async def get_financials(code: str):
    return await data_service.get_financials(code)

@app.post("/api/analyze")
async def analyze_stock(request: AnalysisRequest):
    prices = await data_service.get_stock_price(request.stock_code, "day", None, None)
    financials = await data_service.get_financials(request.stock_code)
    analysis = await ai_service.analyze_stock(request.stock_name, prices, financials)
    return {"analysis": analysis}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    response = await ai_service.chat_with_agent(request.message, request.history, request.context)
    return {"response": response}

@app.get("/api/dashboard")
async def get_dashboard_data():
    # 1. Fetch Data
    indices = await data_service.get_global_market_indices()
    
    # 2. Generate Briefing via AI
    briefing = await ai_service.generate_market_briefing(indices)
    
    return {
        "indices": indices,
        "briefing": briefing
    }

@app.get("/api/reports")
async def get_reports(source: str = "hankyung", start_date: str = None, end_date: str = None):
    return await report_service.get_research_reports(source, start_date, end_date)

@app.get("/api/issue/ai")
async def get_ai_issues():
    return await thinkpool_service.get_ai_issue_data()


if __name__ == "__main__":
    print("STARTING NEW SERVER...")
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
