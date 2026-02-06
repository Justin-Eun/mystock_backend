from database import SessionLocal, engine
import models
from sqlalchemy import text

def migrate_favorites():
    # Ensure tables exist
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Get all existing favorites
        favorites = db.query(models.Favorite).all()
        print(f"Found {len(favorites)} existing favorites to migrate.")

        migrated_kr = 0
        migrated_us = 0

        for fav in favorites:
            # Check if it's KR (digits only) or US
            if fav.stock_code.isdigit():
                # Check if already exists in KR table
                existing = db.query(models.FavoriteKR).filter(models.FavoriteKR.stock_code == fav.stock_code).first()
                if not existing:
                    new_fav = models.FavoriteKR(
                        stock_code=fav.stock_code,
                        stock_name=fav.stock_name
                    )
                    db.add(new_fav)
                    migrated_kr += 1
            else:
                # Check if already exists in US table
                existing = db.query(models.FavoriteUS).filter(models.FavoriteUS.stock_code == fav.stock_code).first()
                if not existing:
                    new_fav = models.FavoriteUS(
                        stock_code=fav.stock_code,
                        stock_name=fav.stock_name
                    )
                    db.add(new_fav)
                    migrated_us += 1
        
        db.commit()
        print(f"Migration Complete.")
        print(f"Migrated to KR: {migrated_kr}")
        print(f"Migrated to US: {migrated_us}")

    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_favorites()
