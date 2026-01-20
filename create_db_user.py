import pymysql
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect as root
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "",  # Assuming root has no password based on previous context
    "port": 3306,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def create_admin_user():
    try:
        connection = pymysql.connect(**DB_CONFIG)
        try:
            with connection.cursor() as cursor:
                # Create Database if not exists (just in case)
                cursor.execute("CREATE DATABASE IF NOT EXISTS stock_db;")
                
                # Create User
                logger.info("Creating user 'admin'...")
                cursor.execute("CREATE USER IF NOT EXISTS 'admin'@'localhost' IDENTIFIED BY 'admin1234';")
                
                # Grant Privileges
                logger.info("Granting privileges to 'admin' on 'stock_db'...")
                cursor.execute("GRANT ALL PRIVILEGES ON stock_db.* TO 'admin'@'localhost';")
                cursor.execute("FLUSH PRIVILEGES;")
                
                logger.info("Successfully created user 'admin' with access to 'stock_db'.")
        finally:
            connection.close()
    except Exception as e:
        logger.error(f"Error creating user: {e}")

if __name__ == "__main__":
    create_admin_user()
