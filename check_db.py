from sqlalchemy import text
from database import engine, SessionLocal

def check_database():
    try:
        db = SessionLocal()
        # Check current database name
        result = db.execute(text("SELECT DATABASE()")).scalar()
        print(f"Connected Database: {result}")

        # Check tables
        result = db.execute(text("SHOW TABLES")).fetchall()
        print("Tables in this database:")
        for row in result:
            print(f"- {row[0]}")
            
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_database()
