from database import engine, Base
from models import Favorite
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    try:
        logger.info("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Tables dropped.")
        
        logger.info("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully.")
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")

if __name__ == "__main__":
    reset_database()
