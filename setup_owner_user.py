import pymysql
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect as root
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "", 
    "port": 3306,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def setup_owner_user():
    try:
        connection = pymysql.connect(**DB_CONFIG)
        try:
            with connection.cursor() as cursor:
                # 1. Create User
                logger.info("Creating user 'stock_owner'...")
                cursor.execute("CREATE USER IF NOT EXISTS 'stock_owner'@'localhost' IDENTIFIED BY 'stock1234';")
                cursor.execute("ALTER USER 'stock_owner'@'localhost' IDENTIFIED BY 'stock1234';")

                # 2. Revoke all existing privileges (start fresh)
                logger.info("Revoking global privileges from 'stock_owner'...")
                cursor.execute("REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'stock_owner'@'localhost';")

                # 3. Grant Privileges ONLY on mystock
                logger.info("Granting privileges on 'mystock' to 'stock_owner'...")
                cursor.execute("GRANT ALL PRIVILEGES ON mystock.* TO 'stock_owner'@'localhost';")
                
                # 4. Flush
                cursor.execute("FLUSH PRIVILEGES;")
                
                logger.info("Successfully configured 'stock_owner' with access ONLY to 'mystock'.")
                
                # Verify grants
                cursor.execute("SHOW GRANTS FOR 'stock_owner'@'localhost';")
                grants = cursor.fetchall()
                for grant in grants:
                    logger.info(f"Grant: {list(grant.values())[0]}")

        finally:
            connection.close()
    except Exception as e:
        logger.error(f"Error setting up user: {e}")

if __name__ == "__main__":
    setup_owner_user()
