from pydantic import BaseModel
from datetime import datetime

class FavoriteBase(BaseModel):
    stock_code: str
    stock_name: str

class FavoriteCreate(FavoriteBase):
    pass

class Favorite(FavoriteBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
