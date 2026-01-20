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

load_dotenv()

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Stock Search AI (NEW SERVER)", description="Stock Search with AI Analysis")

# CORS Setup
origins = [
    "http://localhost:5173",  # Vite default port
    "http://127.0.0.1:5173",
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
@app.post("/api/favorites", response_model=schemas.Favorite)
def add_favorite(favorite: schemas.FavoriteCreate, db: Session = Depends(get_db)):
    return crud.create_favorite(db=db, favorite=favorite)

@app.get("/api/favorites", response_model=List[schemas.Favorite])
def read_favorites(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_favorites(db, skip=skip, limit=limit)

@app.delete("/api/favorites/{favorite_id}")
def delete_favorite(favorite_id: int, db: Session = Depends(get_db)):
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"status": "success"}

@app.delete("/api/favorites/code/{stock_code}")
def delete_favorite_by_code(stock_code: str, db: Session = Depends(get_db)):
    success = crud.delete_favorite_by_code(db, stock_code=stock_code)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"status": "success"}

# Stock & AI Endpoints
class AnalysisRequest(BaseModel):
    stock_code: str
    stock_name: str

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

if __name__ == "__main__":
    print("STARTING NEW SERVER...")
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
