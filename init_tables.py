from database import engine
import models

def init_tables():
    print("Creating tables...")
    models.Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_tables()
