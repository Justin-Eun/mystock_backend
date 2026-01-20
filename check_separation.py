from sqlalchemy import text
from database import engine, SessionLocal

def check_separation():
    try:
        db = SessionLocal()
        # List Databases
        print("--- Databases ---")
        result = db.execute(text("SHOW DATABASES")).fetchall()
        for row in result:
            print(row[0])
            
        # Check current user (should be admin)
        print("\n--- Current User ---")
        user = db.execute(text("SELECT USER()")).scalar()
        print(f"User: {user}")

        # Check Grants
        print("\n--- Grants for Current User ---")
        grants = db.execute(text(f"SHOW GRANTS FOR CURRENT_USER")).fetchall()
        for row in grants:
            print(row[0])

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_separation()
