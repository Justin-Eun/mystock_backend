from sqlalchemy.orm import Session
from models import Favorite
import schemas

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

def delete_favorite(db: Session, favorite_id: int):
    db_favorite = db.query(Favorite).filter(Favorite.id == favorite_id).first()
    if db_favorite:
        db.delete(db_favorite)
        db.commit()
        return True
    return False

def delete_favorite_by_code(db: Session, stock_code: str):
    db_favorite = db.query(Favorite).filter(Favorite.stock_code == stock_code).first()
    if db_favorite:
        db.delete(db_favorite)
        db.commit()
        return True
    return False
