import pymysql
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect as root
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "",  # Assuming root has no password
    "port": 3306,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def setup_database():
    try:
        connection = pymysql.connect(**DB_CONFIG)
        try:
            with connection.cursor() as cursor:
                # Create Database
                logger.info("Creating database 'mystock' if not exists...")
                cursor.execute("CREATE DATABASE IF NOT EXISTS mystock CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                
                # Create User
                logger.info("Creating user 'admin'...")
                # Note: IF NOT EXISTS for CREATE USER is available in MySQL 5.7+ and MariaDB 10.1.3+
                try:
                    cursor.execute("CREATE USER IF NOT EXISTS 'admin'@'localhost' IDENTIFIED BY 'admin1234';")
                    # Update password just in case it already exists but with different password
                    cursor.execute("ALTER USER 'admin'@'localhost' IDENTIFIED BY 'admin1234';")
                except pymysql.err.OperationalError as e:
                    # Fallback for older versions or if user creation fails specifically
                    logger.warning(f"User creation warning (might already exist): {e}")
                    cursor.execute("GRANT USAGE ON *.* TO 'admin'@'localhost';")
                    cursor.execute("SET PASSWORD FOR 'admin'@'localhost' = PASSWORD('admin1234');")

                # Grant Privileges
                logger.info("Granting privileges to 'admin' on 'mystock'...")
                cursor.execute("GRANT ALL PRIVILEGES ON mystock.* TO 'admin'@'localhost';")
                cursor.execute("FLUSH PRIVILEGES;")
                
                logger.info("Successfully setup 'mystock' database and 'admin' user.")
        finally:
            connection.close()
    except Exception as e:
        logger.error(f"Error setting up database: {e}")

if __name__ == "__main__":
    setup_database()
