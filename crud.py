from sqlalchemy.orm import Session
from models import Favorite, FavoriteKR, FavoriteUS
import schemas

# Generic/Old
def get_favorites(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Favorite).offset(skip).limit(limit).all()

def create_favorite(db: Session, favorite: schemas.FavoriteCreate):
    existing = db.query(Favorite).filter(Favorite.stock_code == favorite.stock_code).first()
    if existing:
        return existing
    db_favorite = Favorite(stock_code=favorite.stock_code, stock_name=favorite.stock_name)
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    return db_favorite

def delete_favorite_by_code(db: Session, stock_code: str):
    db_favorite = db.query(Favorite).filter(Favorite.stock_code == stock_code).first()
    if db_favorite:
        db.delete(db_favorite)
        db.commit()
        return True
    return False

# KR
def get_favorites_kr(db: Session, skip: int = 0, limit: int = 100):
    return db.query(FavoriteKR).offset(skip).limit(limit).all()

def create_favorite_kr(db: Session, favorite: schemas.FavoriteCreate):
    existing = db.query(FavoriteKR).filter(FavoriteKR.stock_code == favorite.stock_code).first()
    if existing:
        return existing
    db_favorite = FavoriteKR(stock_code=favorite.stock_code, stock_name=favorite.stock_name)
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    return db_favorite

def delete_favorite_kr(db: Session, stock_code: str):
    db_favorite = db.query(FavoriteKR).filter(FavoriteKR.stock_code == stock_code).first()
    if db_favorite:
        db.delete(db_favorite)
        db.commit()
        return True
    return False

# US
def get_favorites_us(db: Session, skip: int = 0, limit: int = 100):
    return db.query(FavoriteUS).offset(skip).limit(limit).all()

def create_favorite_us(db: Session, favorite: schemas.FavoriteCreate):
    existing = db.query(FavoriteUS).filter(FavoriteUS.stock_code == favorite.stock_code).first()
    if existing:
        return existing
    db_favorite = FavoriteUS(stock_code=favorite.stock_code, stock_name=favorite.stock_name)
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    return db_favorite

def delete_favorite_us(db: Session, stock_code: str):
    db_favorite = db.query(FavoriteUS).filter(FavoriteUS.stock_code == stock_code).first()
    if db_favorite:
        db.delete(db_favorite)
        db.commit()
        return True
    return False
